from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums.parse_mode import ParseMode
from aiogram.client.session.middlewares.request_logging import logger

from loader import db, bot
from data.config import ADMINS
from utils.extra_datas import make_title

router = Router()


# === FSM ===
class Registration(StatesGroup):
    full_name = State()
    phone = State()
    age = State()


# === START ===
@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    username = message.from_user.username

    user = await db.get_user_by_telegram_id(telegram_id)

    if user:
        await message.answer(f"Welcome back, {make_title(user['full_name'])}! 👋")
    else:
        await message.answer("Welcome! Let's get you registered.\n\nPlease enter your full name:")
        await state.set_state(Registration.full_name)


# === Full name ===
@router.message(Registration.full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("Great! Now send me your phone number (example: +123456789).")
    await state.set_state(Registration.phone)


# === Phone ===
@router.message(Registration.phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text

    if not phone.startswith("+") or not phone[1:].isdigit():
        await message.answer("❌ Invalid phone number format. Try again (example: +123456789).")
        return

    await state.update_data(phone=phone)
    await message.answer("Nice! Now send me your age (just a number).")
    await state.set_state(Registration.age)


# === Age ===
@router.message(Registration.age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Age must be a number. Try again:")
        return

    age = int(message.text)
    await state.update_data(age=age)

    data = await state.get_data()

    telegram_id = message.from_user.id
    username = message.from_user.username
    full_name = data["full_name"]
    phone = data["phone"]

    try:
        user = await db.add_user(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            phone=phone,
            age=age
        )
    except Exception as error:
        logger.error(error)
        await message.answer("⚠️ Error saving your data. Please try again later.")
        return

    await message.answer(f"✅ Registration complete!\n\n"
                         f"Name: {full_name}\n"
                         f"Phone: {phone}\n"
                         f"Age: {age}")

    # Notify admins
    count = await db.count_users()
    msg = (f"[{make_title(full_name)}](tg://user?id={telegram_id}) registered.\n"
           f"Now {count} users in the database.")

    for admin in ADMINS:
        try:
            await bot.send_message(admin, msg, parse_mode=ParseMode.MARKDOWN_V2)
        except Exception as error:
            logger.info(f"Message not sent to admin {admin}: {error}")

    await state.clear()
