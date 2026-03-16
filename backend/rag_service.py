# backend/rag_service.py
import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq

load_dotenv()

# --- Load Models ---
try:
    GROQ_API_KEY = os.environ["GROQ_API_KEY"]
    LLM = ChatGroq(model="llama-3.1-8b-instant", api_key=GROQ_API_KEY)
    
    # Using the 768-dimension model to match your DB
    EMBEDDING_FUNCTION = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-mpnet-base-v2" 
    )
except KeyError:
    raise RuntimeError("GROQ_API_KEY not found in .env file.")
except Exception as e:
    raise RuntimeError(f"Failed to initialize AI models: {e}")


def query_rag_module(
    question: str,
    db_path: str,
    prompt_template: str,
    not_found_message: str = "No relevant information found."
):
    question = (question or "").strip()
    if not question:
        return {"answer": "Please provide a question.", "sources": []}

    print(f"\n--- [RAG Debug] Querying: {db_path} ---")
    print(f"Question: {question}")

    if not os.path.exists(db_path):
        print(f"[Error] DB path does not exist: {db_path}")
        return {"answer": f"Database not found at {db_path}. Please ingest data first.", "sources": []}

    # 1. Connect to DB
    db = Chroma(
        persist_directory=db_path, 
        embedding_function=EMBEDDING_FUNCTION
    )

    # 2. Retrieve top-k (Force 4 docs)
    # We use similarity_search instead of relevance_scores to BYPASS score filtering issues
    results = db.similarity_search(question, k=8)

    print(f"--- [RAG Debug] Found {len(results)} chunks ---")
    
    # 3. NO THRESHOLD CHECK (The Nuclear Fix)
    if not results:
        print("[RAG Debug] No results found in DB.")
        return {"answer": not_found_message, "sources": []}

    # Print the first chunk to console so you see what it found
    print(f"[RAG Debug] Top Result Preview: {results[0].page_content[:150]}...")

    # 4. Build context
    context = "\n\n---\n\n".join([doc.page_content for doc in results])
    
    # 5. Format prompt
    prompt = prompt_template.format(context=context, question=question)

    # 6. Call LLM
    try:
        response = LLM.invoke(prompt).content
    except Exception as e:
        print(f"[ERROR] LLM call failed: {e}")
        return {"answer": "Error communicating with the language model.", "sources": []}

    # 7. Build sources list
    sources = []
    for doc in results:
        sources.append({
            "source": doc.metadata.get("source", "unknown"),
            "content_preview": doc.page_content[:100] + "...", 
            "score": 1.0 # Dummy score since we aren't calculating it
        })

    return {"answer": response, "sources": sources}