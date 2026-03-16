# backend/ingest_all.py
import os
import time
from ingestion_service import ingest_document

DATA_DIR = "data"

def main():
    start_time = time.time()
    print("--- STARTING DYNAMIC BATCH INGESTION ---")
    
    if not os.path.exists(DATA_DIR):
        print(f"[ERROR] Data directory not found: {DATA_DIR}")
        return

    # Clear old RAG databases for a clean build
    if os.path.exists("chroma/syllabus"):
        print("Removing old syllabus database...")
        shutil.rmtree("chroma/syllabus")
    if os.path.exists("chroma/labmanual"):
        print("Removing old labmanual database...")
        shutil.rmtree("chroma/labmanual")
    
    # Scan and process RAG files (PDFs/DOCX)
    for filename in os.listdir(DATA_DIR):
        file_path = os.path.join(DATA_DIR, filename)
        
        if filename.lower().endswith((".pdf", ".docx")):
            print(f"\n--- Found RAG file: {filename} ---")
            ingest_document(file_path)
        
        elif "timetable.csv" in filename.lower():
            print(f"\n--- Found Tool file: {filename} ---")
            print("Tool will load this live. No ingestion needed.")
        
        elif "inventory.xlsx" in filename.lower():
            print(f"\n--- Found Tool file: {filename} ---")
            print("Tool will load this live. No ingestion needed.")

    end_time = time.time()
    print(f"\n--- ✅ BATCH INGESTION COMPLETE ---")
    print(f"Total time taken: {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    main()