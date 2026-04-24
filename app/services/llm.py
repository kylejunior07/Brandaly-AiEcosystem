import httpx
from app.config import OPENROUTER_API_KEY, OPENROUTER_MODEL

async def query_llm(system_prompt: str, user_prompt: str) -> str:
    """Helper to call OpenRouter."""
    if not OPENROUTER_API_KEY:
        print("WARNING: No valid API Key set in .env file.")
        return "Error: No API Key configured."

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "FastAPI Social Sim"
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"LLM Error: {e}")
            return ""