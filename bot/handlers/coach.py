"""Free-form chat with the AI coach."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from ai.client import smart
from db.database import get_user, get_recent_workouts, get_today_food
from tts.speaker import send_voice_or_text

router = Router()

COACH_SYSTEM = """Ты личный тренер и нутрициолог. Ты общаешься жёстко но справедливо.
Пишешь на русском. Коротко, конкретно. Можешь ругать если нужно, но всегда мотивируешь."""


@router.message(F.text == "💬 Спросить тренера")
async def prompt_coach(msg: Message):
    await msg.answer("Пиши свой вопрос тренеру — отвечу как смогу! 💪")


@router.message(Command("ask"))
@router.message(F.text.startswith("тренер") | F.text.startswith("Тренер"))
async def ask_coach(msg: Message):
    user = await get_user(msg.from_user.id)
    workouts = await get_recent_workouts(msg.from_user.id, days=7)

    context_parts = []
    if user:
        context_parts.append(f"Клиент: {user.get('name','?')}, {user.get('age','?')} лет, {user.get('weight_kg','?')} кг, цель: {user.get('goal','?')}")
    if workouts:
        context_parts.append(f"Последних тренировок за неделю: {len(workouts)}")

    question = msg.text
    for prefix in ["тренер,", "тренер", "Тренер,", "Тренер", "/ask"]:
        question = question.replace(prefix, "").strip()

    system = COACH_SYSTEM
    if context_parts:
        system += "\n\nКонтекст клиента:\n" + "\n".join(context_parts)

    await msg.answer("💭 Думаю...")
    answer = await smart(question, system=system)

    # Голосовой ответ если сообщение заканчивается на 🎤 или содержит "голосом"
    if "🎤" in msg.text or "голосом" in msg.text.lower():
        await send_voice_or_text(msg.bot, msg.from_user.id, answer)
    else:
        await msg.answer(answer)
