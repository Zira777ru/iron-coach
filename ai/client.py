import httpx
import base64
from config import settings

OPENROUTER_BASE = "https://openrouter.ai/api/v1"


async def _chat(model: str, messages: list, max_tokens: int = 1024) -> str:
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": "https://github.com/Zira777ru/iron-coach",
        "X-Title": "IronCoach",
    }
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{OPENROUTER_BASE}/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


async def fast(prompt: str, system: str = "") -> str:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    return await _chat(settings.ai_fast_model, msgs)


async def smart(prompt: str, system: str = "", max_tokens: int = 2048) -> str:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    return await _chat(settings.ai_smart_model, msgs, max_tokens)


async def vision(image_bytes: bytes, prompt: str, fast_model: bool = True) -> str:
    b64 = base64.b64encode(image_bytes).decode()
    model = settings.ai_fast_model if fast_model else settings.ai_smart_model
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    return await _chat(model, messages, max_tokens=1024)
