from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db.database import get_user, upsert_user
from bot.keyboards import main_menu

router = Router()


class OnboardingState(StatesGroup):
    name = State()
    age = State()
    weight = State()
    height = State()
    goal = State()


@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    user = await get_user(msg.from_user.id)
    if user and user.get("name"):
        await msg.answer(
            f"Привет, {user['name']}! Я твой личный тренер 💪\n"
            "Используй меню ниже или просто пиши — я отвечу.",
            reply_markup=main_menu()
        )
        return

    await msg.answer(
        "👋 Привет! Я твой личный тренер и нутрициолог.\n\n"
        "Давай познакомимся. Как тебя зовут?"
    )
    await state.set_state(OnboardingState.name)


@router.message(OnboardingState.name)
async def onboard_name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text.strip())
    await msg.answer("Сколько тебе лет?")
    await state.set_state(OnboardingState.age)


@router.message(OnboardingState.age)
async def onboard_age(msg: Message, state: FSMContext):
    try:
        age = int(msg.text.strip())
    except ValueError:
        await msg.answer("Введи число, например: 28")
        return
    await state.update_data(age=age)
    await msg.answer("Какой у тебя вес (кг)? Например: 82.5")
    await state.set_state(OnboardingState.weight)


@router.message(OnboardingState.weight)
async def onboard_weight(msg: Message, state: FSMContext):
    try:
        weight = float(msg.text.strip().replace(",", "."))
    except ValueError:
        await msg.answer("Введи число, например: 82.5")
        return
    await state.update_data(weight=weight)
    await msg.answer("Рост (см)? Например: 180")
    await state.set_state(OnboardingState.height)


@router.message(OnboardingState.height)
async def onboard_height(msg: Message, state: FSMContext):
    try:
        height = float(msg.text.strip())
    except ValueError:
        await msg.answer("Введи число, например: 180")
        return
    await state.update_data(height=height)
    await msg.answer(
        "Какая у тебя цель?\n\n"
        "1 — Похудеть\n"
        "2 — Набрать мышечную массу\n"
        "3 — Поддержать форму"
    )
    await state.set_state(OnboardingState.goal)


@router.message(OnboardingState.goal)
async def onboard_goal(msg: Message, state: FSMContext):
    goals = {"1": "lose_weight", "2": "gain_muscle", "3": "maintain"}
    goal_names = {"lose_weight": "похудеть", "gain_muscle": "набрать мышечную массу", "maintain": "поддержать форму"}
    goal = goals.get(msg.text.strip(), "maintain")

    data = await state.get_data()
    await upsert_user(
        msg.from_user.id,
        name=data["name"],
        age=data["age"],
        weight_kg=data["weight"],
        height_cm=data["height"],
        goal=goal,
    )
    await state.clear()

    await msg.answer(
        f"✅ Отлично, {data['name']}!\n\n"
        f"Записал: {data['age']} лет, {data['weight']} кг, {data['height']} см\n"
        f"Цель: {goal_names[goal]}\n\n"
        "Теперь я буду следить за твоими тренировками, питанием и активностью.\n"
        "Подключи Fitbit командой /fitbit",
        reply_markup=main_menu()
    )


@router.message(Command("profile"))
async def cmd_profile(msg: Message):
    from db.database import get_user
    user = await get_user(msg.from_user.id)
    if not user:
        await msg.answer("Сначала пройди регистрацию /start")
        return
    goal_names = {"lose_weight": "похудеть", "gain_muscle": "набрать массу", "maintain": "поддержать форму"}
    goal = goal_names.get(user.get("goal", ""), user.get("goal", "—"))
    fitbit_status = "✅ подключён" if user.get("fitbit_token") else "❌ не подключён"
    await msg.answer(
        f"👤 *{user.get('name', '—')}*\n"
        f"🎂 {user.get('age', '—')} лет\n"
        f"⚖️ {user.get('weight_kg', '—')} кг, {user.get('height_cm', '—')} см\n"
        f"🎯 Цель: {goal}\n"
        f"⌚ Fitbit: {fitbit_status}",
        parse_mode="Markdown"
    )
