from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Функция для создания главного меню
def main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("📚 Download Tests"), KeyboardButton("📝 Download Answers")],
            [KeyboardButton("❓ Ask a Question"), KeyboardButton("ℹ️ About Us")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard
