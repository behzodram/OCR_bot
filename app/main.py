import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image
import pytesseract
from config import BOT_TOKEN, BOT_USERNAME
import io
import json
import os

# Logger
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# Foydalanuvchilarni saqlash fayli
USERS_FILE = "users.json"

# Foydalanuvchilarni yuklash yoki bo'sh set yaratish
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r") as f:
        users = set(json.load(f))
else:
    users = set()

# Bot username (bu yerga sizning bot username kiradi, @ bilan)

# /start buyrug'i
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    users.add(user_id)  # set takroriy ID ni qo‘shmaydi

    # Saqlash
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f)

    await update.message.reply_text("Salom! Rasmingizni yuboring, men undagi matnni ajratib beraman.\n\n/help buyrug'ini yozib, yordam olishingiz mumkin.")

# /stats buyrug'i
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Bot foydalanuvchilari soni: {len(users)}")

# /help buyrug'i
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Bot quyidagi buyruqlarni qo‘llab-quvvatlaydi:\n\n"
        "/start - Botni ishga tushirish va matn ajratish uchun tayyorlash\n"
        "/stats - Bot foydalanuvchilari sonini ko‘rish\n"
        "/share - Bot username’ini nusxa olish\n"
        "/help - Bu yordam oynasini ko‘rish"
    )
    await update.message.reply_text(help_text)

# /share buyrug'i
async def share(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Bot username’i:\n{BOT_USERNAME}\n\n"
        "Username’ni nusxa olish uchun shu matnni tanlab copy qiling."
    )


# Rasmni qabul qilish va Tesseract OCR
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()

    img = Image.open(io.BytesIO(photo_bytes))

    # OCR ishlatish (o‘zbek va ingliz tillari)
    text = pytesseract.image_to_string(img, lang='uz+eng')

    if not text.strip():
        text = "Matn topilmadi."

    await update.message.reply_text(text)

# Bot ishga tushurish
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("share", share))  # <-- Qo'shildi
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    print("Bot ishga tushdi...")
    app.run_polling()
