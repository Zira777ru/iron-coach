"""AI client: OpenRouter (text) + Google Gemini (vision fallback)."""
import base64
import httpx
from config import settings

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


async def _openrouter_chat(model: str, messages: list, max_tokens: int = 1024) -> str:
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": "https://github.com/Zira777ru/iron-coach",
        "X-Title": "IronCoach",
    }
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens}
    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(f"{OPENROUTER_BASE}/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


async def fast(prompt: str, system: str = "", max_tokens: int = 1024) -> str:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    return await _openrouter_chat(settings.ai_fast_model, msgs, max_tokens)


async def smart(prompt: str, system: str = "", max_tokens: int = 2048) -> str:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    return await _openrouter_chat(settings.ai_smart_model, msgs, max_tokens)


async def vision(image_bytes: bytes, prompt: str) -> str:
    """Vision analysis — uses Gemini if key is set, otherwise OpenRouter."""
    if settings.gemini_api_key:
        return await _gemini_vision(image_bytes, prompt)
    return await _openrouter_vision(image_bytes, prompt)


async def _gemini_vision(image_bytes: bytes, prompt: str) -> str:
    b64 = base64.b64encode(image_bytes).decode()
    payload = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
                {"text": prompt},
            ]
        }],
        "generationConfig": {"maxOutputTokens": 1024},
    }
    url = f"{GEMINI_BASE}/models/gemini-2.0-flash:generateContent?key={settings.gemini_api_key}"
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


async def _openrouter_vision(image_bytes: bytes, prompt: str) -> str:
    b64 = base64.b64encode(image_bytes).decode()
    messages = [{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            {"type": "text", "text": prompt},
        ],
    }]
    return await _openrouter_chat(settings.ai_vision_model, messages, max_tokens=1024)
