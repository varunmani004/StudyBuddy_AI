# modules/chat_ai.py
import textwrap
from langchain_ollama import OllamaLLM
from modules.vector_store import get_vector_store

def get_ai_response_for_subject(query: str, subject_id: int) -> str:
    """
    Generate an AI-based response for a subject using local Ollama LLM
    with retrieved context from that subject’s Chroma vector store.
    Uses vectorstore.similarity_search(...) for compatibility.
    """
    try:
        print(f"🔹 Generating answer for subject {subject_id} — Query: {query}")

        # 1) Load local Ollama model
        llm = OllamaLLM(model="tinyllama:latest")
        print("✅ Ollama model loaded successfully")

        # 2) Load vector store and retrieve similar chunks
        vectorstore = get_vector_store(subject_id)
        # Use similarity_search which exists on Chroma-like vectorstores
        docs = []
        try:
            docs = vectorstore.similarity_search(query, k=3)
        except Exception as e:
            # fallback: if vectorstore exposes as_retriever with a method name
            try:
                retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
                # some retrievers may implement 'get_relevant_documents'
                if hasattr(retriever, "get_relevant_documents"):
                    docs = retriever.get_relevant_documents(query)
                elif hasattr(retriever, "get_relevant_texts"):
                    txts = retriever.get_relevant_texts(query)
                    docs = [type("D", (), {"page_content": t}) for t in txts]
                else:
                    docs = []
            except Exception:
                docs = []

        context = "\n\n".join([getattr(d, "page_content", str(d)) for d in docs]) if docs else "No relevant context found in uploaded notes."
        print(f"📚 Retrieved {len(docs)} context chunks")

        # 3) Build a safe tutor-style prompt
        prompt = textwrap.dedent(f"""
        You are a helpful AI tutor for students. Use the provided context to answer concisely.
        If the context does not contain the answer, say "I don't know based on the given notes."

        Context:
        {context}

        Question:
        {query}

        Answer:
        """).strip()

        # 4) Query the model
        try:
            ai_output = llm.invoke(prompt)
        except Exception:
            # some versions can be called directly
            ai_output = llm(prompt)

        answer = ai_output if isinstance(ai_output, str) else str(ai_output)
        print("✅ Final AI Answer (preview):", answer[:300])
        return answer

    except Exception as e:
        print("❌ ERROR in get_ai_response_for_subject:", e)
        return f"[Error contacting local AI]: {e}"
