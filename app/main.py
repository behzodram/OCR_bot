import logging, io, os, json, requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from PIL import Image
import pytesseract
from config import BOT_TOKEN, BOT_USERNAME

ADMIN_ID = 961619801
DATA_FILE = "data.json"

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ─────────────────────────── DATA ───────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"groups": {}, "members": {}, "muted": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─────────────────────────── KEYBOARDS ──────────────────────
def groups_keyboard(data, user_id):
    """Barcha guruhlar ro'yxati + MUTE tugmasi"""
    buttons = []
    user_groups = data["members"].get(str(user_id), [])
    is_muted = user_id in data.get("muted", [])

    for gid, ginfo in data["groups"].items():
        joined = gid in user_groups
        label = f"{'✅ ' if joined else ''}{ginfo['name']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"grp_{gid}")])

    mute_label = "🔕 MUTE (yoqilgan)" if is_muted else "🔔 MUTE"
    buttons.append([InlineKeyboardButton(mute_label, callback_data="toggle_mute")])
    return InlineKeyboardMarkup(buttons)

# ─────────────────────────── HELPERS ────────────────────────
async def get_profile_photo_url(bot, user_id: int) -> str | None:
    """Profil rasmini URL sifatida qaytaradi"""
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count == 0:
            return None
        photo = photos.photos[0][-1]
        file = await bot.get_file(photo.file_id)
        return file.file_path
    except Exception:
        return None

async def broadcast_to_group(bot, group_id: str, data: dict,
                              sender_id: int, sender_name: str,
                              text: str = None, photo_bytes: bytes = None,
                              ocr_text: str = None):
    """Guruh a'zolariga xabar yuborish"""
    members = [
        int(uid) for uid, glist in data["members"].items()
        if group_id in glist and int(uid) != sender_id
    ]
    if not members:
        return

    profile_url = await get_profile_photo_url(bot, sender_id)

    for member_id in members:
        if member_id in data.get("muted", []):
            # Muted user: faqat OCR yubor (agar mavjud bo'lsa)
            if ocr_text:
                await bot.send_message(member_id,
                    f"📷 *{sender_name}* (OCR):\n```\n{ocr_text}\n```",
                    parse_mode="Markdown")
            continue

        try:
            # Profil rasmi + ism + guruh nomi sarlavha
            group_name = data["groups"][group_id]["name"]
            header = f"👤 *{sender_name}* › _{group_name}_"

            if photo_bytes:
                # Rasm + OCR natijasi
                caption = header
                if ocr_text:
                    caption += f"\n\n📝 OCR:\n```\n{ocr_text}\n```"
                await bot.send_photo(member_id,
                    photo=io.BytesIO(photo_bytes),
                    caption=caption, parse_mode="Markdown")
            elif text:
                # Matn xabari
                if profile_url:
                    await bot.send_photo(member_id,
                        photo=profile_url,
                        caption=f"{header}\n\n{text}",
                        parse_mode="Markdown")
                else:
                    await bot.send_message(member_id,
                        f"{header}\n\n{text}", parse_mode="Markdown")
        except Exception as e:
            logging.warning(f"Broadcast xatosi {member_id}: {e}")

# ─────────────────────────── COMMANDS ───────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user_id = update.message.from_user.id
    kb = groups_keyboard(data, user_id)
    await update.message.reply_text(
        "👋 Assalom! Quyidagi guruhlardan biriga qo'shiling:\n"
        "_(guruh nomiga bosib kirish/chiqish)_\n\n"
        "🔕 *MUTE* — barcha guruhlar ovozini o'chiradi,\nfaqat OCR ishlaydi.",
        reply_markup=kb, parse_mode="Markdown"
    )

async def addgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Faqat admin guruh qo'sha oladi.")
        return
    if not context.args:
        await update.message.reply_text("Foydalanish: /addgroup <guruh nomi>")
        return

    data = load_data()
    name = " ".join(context.args)
    gid = str(len(data["groups"]) + 1)
    # ID takrorlanmasligi uchun
    while gid in data["groups"]:
        gid = str(int(gid) + 1)

    data["groups"][gid] = {"name": name}
    save_data(data)
    await update.message.reply_text(f"✅ Guruh yaratildi: *{name}* (ID: {gid})",
                                    parse_mode="Markdown")

async def delgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Faqat admin guruhni o'chira oladi.")
        return
    if not context.args:
        await update.message.reply_text("Foydalanish: /delgroup <guruh_id>")
        return

    data = load_data()
    gid = context.args[0]
    if gid not in data["groups"]:
        await update.message.reply_text("❌ Bunday guruh topilmadi.")
        return

    name = data["groups"][gid]["name"]
    del data["groups"][gid]
    # Barcha memberlardan o'chirish
    for uid in data["members"]:
        if gid in data["members"][uid]:
            data["members"][uid].remove(gid)
    save_data(data)
    await update.message.reply_text(f"🗑 Guruh o'chirildi: *{name}*", parse_mode="Markdown")

async def mygroups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user_id = update.message.from_user.id
    kb = groups_keyboard(data, user_id)
    await update.message.reply_text("📋 Guruhlar:", reply_markup=kb)

# ─────────────────────────── CALLBACKS ──────────────────────
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = load_data()

    if query.data == "toggle_mute":
        muted = data.get("muted", [])
        if user_id in muted:
            muted.remove(user_id)
            msg = "🔔 MUTE o'chirildi. Guruh xabarlari qayta keladi."
        else:
            muted.append(user_id)
            msg = "🔕 MUTE yoqildi. Faqat OCR ishlaydi."
        data["muted"] = muted
        save_data(data)
        kb = groups_keyboard(data, user_id)
        await query.edit_message_reply_markup(reply_markup=kb)
        await query.answer(msg, show_alert=True)
        return

    if query.data.startswith("grp_"):
        gid = query.data[4:]
        if gid not in data["groups"]:
            await query.answer("❌ Guruh topilmadi.", show_alert=True)
            return

        uid_str = str(user_id)
        if uid_str not in data["members"]:
            data["members"][uid_str] = []

        if gid in data["members"][uid_str]:
            data["members"][uid_str].remove(gid)
            msg = f"👋 '{data['groups'][gid]['name']}' guruhidan chiqdingiz."
        else:
            data["members"][uid_str].append(gid)
            msg = f"✅ '{data['groups'][gid]['name']}' guruhiga qo'shildingiz!"

        save_data(data)
        kb = groups_keyboard(data, user_id)
        await query.edit_message_reply_markup(reply_markup=kb)
        await query.answer(msg, show_alert=True)

# ─────────────────────────── MESSAGE HANDLERS ───────────────
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    data = load_data()
    uid_str = str(user.id)
    user_groups = data["members"].get(uid_str, [])

    if not user_groups:
        await update.message.reply_text(
            "⚠️ Hech qanday guruhga qo'shilmagansiz.\n/start yozing.")
        return

    name = user.full_name
    text = update.message.text

    for gid in user_groups:
        if gid in data["groups"]:
            await broadcast_to_group(
                context.bot, gid, data,
                sender_id=user.id, sender_name=name, text=text
            )

    await update.message.reply_text("✅ Xabar yuborildi.")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    data = load_data()
    uid_str = str(user.id)
    user_groups = data["members"].get(uid_str, [])

    # Rasmni yuklab olish
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = bytes(await photo_file.download_as_bytearray())

    # OCR
    img = Image.open(io.BytesIO(photo_bytes))
    ocr_text = pytesseract.image_to_string(img, lang='uz+eng').strip()
    if not ocr_text:
        ocr_text = None

    # O'ziga OCR natijasini qaytarish
    if ocr_text:
        await update.message.reply_text(f"📝 OCR natijasi:\n```\n{ocr_text}\n```",
                                        parse_mode="Markdown")
    else:
        await update.message.reply_text("❓ Rasmda matn topilmadi.")

    if not user_groups:
        return

    name = user.full_name
    for gid in user_groups:
        if gid in data["groups"]:
            await broadcast_to_group(
                context.bot, gid, data,
                sender_id=user.id, sender_name=name,
                photo_bytes=photo_bytes, ocr_text=ocr_text
            )

# ─────────────────────────── MAIN ───────────────────────────
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("groups", mygroups))
    app.add_handler(CommandHandler("addgroup", addgroup))
    app.add_handler(CommandHandler("delgroup", delgroup))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    print("Bot ishga tushdi...")
    app.run_polling()