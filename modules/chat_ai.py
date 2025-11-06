from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA
from modules.vector_store import get_vector_store

def get_ai_response_for_subject(query, subject_id):
    try:
        print(f"🔹 Generating answer for subject {subject_id} — Query: {query}")

        llm = Ollama(model="tinyllama:latest")  # Or "phi3:mini" if you prefer
        print("✅ Ollama model loaded successfully")

        vectorstore = get_vector_store(subject_id)
        print("✅ Vector store loaded")

        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=False,
        )

        result = qa_chain.invoke({"query": query})
        answer = result.get("result") or result.get("answer") or str(result)
        print("✅ Final AI Answer:", answer)
        return answer


    except Exception as e:
        print("❌ ERROR in get_ai_response_for_subject:", e)
        return f"[Error contacting local AI]: {str(e)}"
