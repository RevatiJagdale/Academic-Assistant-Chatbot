# backend/ingestion_service.py
import os
import shutil
import pytesseract
from pdf2image import convert_from_path
from langchain_core.documents import Document
from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# --- Load Embedding Model Once ---
try:
    EMBEDDING_FUNCTION = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-mpnet-base-v2"
    )
except ImportError:
    raise ImportError("Please install langchain_huggingface and sentence-transformers")


def _save_to_chroma(chunks: list[Document], db_path: str):
    """Clears and saves chunks to a specified Chroma directory."""
    if not os.path.exists(db_path):
        print(f"Creating new database at: {db_path}")
    else:
        # We no longer delete. We ADD to the existing database.
        # This allows you to upload multiple files over time.
        print(f"Adding {len(chunks)} chunks to existing database: {db_path}")

    if not chunks:
        print("No chunks to save.")
        return

    db = Chroma.from_documents(
        chunks, 
        embedding=EMBEDDING_FUNCTION, 
        persist_directory=db_path,
        collection_metadata={"hnsw:space": "cosine"}
    )
    print(f"Ingestion complete for this file. Total chunks in DB: {db._collection.count()}")


def _process_pdf_rag(file_path: str, db_path: str):
    """(Private) Loads a PDF using Tesseract OCR, chunks, and saves."""
    print(f"Processing PDF with OCR: {file_path}")
    
    try:
        images = convert_from_path(file_path, dpi=300)
    except Exception as e:
        print(f"\n[!!! PDF2IMAGE/POPPLER ERROR !!!]")
        print(f"Error converting PDF to images: {e}")
        print("Make sure 'poppler' is installed and in your PATH.")
        return

    docs = []
    for i, image in enumerate(images):
        page_num = i + 1
        print(f"Running OCR on page {page_num}/{len(images)}...")
        try:
            text = pytesseract.image_to_string(image, lang='eng')
            if text.strip():
                docs.append(Document(
                    page_content=text,
                    metadata={
                        "source": os.path.basename(file_path),
                        "page": page_num,
                    }
                ))
        except Exception as ocr_e:
            print(f"Error during OCR on page {page_num}: {ocr_e}")
    
    if not docs:
        print("No text extracted from PDF.")
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
    chunks = splitter.split_documents(docs)
    
    for i, doc in enumerate(chunks):
        doc.metadata["chunk_id"] = i
        doc.metadata["module"] = db_path.split(os.sep)[-1] # 'syllabus' or 'labmanual'

    _save_to_chroma(chunks, db_path)
    print(f"PDF processed: {file_path}")


def _process_docx_rag(file_path: str, db_path: str):
    """(Private) Loads a DOCX, chunks it, and saves."""
    print(f"Processing DOCX: {file_path}")
    
    try:
        loader = Docx2txtLoader(file_path)
        docs = loader.load()
    except Exception as e:
        print(f"Error loading .docx file: {e}")
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = splitter.split_documents(docs)
    
    for i, doc in enumerate(chunks):
        doc.metadata["source"] = os.path.basename(file_path)
        doc.metadata["chunk_id"] = i
        doc.metadata["module"] = db_path.split(os.sep)[-1]

    _save_to_chroma(chunks, db_path)
    print(f"DOCX processed: {file_path}")


# --- NEW PUBLIC FUNCTION ---
def ingest_document(file_path: str):
    """
    Public ingestion router.
    Decides where to send a file based on its name.
    """
    filename = os.path.basename(file_path).lower()
    db_path = None
    
    # 1. Determine DB path from filename
    if "syllabus" in filename:
        db_path = os.path.join("chroma", "syllabus")
    elif "lab" in filename or "manual" in filename:
        db_path = os.path.join("chroma", "labmanual")
    else:
        # Default or skip
        print(f"[Warning] Skipping {filename}: Filename does not contain 'syllabus' or 'lab'/'manual'.")
        print("Defaulting to 'syllabus' DB for this file.")
        db_path = os.path.join("chroma", "syllabus")

    # 2. Determine file type and process
    if file_path.endswith(".pdf"):
        _process_pdf_rag(file_path, db_path)
    elif file_path.endswith(".docx"):
        _process_docx_rag(file_path, db_path)
    else:
        print(f"Skipping {filename}: Not a .pdf or .docx file.")