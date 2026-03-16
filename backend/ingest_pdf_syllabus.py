# backend/ingest_pdf_syllabus.py
import os
from ingestion_service import process_syllabus_pdf

DATA_DIR = "data"
PDF_PATH = os.path.join(DATA_DIR, "22-26(1).pdf") # The PDF you want to ingest

def main():
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"Put your syllabus pdf at {PDF_PATH}")
    
    print("--- Starting Manual Syllabus Ingestion ---")
    process_syllabus_pdf(PDF_PATH)
    print("--- Ingestion Complete ---")

if __name__ == "__main__":
    main()