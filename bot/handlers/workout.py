"""Workout logging: Strong CSV export, manual entry."""
import io
from datetime import date
from aiogram import Router, F
from aiogram.types import Message, Document
from aiogram.filters import Command

from db.database import log_workout, get_recent_workouts, get_user
from integrations.strong.parser import parse_strong_csv, workout_summary
from services.coach.motivator import check_gym_streak
from ai.client import fast

router = Router()


@router.message(F.text == "🏋️ Мои тренировки")
@router.message(Command("workouts"))
async def cmd_workouts(msg: Message):
    workouts = await get_recent_workouts(msg.from_user.id, days=14)
    if not workouts:
        await msg.answer(
            "За последние 2 недели нет записей тренировок.\n"
            "Пришли CSV экспорт из Strong или /log_workout чтобы добавить вручную."
        )
        return

    streak = await check_gym_streak(msg.from_user.id)
    days = streak["days_since"]

    lines = [f"🏋️ *Тренировки за 14 дней* ({len(workouts)} шт)\n"]
    for w in workouts[:5]:
        import json
        exercises = json.loads(w.get("exercises", "[]"))
        ex_count = len(exercises)
        lines.append(f"• {w['workout_date']} — *{w['name']}* ({ex_count} упр., {w.get('duration_min', '?')} мин)")

    if days == 0:
        lines.append("\n💪 Сегодня уже тренировался — красавчик!")
    elif days == 1:
        lines.append("\n✅ Последняя тренировка вчера.")
    else:
        lines.append(f"\n⚠️ Последняя тренировка {days} дней назад!")

    await msg.answer("\n".join(lines), parse_mode="Markdown")


@router.message(F.document)
async def handle_document(msg: Message):
    doc: Document = msg.document
    filename = doc.file_name or ""

    if not filename.endswith(".csv"):
        return

    await msg.answer("📄 Обрабатываю экспорт Strong...")

    file = await msg.bot.get_file(doc.file_id)
    buf = io.BytesIO()
    await msg.bot.download_file(file.file_path, destination=buf)
    content = buf.getvalue().decode("utf-8", errors="replace")

    try:
        workouts = parse_strong_csv(content)
    except Exception as e:
        await msg.answer(f"Не смог распарсить файл: {e}")
        return

    if not workouts:
        await msg.answer("В файле не найдено тренировок.")
        return

    saved = 0
    for w in workouts:
        await log_workout(
            tg_id=msg.from_user.id,
            source="strong",
            workout_date=w["workout_date"],
            name=w["name"],
            duration_min=w["duration_min"],
            exercises=w["exercises"],
            notes=w["notes"],
            raw_data=content[:5000],
        )
        saved += 1

    latest = workouts[0]
    summary = workout_summary(latest)

    user = await get_user(msg.from_user.id)
    ai_comment = await fast(
        f"Прокомментируй тренировку кратко (2 предложения): {summary}",
        system="Ты личный тренер. Коротко и конкретно, на русском."
    )

    await msg.answer(
        f"✅ Загружено {saved} тренировок!\n\n"
        f"{summary}\n\n"
        f"🤖 {ai_comment}",
        parse_mode="Markdown"
    )


@router.message(F.text == "📅 Неделя")
async def cmd_week(msg: Message):
    from services.coach.motivator import weekly_review
    user = await get_user(msg.from_user.id)
    if not user:
        await msg.answer("Сначала пройди регистрацию /start")
        return
    await msg.answer("⏳ Анализирую неделю...")
    review = await weekly_review(msg.from_user.id, user)
    from tts.speaker import send_voice_or_text
    await send_voice_or_text(msg.bot, msg.from_user.id, review)
