import os
from langchain_community.vectorstores import Chroma

# --- Configuration ---
# Set this to the DB you want to inspect
CHROMA_DIR = os.path.join("chroma", "syllabus") 

# How many chunks to print
LIMIT = 10
# ---------------------

def view_chunks():
    if not os.path.exists(CHROMA_DIR):
        print(f"Database not found at: {CHROMA_DIR}")
        return

    # Load the persisted database
    # Note: We don't need an embedding function just to .get() data
    print(f"Loading database from: {CHROMA_DIR}...")
    db = Chroma(persist_directory=CHROMA_DIR)

    # Get all data from the database
    data = db.get() 

    documents = data.get("documents", [])
    metadatas = data.get("metadatas", [])
    ids = data.get("ids", [])

    if not documents:
        print("Database is empty.")
        return

    print(f"\n--- Found {len(documents)} total chunks. Showing first {LIMIT} ---")

    for i in range(min(len(documents), LIMIT)):
        print(f"\n--- Chunk {i+1} (ID: {ids[i]}) ---")
        
        # Print metadata
        print("Metadata:")
        print(metadatas[i])
        
        # Print the actual text chunk
        print("\nContent:")
        print(documents[i])
        print("-" * 40)

if __name__ == "__main__":
    view_chunks()