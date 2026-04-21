"""Coach logic: motivation, warnings, weekly reviews."""
import json
from datetime import date, timedelta
from ai.client import fast, smart
from db.database import get_recent_workouts, get_fitbit_today, get_today_food

COACH_SYSTEM = """Ты личный тренер и нутрициолог. Ты общаешься жёстко но справедливо.
Ты можешь ругать клиента когда нужно, но всегда мотивируешь двигаться вперёд.
Пишешь на русском языке. Коротко, конкретно, без воды."""


async def check_gym_streak(tg_id: int) -> dict:
    """Check days since last workout. Returns warning data."""
    workouts = await get_recent_workouts(tg_id, days=30)
    if not workouts:
        return {"days_since": 999, "last_date": None}

    last_date = date.fromisoformat(workouts[0]["workout_date"])
    days_since = (date.today() - last_date).days
    return {"days_since": days_since, "last_date": last_date.isoformat()}


async def gym_warning_message(tg_id: int, days_since: int, user_name: str = "") -> str:
    name = user_name or "чемпион"
    if days_since >= 5:
        severity = "КРИТИЧНО"
        emoji = "🚨"
    elif days_since >= 3:
        severity = "предупреждение"
        emoji = "⚠️"
    else:
        severity = "напоминание"
        emoji = "💪"

    prompt = f"""Клиент {name} не был в зале {days_since} дней. Уровень: {severity}.
Напиши короткое (2-3 предложения) {severity} от тренера.
Если критично — жёстко, без жалости. Если просто напоминание — мотивируй."""

    text = await fast(prompt, system=COACH_SYSTEM)
    return f"{emoji} {text}"


async def daily_steps_message(steps: int, goal: int, user_name: str = "") -> str:
    pct = steps / goal * 100
    if pct >= 100:
        mood = "отлично, похвали"
    elif pct >= 70:
        mood = "неплохо, подбодри добить до цели"
    elif pct >= 40:
        mood = "маловато, мягко попрекни"
    else:
        mood = "провал, жёстко пожури"

    prompt = f"""Клиент прошёл {steps} шагов из {goal} целевых ({pct:.0f}%).
Напиши короткое (1-2 предложения) сообщение — {mood}."""

    text = await fast(prompt, system=COACH_SYSTEM)
    return f"👣 {steps:,} / {goal:,} шагов\n{text}"


async def weekly_review(tg_id: int, user: dict) -> str:
    """Generate smart weekly review using the smart model."""
    workouts = await get_recent_workouts(tg_id, days=7)
    today = date.today()

    workout_summary = []
    for w in workouts:
        exercises = json.loads(w.get("exercises", "[]"))
        ex_names = [e["name"] for e in exercises[:5]]
        workout_summary.append(f"- {w['workout_date']}: {w['name']} ({', '.join(ex_names)})")

    fitbit_summary = []
    for i in range(7):
        d = (today - timedelta(days=i)).isoformat()
        fb = await get_fitbit_today(tg_id, d)
        if fb:
            fitbit_summary.append(f"- {d}: {fb.get('steps', 0)} шагов, сон {fb.get('sleep_min', 0)}мин")

    prompt = f"""Сделай анализ недели клиента.

ПРОФИЛЬ: цель={user.get('goal','?')}, вес={user.get('weight_kg','?')}кг
ТРЕНИРОВКИ за 7 дней ({len(workouts)} шт):
{chr(10).join(workout_summary) if workout_summary else 'Нет тренировок!'}

АКТИВНОСТЬ (Fitbit):
{chr(10).join(fitbit_summary) if fitbit_summary else 'Нет данных'}

Напиши анализ недели: что хорошо, что плохо, 3 конкретных задачи на следующую неделю.
Формат: структурированный текст с эмодзи, 10-15 строк."""

    return await smart(prompt, system=COACH_SYSTEM)


async def morning_motivation(user: dict) -> str:
    name = user.get("name", "чемпион")
    goal = user.get("goal", "")
    prompt = f"""Напиши утреннее мотивационное сообщение для {name}.
Цель клиента: {goal}.
Коротко (2-3 предложения), заряжающее, конкретное. Без банальщины."""
    text = await fast(prompt, system=COACH_SYSTEM)
    return f"🌅 {text}"
