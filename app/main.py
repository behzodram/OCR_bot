import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import easyocr
from PIL import Image
import io
from config import BOT_TOKEN

# Logger sozlash
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

# OCR reader yaratish (o'zbek va ingliz tillari)
reader = easyocr.Reader(['uz', 'en'])

# /start buyrug'i
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Rasmingizni yuboring, men undagi matnni ajratib beraman.")

# Rasmni qabul qilish va OCR ishlatish
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()

    # PIL Image sifatida ochish
    img = Image.open(io.BytesIO(photo_bytes))

    # OCR ishlatish
    result = reader.readtext(photo_bytes)

    # Natijani birlashtirish
    text = "\n".join([res[1] for res in result]) if result else "Matn topilmadi."

    await update.message.reply_text(text)

# Botni ishga tushurish
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    print("Bot ishga tushdi...")
    app.run_polling()
