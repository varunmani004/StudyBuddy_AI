# rag_engine.py
# Phase 2.6 – Step 4: Offline AI Chat System (Ollama + RAG)
from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OllamaEmbeddings
from langchain.vectorstores import Chroma
from langchain.llms import Ollama
from langchain.chains import RetrievalQA
from pathlib import Path

# ---------- CONFIG ----------
DOCS_DIR = Path("phase2_6_offline_ai/docs")
CHROMA_DIR = Path("phase2_6_offline_ai/chroma_db")
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "mistral:7b-instruct-q4_0"

# ---------- STEP 1: Load Docs ----------
def load_documents():
    print("📘 Loading documents...")
    loaders = [TextLoader(str(p), encoding="utf8") for p in DOCS_DIR.glob("*.txt")]
    docs = []
    for loader in loaders:
        docs.extend(loader.load())
    return docs

# ---------- STEP 2: Split ----------
def split_docs(docs):
    print("✂️ Splitting documents into chunks...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    return splitter.split_documents(docs)

# ---------- STEP 3: Create / Load Vector Store ----------
def build_vector_store(chunks):
    print("🧩 Creating embeddings and vector database...")
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    vectordb = Chroma.from_documents(chunks, embedding=embeddings, persist_directory=str(CHROMA_DIR))
    vectordb.persist()
    return vectordb

# ---------- STEP 4: Build QA Chain ----------
def build_qa_chain(vectordb):
    retriever = vectordb.as_retriever(search_type="similarity", search_kwargs={"k": 3})
    llm = Ollama(model=CHAT_MODEL)
    qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever)
    return qa

# ---------- STEP 5: Full Pipeline ----------
def ask(query):
    print(f"💬 Query: {query}")
    # load or create vector DB
    if not CHROMA_DIR.exists() or not any(CHROMA_DIR.iterdir()):
        docs = load_documents()
        chunks = split_docs(docs)
        vectordb = build_vector_store(chunks)
    else:
        embeddings = OllamaEmbeddings(model=EMBED_MODEL)
        vectordb = Chroma(persist_directory=str(CHROMA_DIR), embedding_function=embeddings)

    qa = build_qa_chain(vectordb)
    answer = qa.run(query)
    return answer


if __name__ == "__main__":
    while True:
        q = input("\nYou: ")
        if q.lower() in ["exit", "quit"]:
            break
        print("AI:", ask(q))
