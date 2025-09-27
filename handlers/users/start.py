from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loader import db
from utils.extra_datas import make_title
import os

router = Router()

# === FSM ===
class Registration(StatesGroup):
    full_name = State()
    phone = State()
    age = State()

# === Main Menu Keyboard ===
def main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Download Tests"), KeyboardButton(text="📝 Download Answers")],
            [KeyboardButton(text="❓ Ask a Question"), KeyboardButton(text="ℹ️ About Us")]
        ],
        resize_keyboard=True
    )
    return keyboard

# ===== Folders =====
TESTS_FOLDER = "files/tests"
ANSWERS_FOLDER = "files/answers"

ALLOWED_EXTENSIONS = (".txt", ".png", ".json", ".pdf")
user_files = {}  # ключ: telegram_id, значение: dict с id -> filename

# === START ===
@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    user = await db.select_user(telegram_id=telegram_id)

    if user:
        await message.answer(f"👋 Welcome back, {make_title(user['full_name'])}!", reply_markup=main_menu())
    else:
        await message.answer("🎉 Welcome! Let's get you registered.\n\nPlease enter your full name:")
        await state.set_state(Registration.full_name)

# === Registration Handlers ===
@router.message(Registration.full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📲 Share my phone number", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "Awesome! Now send me your phone number 📞\nYou can type it or just press the button below 👇",
        reply_markup=keyboard
    )
    await state.set_state(Registration.phone)

@router.message(Registration.phone)
async def process_phone(message: types.Message, state: FSMContext):
    if message.contact and message.contact.user_id == message.from_user.id:
        phone = message.contact.phone_number
    else:
        phone = message.text
        if not phone.startswith("+") or not phone[1:].isdigit():
            await message.answer("❌ Invalid phone number format. Try again (example: +123456789).")
            return

    await state.update_data(phone=phone)
    await message.answer("👍 Great! Now send me your age (just a number) 🎂", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.age)

@router.message(Registration.age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Age must be a number. Try again:")
        return

    age = int(message.text)
    await state.update_data(age=age)

    data = await state.get_data()
    telegram_id = message.from_user.id
    full_name = data["full_name"]
    phone = data["phone"]

    try:
        await db.add_user(
            telegram_id=telegram_id,
            full_name=full_name,
            username=message.from_user.username,
            phone=phone,
            age=age
        )
    except Exception:
        await message.answer("⚠️ Oops! Something went wrong while saving your data. Please try again later.")
        return

    await message.answer(
        f"✅ Registration complete! 🎉\n\n👤 Name: {full_name}\n📞 Phone: {phone}\n🎂 Age: {age}",
        reply_markup=main_menu()
    )

# ===== Inline Menu Builder =====
def subject_inline(file_type: str):
    builder = InlineKeyboardBuilder()
    if file_type == "test":
        builder.button(text="🧮 Math", callback_data="subject:test:math")
        builder.button(text="📝 English", callback_data="subject:test:english")
    else:
        builder.button(text="🧮 Math", callback_data="subject:answer:math")
        builder.button(text="📝 English", callback_data="subject:answer:english")
    builder.adjust(2)
    builder.button(text="⬅ Back to Menu", callback_data="back_to_menu")
    return builder

# ===== Download Tests / Answers =====
@router.message(F.text == "📚 Download Tests")
async def download_tests(message: types.Message):
    await message.answer("📄 Which subject test do you want to download?", reply_markup=ReplyKeyboardRemove())
    builder = subject_inline("test")
    await message.answer("Select a subject:", reply_markup=builder.as_markup())

@router.message(F.text == "📝 Download Answers")
async def download_answers(message: types.Message):
    await message.answer("📄 Which subject answers do you want to download?", reply_markup=ReplyKeyboardRemove())
    builder = subject_inline("answer")
    await message.answer("Select a subject:", reply_markup=builder.as_markup())

# ===== Show Files =====
@router.callback_query(F.data.startswith("subject:"))
async def show_files(call: types.CallbackQuery):
    _, file_type, subject = call.data.split(":")
    folder = TESTS_FOLDER if file_type == "test" else ANSWERS_FOLDER
    subject_folder = os.path.join(folder, subject)

    if not os.path.exists(subject_folder) or not os.listdir(subject_folder):
        await call.message.edit_text("❌ No files found for this subject!", reply_markup=None)
        builder = InlineKeyboardBuilder()
        builder.button(text="⬅ Back to Menu", callback_data="back_to_menu")
        await call.message.answer("Choose what to do next:", reply_markup=builder.as_markup())
        await call.answer()
        return

    files = [f for f in os.listdir(subject_folder) if f.lower().endswith(ALLOWED_EXTENSIONS)]
    telegram_id = call.from_user.id
    user_files[telegram_id] = {str(i): f for i, f in enumerate(files)}

    builder = InlineKeyboardBuilder()
    for i, f in enumerate(files):
        builder.button(text=f, callback_data=f"{file_type}:{subject}:{i}")
    builder.button(text="⬅ Back to Menu", callback_data="back_to_menu")
    builder.adjust(1)
    await call.message.edit_text(f"Select the {file_type} you want for {subject.capitalize()} 📄", reply_markup=builder.as_markup())
    await call.answer()

# ===== Send File =====
@router.callback_query(F.data.startswith(("test:", "answer:")))
async def send_file(call: types.CallbackQuery):
    file_type, subject, file_id = call.data.split(":")
    telegram_id = call.from_user.id
    filename = user_files.get(telegram_id, {}).get(file_id)
    if not filename:
        await call.message.answer("❌ File not found!", reply_markup=main_menu())
        await call.answer()
        return

    folder = TESTS_FOLDER if file_type == "test" else ANSWERS_FOLDER
    file_path = os.path.join(folder, subject, filename)

    try:
        await call.message.answer_document(FSInputFile(file_path), caption=f"Here is your {file_type}: {filename} ✅")
    except Exception as e:
        await call.message.answer(f"❌ Failed to send file!\nError: {e}")

    builder = InlineKeyboardBuilder()
    builder.button(text="⬅ Back to Menu", callback_data="back_to_menu")
    await call.message.answer("Choose what to do next:", reply_markup=builder.as_markup())
    await call.answer()

# ===== Back to Menu =====
@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(call: types.CallbackQuery):
    await call.message.edit_text("Main Menu:", reply_markup=None)
    await call.message.answer("Choose what to do next:", reply_markup=main_menu())
    await call.answer()

# ===== Ask a Question / About Us =====
@router.message(F.text == "❓ Ask a Question")
async def ask_question(message: types.Message):
    await message.answer("Send me your question, and we will answer it soon! 📨", reply_markup=ReplyKeyboardRemove())
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅ Back to Menu", callback_data="back_to_menu")
    await message.answer("Back to menu:", reply_markup=builder.as_markup())

@router.message(F.text == "ℹ️ About Us")
async def about_us(message: types.Message):
    await message.answer("We are a cool educational bot! 🎓 Enjoy learning! ✨", reply_markup=ReplyKeyboardRemove())
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅ Back to Menu", callback_data="back_to_menu")
    await message.answer("Back to menu:", reply_markup=builder.as_markup())
