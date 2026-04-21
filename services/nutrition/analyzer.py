"""AI-powered food analysis from photos and FatSecret screenshots."""
import json
from ai.client import vision, fast

FOOD_PHOTO_PROMPT = """Ты нутрициолог-эксперт. Проанализируй еду на фото.
Определи:
1. Что это за блюда/продукты
2. Примерный вес/объем каждой позиции
3. КБЖУ (калории, белки, жиры, углеводы) для ВСЕГО приёма пищи

Ответь ТОЛЬКО в формате JSON (без markdown):
{
  "description": "краткое описание блюд",
  "items": [{"name": "...", "weight_g": 0, "kcal": 0, "protein_g": 0, "fat_g": 0, "carbs_g": 0}],
  "total": {"kcal": 0, "protein_g": 0, "fat_g": 0, "carbs_g": 0},
  "meal_type": "breakfast|lunch|dinner|snack",
  "confidence": "high|medium|low"
}"""

FATSECRET_PROMPT = """Это скриншот приложения FatSecret с записью питания.
Извлеки все данные о питании.
Ответь ТОЛЬКО в формате JSON (без markdown):
{
  "date": "YYYY-MM-DD или null",
  "meals": [
    {
      "meal_type": "breakfast|lunch|dinner|snack",
      "items": [{"name": "...", "weight_g": 0, "kcal": 0, "protein_g": 0, "fat_g": 0, "carbs_g": 0}],
      "total": {"kcal": 0, "protein_g": 0, "fat_g": 0, "carbs_g": 0}
    }
  ],
  "day_total": {"kcal": 0, "protein_g": 0, "fat_g": 0, "carbs_g": 0}
}"""


async def analyze_food_photo(image_bytes: bytes) -> dict:
    raw = await vision(image_bytes, FOOD_PHOTO_PROMPT, fast_model=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Failed to parse AI response: {raw[:200]}")


async def analyze_fatsecret_screenshot(image_bytes: bytes) -> dict:
    raw = await vision(image_bytes, FATSECRET_PROMPT, fast_model=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Failed to parse AI response: {raw[:200]}")


async def daily_nutrition_summary(food_logs: list[dict], user: dict) -> str:
    if not food_logs:
        return "Сегодня записей питания нет."

    total = {"kcal": 0, "protein_g": 0, "fat_g": 0, "carbs_g": 0}
    for log in food_logs:
        total["kcal"] += log.get("calories", 0) or 0
        total["protein_g"] += log.get("protein_g", 0) or 0
        total["fat_g"] += log.get("fat_g", 0) or 0
        total["carbs_g"] += log.get("carbs_g", 0) or 0

    goal = user.get("goal", "maintain")
    weight = user.get("weight_kg", 80)

    prompt = f"""Проанализируй питание за день для клиента.
Цель: {goal}, вес: {weight} кг.
Итоги дня: {total['kcal']:.0f} ккал, белки {total['protein_g']:.0f}г, жиры {total['fat_g']:.0f}г, углеводы {total['carbs_g']:.0f}г.
Записей приёмов пищи: {len(food_logs)}.

Дай короткий (3-4 предложения) анализ: достаточно ли белка, есть ли избыток/дефицит калорий, главный совет на завтра.
Тон: конкретный, без лишних слов."""

    return await fast(prompt)
