"""Fitbit OAuth2 flow and data commands."""
import json
from datetime import date
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import settings
from db.database import get_user, upsert_user, get_fitbit_today, upsert_fitbit_daily
from integrations.fitbit.client import FitbitClient, refresh_token

router = Router()

# Simple in-memory state for OAuth (tg_id -> state_token)
_oauth_states: dict[str, int] = {}

REDIRECT_URI = "https://ironcoach.example.com/fitbit/callback"  # set via env in prod


@router.message(Command("fitbit"))
async def cmd_fitbit(msg: Message):
    user = await get_user(msg.from_user.id)
    if not user:
        await msg.answer("Сначала /start")
        return

    if user.get("fitbit_token"):
        await msg.answer("✅ Fitbit уже подключён! Используй /fitbit_sync для обновления данных.")
        return

    from integrations.fitbit.client import get_auth_url
    if not settings.fitbit_client_id:
        await msg.answer("Fitbit не настроен. Добавь FITBIT_CLIENT_ID и FITBIT_CLIENT_SECRET в конфиг.")
        return

    state = str(msg.from_user.id)
    _oauth_states[state] = msg.from_user.id
    auth_url = get_auth_url(REDIRECT_URI, state)

    await msg.answer(
        f"🔗 Подключи Fitbit:\n{auth_url}\n\n"
        "После авторизации пришли мне код из адресной строки командой:\n"
        "`/fitbit_code <КОД>`",
        parse_mode="Markdown"
    )


@router.message(Command("fitbit_code"))
async def cmd_fitbit_code(msg: Message):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.answer("Использование: /fitbit_code <код>")
        return

    code = parts[1].strip()
    try:
        from integrations.fitbit.client import exchange_code
        token = await exchange_code(code, REDIRECT_URI)
        await upsert_user(msg.from_user.id, fitbit_token=json.dumps(token))
        await msg.answer("✅ Fitbit успешно подключён! Данные будут синхронизироваться автоматически.")
    except Exception as e:
        await msg.answer(f"Ошибка авторизации: {e}")


@router.message(Command("fitbit_sync"))
async def cmd_fitbit_sync(msg: Message):
    user = await get_user(msg.from_user.id)
    if not user or not user.get("fitbit_token"):
        await msg.answer("Fitbit не подключён. Используй /fitbit")
        return

    await msg.answer("⏳ Синхронизирую данные...")
    try:
        token = json.loads(user["fitbit_token"])
        try:
            token = await refresh_token(token)
            await upsert_user(msg.from_user.id, fitbit_token=json.dumps(token))
        except Exception:
            pass

        fc = FitbitClient(token)
        today = date.today().isoformat()

        summary = await fc.get_daily_summary(today)
        sleep = await fc.get_sleep(today)
        hr = await fc.get_heart_rate(today)
        weight = await fc.get_weight(today)

        await upsert_fitbit_daily(
            msg.from_user.id, today,
            steps=summary["steps"],
            calories_out=summary["calories_out"],
            active_minutes=summary["active_minutes"],
            sleep_min=sleep["total_minutes"],
            resting_hr=hr,
            weight_kg=weight,
        )

        lines = [
            f"⌚ *Fitbit — {today}*",
            f"👣 Шаги: {summary['steps']:,}",
            f"🔥 Калорий сожжено: {summary['calories_out']:,}",
            f"⚡ Активных минут: {summary['active_minutes']}",
            f"😴 Сон: {sleep['total_minutes']} мин ({sleep['total_minutes']//60}ч {sleep['total_minutes']%60}мин)",
        ]
        if hr:
            lines.append(f"❤️ Пульс в покое: {hr} уд/мин")
        if weight:
            lines.append(f"⚖️ Вес: {weight} кг")

        await msg.answer("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await msg.answer(f"Ошибка синхронизации: {e}")
