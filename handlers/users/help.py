from aiogram import Router, types
from aiogram.filters.command import Command

router = Router()

@router.message(Command('help'))
async def bot_help(message: types.Message):
    text = (
        "Hello! I’m here to help you prepare for the SAT. Here’s what you can do:\n\n"
        "Main Commands:\n\n"
        "📚 Download Tests – Get SAT practice tests for Math and English.\n\n"
        "📝 Download Answers – Get answer keys for the available tests.\n\n"
        "❓ Ask a Question – Send your question, and we’ll respond as soon as possible.\n\n"
        "ℹ️ About Us – Learn more about our bot and its purpose.\n\n"
        "How to use:\n\n"
        "1. Choose a subject (Math or English).\n"
        "2. Select the test you want to download.\n"
        "3. Receive the file and practice! ✅\n\n"
        "Need more help? Just type /start to return to the main menu anytime."
    )
    await message.answer(text)
