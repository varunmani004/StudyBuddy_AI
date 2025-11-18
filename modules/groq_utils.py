# modules/groq_utils.py

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


# ============================================================
# 🔹 PRIMARY CHAT MODEL (OpenRouter)
# ============================================================
def openrouter_llm(messages):
    """
    Normal chat LLM for subject chat page.
    Uses DeepSeek (free).
    """
    if not OPENROUTER_API_KEY:
        return "⚠️ OpenRouter API key missing."

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://localhost",
        "X-Title": "StudyBuddy AI",
    }

    payload = {
        "model": "deepseek/deepseek-r1:free",
        "messages": messages,
        "max_tokens": 500,
        "temperature": 0.2
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=25)
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print("⚠️ OpenRouter API Error:", e)
        return "AI temporarily unavailable."


# ============================================================
# 🔹 STRICT JSON MODEL (for Quiz Generation)
# ============================================================
def openrouter_json_llm(prompt):
    """
    SPECIAL STRICT JSON generator for creating quizzes.
    Forces the model to output ONLY a JSON array.
    """

    if not OPENROUTER_API_KEY:
        raise ValueError("❌ OPENROUTER_API_KEY missing in .env")

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://localhost",
        "X-Title": "StudyBuddy AI",
    }

    messages = [
        {
            "role": "system",
            "content": (
                "You output STRICT JSON. "
                "No explanations. No markdown. No text before/after. "
                "Only a JSON array of 5 MCQ questions like:\n\n"
                "[{\"question\":\"...\",\"options\":[\"A\",\"B\",\"C\",\"D\"],\"answer\":\"A\"}]"
            )
        },
        {"role": "user", "content": prompt}
    ]

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": messages,
        "max_tokens": 1200,
        "temperature": 0.1
    }

    # Retry JSON parsing
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            data = response.json()

            raw = data["choices"][0]["message"]["content"].strip()

            # Extract JSON inside any text
            start = raw.find("[")
            end = raw.rfind("]") + 1

            if start == -1 or end == -1:
                continue

            json_str = raw[start:end]
            return json.loads(json_str)  # validate JSON

        except Exception as e:
            print(f"⚠️ JSON generation attempt {attempt+1} failed:", e)

    return []  # return empty to handle safely
