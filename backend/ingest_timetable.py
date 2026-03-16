# backend/ingest_timetable.py
import os
from ingestion_service import process_timetable_csv

CSV_PATH = "data/timetable.csv" # The CSV you want to ingest

def main():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CSV not found at {CSV_PATH}")
    
    print("--- Starting Manual Timetable Ingestion ---")
    process_timetable_csv(CSV_PATH)
    print("--- Ingestion Complete ---")

if __name__ == "__main__":
    main()