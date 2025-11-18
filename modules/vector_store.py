# ==============================================================
# VECTOR STORE — Chroma + SentenceTransformer (Stable RAG Engine)
# ==============================================================

import os
from langchain.vectorstores import Chroma
from sentence_transformers import SentenceTransformer


EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_embedder = None


def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL)
    return _embedder


# ---- Wrapper Class Required By LangChain 0.1.20 ----
class SentenceTransformerEmbedding:
    def __init__(self):
        self.model = get_embedder()

    def embed_documents(self, texts):
        return self.model.encode(texts).tolist()

    def embed_query(self, text):
        return self.model.encode([text])[0].tolist()


# Root directory
VECTOR_DB_ROOT = "vector_dbs"
os.makedirs(VECTOR_DB_ROOT, exist_ok=True)


# --------------------------------------------------------------
# ADD TEXT TO VECTOR DB
# --------------------------------------------------------------
def add_text_file_to_vector_db(text_path, subject_id):
    try:
        with open(text_path, "r", encoding="utf-8") as f:
            text = f.read().strip()

        if not text:
            print("⚠️ No text to embed.")
            return 0

        chunks = [text[i:i+800] for i in range(0, len(text), 800)]

        embedding = SentenceTransformerEmbedding()

        save_path = os.path.join(VECTOR_DB_ROOT, f"subject_{subject_id}")
        os.makedirs(save_path, exist_ok=True)

        db = Chroma.from_texts(
            texts=chunks,
            embedding=embedding,
            persist_directory=save_path
        )

        db.persist()
        print(f"✅ Vector DB created for subject {subject_id}")
        return 1

    except Exception as e:
        print("❌ Error vector DB:", e)
        return 0


# --------------------------------------------------------------
# LOAD VECTOR DB
# --------------------------------------------------------------
def get_vector_store(subject_id):
    try:
        save_path = os.path.join(VECTOR_DB_ROOT, f"subject_{subject_id}")

        if not os.path.exists(save_path):
            raise FileNotFoundError("Vector DB does not exist")

        embedding = SentenceTransformerEmbedding()

        db = Chroma(
            persist_directory=save_path,
            embedding_function=embedding
        )

        print(f"✅ Loaded vector DB for subject {subject_id}")
        return db

    except Exception as e:
        print("❌ Load error:", e)
        raise
