"""TTS: convert text to voice message (OGG Opus for Telegram)."""
import io
import httpx
from config import settings


async def text_to_voice(text: str) -> bytes | None:
    """Returns OGG Opus bytes or None if TTS is not configured."""
    if not settings.tts_url:
        return None

    payload = {
        "model": "tts-1",
        "input": text,
        "voice": settings.tts_voice,
        "response_format": "opus",
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{settings.tts_url}/audio/speech", json=payload)
        r.raise_for_status()
    return r.content


async def send_voice_or_text(bot, chat_id: int, text: str):
    """Try to send as voice message; fall back to text."""
    try:
        audio = await text_to_voice(text)
        if audio:
            from aiogram.types import BufferedInputFile
            voice_file = BufferedInputFile(audio, filename="voice.ogg")
            await bot.send_voice(chat_id, voice=voice_file, caption=text[:1024])
            return
    except Exception:
        pass
    await bot.send_message(chat_id, text)
