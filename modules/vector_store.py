import os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings

# Set your embedding model name
EMBED_MODEL = "nomic-embed-text"

# Base directory to store vector databases
VECTOR_DB_DIR = os.path.join("vector_dbs")
os.makedirs(VECTOR_DB_DIR, exist_ok=True)

# -------------------------------------------------------------
# 🧠 Add a text file into the vector database for a specific subject
# -------------------------------------------------------------
def add_text_file_to_vector_db(text_file_path, subject_id):
    """Add extracted text into a Chroma vector store for a specific subject."""
    try:
        with open(text_file_path, "r", encoding="utf-8") as f:
            text_data = f.read()

        if not text_data.strip():
            print(f"⚠️ Empty text file: {text_file_path}")
            return 0

        # Initialize embeddings
        embeddings = OllamaEmbeddings(model=EMBED_MODEL)

        # Folder for this subject’s vector store
        subject_db_dir = os.path.join(VECTOR_DB_DIR, f"subject_{subject_id}")
        os.makedirs(subject_db_dir, exist_ok=True)

        # Create Chroma vector store
        db = Chroma.from_texts([text_data], embedding=embeddings, persist_directory=subject_db_dir)
        db.persist()

        print(f"✅ Added text to vector DB for subject {subject_id}")
        return 1

    except Exception as e:
        print(f"❌ Error adding to vector DB: {e}")
        return 0


# -------------------------------------------------------------
# 🔍 Retrieve the vector store for a given subject
# -------------------------------------------------------------
def get_vector_store(subject_id):
    """Load an existing Chroma vector store for the given subject."""
    try:
        subject_db_dir = os.path.join(VECTOR_DB_DIR, f"subject_{subject_id}")

        if not os.path.exists(subject_db_dir):
            raise FileNotFoundError(f"Vector DB for subject {subject_id} not found at {subject_db_dir}")

        embeddings = OllamaEmbeddings(model=EMBED_MODEL)
        db = Chroma(persist_directory=subject_db_dir, embedding_function=embeddings)
        print(f"✅ Loaded vector store for subject {subject_id}")
        return db

    except Exception as e:
        print(f"❌ Error loading vector store: {e}")
        raise
