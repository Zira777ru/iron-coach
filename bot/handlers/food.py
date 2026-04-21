"""Food logging: photo analysis, FatSecret screenshots, text input."""
import io
from datetime import date
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PhotoSize
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db.database import log_food, get_today_food, get_user
from services.nutrition.analyzer import analyze_food_photo, analyze_fatsecret_screenshot, daily_nutrition_summary
from bot.keyboards import meal_type_keyboard

router = Router()
MEAL_NAMES = {"breakfast": "Завтрак", "lunch": "Обед", "dinner": "Ужин", "snack": "Перекус"}


class FoodState(StatesGroup):
    waiting_meal_type = State()
    waiting_photo = State()


@router.message(F.text == "🍽 Записать еду")
@router.message(Command("food"))
async def cmd_food(msg: Message):
    await msg.answer(
        "Пришли фото еды или скриншот из FatSecret — я всё распознаю автоматически.\n\n"
        "Или напиши текстом, например: *2 яйца, овсянка 100г, молоко 200мл*",
        parse_mode="Markdown"
    )


@router.message(F.photo)
async def handle_photo(msg: Message, state: FSMContext):
    await msg.answer("📸 Анализирую фото...")

    bot = msg.bot
    photo: PhotoSize = msg.photo[-1]
    file = await bot.get_file(photo.file_id)
    buf = io.BytesIO()
    await bot.download_file(file.file_path, destination=buf)
    image_bytes = buf.getvalue()

    # Detect if it's FatSecret screenshot or food photo
    # We'll try food photo first; if caption contains "fatsecret" — use that parser
    caption = (msg.caption or "").lower()
    try:
        if "fatsecret" in caption or "fat secret" in caption:
            data = await analyze_fatsecret_screenshot(image_bytes)
            await _save_fatsecret_data(msg.from_user.id, data)
            await msg.answer(_format_fatsecret_result(data))
        else:
            data = await analyze_food_photo(image_bytes)
            today = date.today().isoformat()
            total = data.get("total", {})
            meal_type = data.get("meal_type", "snack")
            await log_food(
                tg_id=msg.from_user.id,
                log_date=today,
                meal_type=meal_type,
                description=data.get("description", ""),
                calories=total.get("kcal", 0),
                protein_g=total.get("protein_g", 0),
                carbs_g=total.get("carbs_g", 0),
                fat_g=total.get("fat_g", 0),
                source="photo",
                ai_analysis=str(data),
            )
            await msg.answer(_format_food_result(data))
    except Exception as e:
        await msg.answer(f"Не смог распознать фото. Попробуй описать текстом.\n_Ошибка: {e}_", parse_mode="Markdown")


async def _save_fatsecret_data(tg_id: int, data: dict):
    today = data.get("date") or date.today().isoformat()
    for meal in data.get("meals", []):
        total = meal.get("total", {})
        items = meal.get("items", [])
        desc = ", ".join(i["name"] for i in items)
        await log_food(
            tg_id=tg_id,
            log_date=today,
            meal_type=meal.get("meal_type", "snack"),
            description=desc,
            calories=total.get("kcal", 0),
            protein_g=total.get("protein_g", 0),
            carbs_g=total.get("carbs_g", 0),
            fat_g=total.get("fat_g", 0),
            source="fatsecret_screenshot",
            ai_analysis=str(data),
        )


def _format_food_result(data: dict) -> str:
    total = data.get("total", {})
    items = data.get("items", [])
    confidence = data.get("confidence", "?")
    conf_emoji = {"high": "✅", "medium": "⚠️", "low": "❓"}.get(confidence, "")
    lines = [f"🍽 *{data.get('description', 'Приём пищи')}* {conf_emoji}"]
    for item in items:
        lines.append(f"  • {item['name']} ~{item.get('weight_g', 0)}г — {item.get('kcal', 0):.0f} ккал")
    lines.append(f"\n📊 *Итого:* {total.get('kcal', 0):.0f} ккал | Б:{total.get('protein_g', 0):.0f} Ж:{total.get('fat_g', 0):.0f} У:{total.get('carbs_g', 0):.0f}")
    lines.append("✅ Записано!")
    return "\n".join(lines)


def _format_fatsecret_result(data: dict) -> str:
    day = data.get("day_total", {})
    meals = data.get("meals", [])
    lines = ["📱 *FatSecret импорт*"]
    for meal in meals:
        total = meal.get("total", {})
        name = MEAL_NAMES.get(meal.get("meal_type", ""), meal.get("meal_type", ""))
        lines.append(f"\n*{name}:* {total.get('kcal', 0):.0f} ккал")
        for item in meal.get("items", [])[:4]:
            lines.append(f"  • {item['name']}")
    if day:
        lines.append(f"\n📊 *День итого:* {day.get('kcal', 0):.0f} ккал | Б:{day.get('protein_g', 0):.0f} Ж:{day.get('fat_g', 0):.0f} У:{day.get('carbs_g', 0):.0f}")
    lines.append("✅ Все приёмы записаны!")
    return "\n".join(lines)


@router.message(F.text == "📊 Статистика сегодня")
async def cmd_today_stats(msg: Message):
    today = date.today().isoformat()
    logs = await get_today_food(msg.from_user.id, today)
    user = await get_user(msg.from_user.id)

    if not logs:
        await msg.answer("Сегодня ещё нет записей питания. Пришли фото еды!")
        return

    total = {"kcal": 0, "protein_g": 0, "fat_g": 0, "carbs_g": 0}
    lines = [f"📊 *Питание за {today}*\n"]
    for log in logs:
        meal_name = MEAL_NAMES.get(log.get("meal_type", ""), "")
        lines.append(f"*{meal_name}:* {log.get('description', '')[:50]} — {log.get('calories', 0):.0f} ккал")
        total["kcal"] += log.get("calories", 0) or 0
        total["protein_g"] += log.get("protein_g", 0) or 0
        total["fat_g"] += log.get("fat_g", 0) or 0
        total["carbs_g"] += log.get("carbs_g", 0) or 0

    lines.append(f"\n📊 *Итого:* {total['kcal']:.0f} ккал | Б:{total['protein_g']:.0f} Ж:{total['fat_g']:.0f} У:{total['carbs_g']:.0f}г")

    analysis = await daily_nutrition_summary(logs, user or {})
    lines.append(f"\n🤖 {analysis}")
    await msg.answer("\n".join(lines), parse_mode="Markdown")
