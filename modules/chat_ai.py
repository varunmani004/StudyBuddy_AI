# modules/chat_ai.py

import time
from modules.vector_store import get_vector_store
from modules.groq_utils import openrouter_llm     # we reuse this helper only


def _build_chat_messages(context: str, query: str) -> list:
    """
    Build structured messages for OpenRouter LLM.
    """
    system_prompt = (
        "You are a helpful and concise AI tutor. "
        "Use the provided context from the student's uploaded notes to answer. "
        "If the context does not contain the information, reply exactly with: "
        "\"I don't know based on the given notes.\" "
        "Keep the explanation simple, clear, and student-friendly."
    )

    user_prompt = (
        f"Context:\n{context}\n\n"
        f"Question:\n{query}\n\n"
        f"Answer clearly and in simple words:"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def get_ai_response_for_subject(query: str, subject_id: int) -> str:
    """
    MAIN + ONLY MODEL → OpenRouter
    Uses vector search + DeepSeek/OpenRouter for response.
    No Groq. No fallback. Clean & stable.
    """
    try:
        print(f"🔹 Generating answer for subject {subject_id} — Query: {query}")

        # ----------------------------------------------
        # 1️⃣ Load Vector DB & retrieve relevant chunks
        # ----------------------------------------------
        vectorstore = get_vector_store(subject_id)

        try:
            docs = vectorstore.similarity_search(query, k=3)
        except Exception as e:
            print("⚠️ Vector search error:", e)
            docs = []

        context = (
            "\n\n".join([getattr(d, "page_content", "") for d in docs])
            if docs else "No relevant context found in uploaded notes."
        )

        print(f"📚 Retrieved {len(docs)} context chunks")

        # ----------------------------------------------
        # 2️⃣ Build messages for OpenRouter
        # ----------------------------------------------
        messages = _build_chat_messages(context=context, query=query)

        # ----------------------------------------------
        # 3️⃣ Call OpenRouter API (MAIN MODEL)
        # ----------------------------------------------
        print("⚡ Using OpenRouter as primary & only model...")

        answer = openrouter_llm(messages)

        if not answer or answer.strip() == "":
            print("⚠️ OpenRouter returned empty response")
            return "⚠️ AI could not generate an answer."

        print("✅ OpenRouter Answer (preview):", answer[:150])
        return answer

    except Exception as e:
        print("❌ ERROR in get_ai_response_for_subject:", e)
        return "⚠️ AI temporarily unavailable."
