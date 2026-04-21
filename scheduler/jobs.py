"""APScheduler jobs: daily checks, step tracking, gym warnings."""
import json
import logging
from datetime import date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import settings
from db.database import get_db, get_fitbit_today, save_coach_message, upsert_fitbit_daily
from services.coach.motivator import (
    check_gym_streak, gym_warning_message, daily_steps_message,
    morning_motivation, weekly_review
)
from tts.speaker import send_voice_or_text

logger = logging.getLogger(__name__)
_bot = None
_scheduler = None


def init_scheduler(bot) -> AsyncIOScheduler:
    global _bot, _scheduler
    _bot = bot
    _scheduler = AsyncIOScheduler(timezone=settings.TZ if hasattr(settings, "TZ") else "Europe/Moscow")

    # Morning motivation + gym check
    _scheduler.add_job(
        morning_check,
        CronTrigger(hour=settings.daily_check_hour, minute=0),
        id="morning_check",
    )

    # Evening steps report
    _scheduler.add_job(
        evening_steps_check,
        CronTrigger(hour=settings.evening_check_hour, minute=0),
        id="evening_steps",
    )

    # Weekly review — Sunday 18:00
    _scheduler.add_job(
        weekly_review_job,
        CronTrigger(day_of_week="sun", hour=18, minute=0),
        id="weekly_review",
    )

    _scheduler.start()
    logger.info("Scheduler started.")
    return _scheduler


async def _get_all_users() -> list[dict]:
    db = await get_db()
    async with db.execute("SELECT * FROM users") as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def _sync_fitbit(user: dict) -> dict | None:
    if not user.get("fitbit_token"):
        return None
    try:
        from integrations.fitbit.client import FitbitClient, refresh_token
        from db.database import upsert_user
        token = json.loads(user["fitbit_token"])
        # Try refresh
        try:
            token = await refresh_token(token)
            await upsert_user(user["tg_id"], fitbit_token=json.dumps(token))
        except Exception:
            pass

        fc = FitbitClient(token)
        today = date.today().isoformat()
        summary = await fc.get_daily_summary(today)
        sleep = await fc.get_sleep(today)
        hr = await fc.get_heart_rate(today)
        weight = await fc.get_weight(today)

        await upsert_fitbit_daily(
            user["tg_id"], today,
            steps=summary["steps"],
            calories_out=summary["calories_out"],
            active_minutes=summary["active_minutes"],
            sleep_min=sleep["total_minutes"],
            resting_hr=hr,
            weight_kg=weight,
        )
        return await get_fitbit_today(user["tg_id"], today)
    except Exception as e:
        logger.warning(f"Fitbit sync failed for {user['tg_id']}: {e}")
        return None


async def morning_check():
    users = await _get_all_users()
    for user in users:
        try:
            await _sync_fitbit(user)

            # Morning motivation
            msg = await morning_motivation(user)
            await _bot.send_message(user["tg_id"], msg)
            await save_coach_message(user["tg_id"], "motivation", msg)

            # Gym warning if needed
            streak = await check_gym_streak(user["tg_id"])
            days = streak["days_since"]
            if days >= settings.no_gym_warn_days:
                warn = await gym_warning_message(user["tg_id"], days, user.get("name", ""))
                await send_voice_or_text(_bot, user["tg_id"], warn)
                await save_coach_message(user["tg_id"], "warning", warn)

        except Exception as e:
            logger.error(f"Morning check error for {user['tg_id']}: {e}")


async def evening_steps_check():
    users = await _get_all_users()
    today = date.today().isoformat()
    for user in users:
        try:
            await _sync_fitbit(user)
            fb = await get_fitbit_today(user["tg_id"], today)
            if not fb:
                continue
            steps = fb.get("steps", 0) or 0
            msg = await daily_steps_message(steps, settings.steps_goal, user.get("name", ""))
            await _bot.send_message(user["tg_id"], msg)
            await save_coach_message(user["tg_id"], "daily_steps", msg)
        except Exception as e:
            logger.error(f"Evening steps error for {user['tg_id']}: {e}")


async def weekly_review_job():
    users = await _get_all_users()
    for user in users:
        try:
            msg = await weekly_review(user["tg_id"], user)
            await send_voice_or_text(_bot, user["tg_id"], msg)
            await save_coach_message(user["tg_id"], "weekly_review", msg)
        except Exception as e:
            logger.error(f"Weekly review error for {user['tg_id']}: {e}")
