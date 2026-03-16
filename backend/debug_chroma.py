import numpy as np
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

CHROMA_PATH = "chroma"

# ✅ Use the SAME model name you used in create_database.py
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Change this to test different queries
TEST_QUERY = "What are the subjects in semester 5?"

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def main():
    print("[INFO] Loading embeddings + Chroma DB...")
    embedding_function = HuggingFaceEmbeddings(model_name=MODEL_NAME)
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

    # Inspect DB
    docs = db.get()
    ids = docs.get("ids", [])
    vectors = docs.get("embeddings", [])
    metadatas = docs.get("metadatas", [])
    print(f"[INFO] DB has {len(ids)} vectors stored.")
    if not vectors:
        print("[ERROR] No vectors found. Did you run create_database.py?")
        return

    print(f"[INFO] Embedding dimension: {len(vectors[0])}")

    # Embed the query
    query_vec = embedding_function.embed_query(TEST_QUERY)
    print(f"[INFO] Query vector dimension: {len(query_vec)}")

    # Compute cosine similarities manually
    sims = []
    for i, v in enumerate(vectors[:50]):  # check only first 50 to keep it fast
        sim = cosine_similarity(np.array(query_vec), np.array(v))
        sims.append((i, sim, metadatas[i]))

    sims = sorted(sims, key=lambda x: x[1], reverse=True)
    print("\n[DEBUG] Top 5 manual cosine similarities:")
    for idx, score, meta in sims[:5]:
        print(f" - Chunk {idx} | score={score:.4f} | metadata={meta}")

    # Use Chroma's similarity search too
    results = db.similarity_search_with_relevance_scores(TEST_QUERY, k=5)
    print("\n[DEBUG] Chroma search results:")
    for i, (doc, score) in enumerate(results):
        print(f"Result {i+1}: score={score:.4f}")
        print("  ", doc.page_content[:200].replace("\n", " "), "...")
        print("  metadata:", doc.metadata)

if __name__ == "__main__":
    main()