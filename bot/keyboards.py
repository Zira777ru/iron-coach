from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍽 Записать еду"), KeyboardButton(text="🏋️ Мои тренировки")],
            [KeyboardButton(text="📊 Статистика сегодня"), KeyboardButton(text="📅 Неделя")],
            [KeyboardButton(text="⚖️ Мой профиль"), KeyboardButton(text="💬 Спросить тренера")],
        ],
        resize_keyboard=True,
    )


def meal_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌅 Завтрак", callback_data="meal:breakfast"),
            InlineKeyboardButton(text="☀️ Обед", callback_data="meal:lunch"),
        ],
        [
            InlineKeyboardButton(text="🌆 Ужин", callback_data="meal:dinner"),
            InlineKeyboardButton(text="🍎 Перекус", callback_data="meal:snack"),
        ],
    ])
