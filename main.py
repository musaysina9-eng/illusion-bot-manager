import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler,
    ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
ARCHIVE_CHANNEL_ID = os.getenv("ARCHIVE_CHANNEL_ID")

VIDEO, TITLE, DESCRIPTION, TAGS, GENRE, BPM, KEY, VERSES, CHORUSES, COVER = range(10)


def load_beats():
    try:
        with open("beats.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_beats(beats):
    with open("beats.json", "w", encoding="utf-8") as f:
        json.dump(beats, f, ensure_ascii=False, indent=2)


def is_owner(update):
    return update.effective_user and update.effective_user.id == OWNER_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("این ربات خصوصی است.")
        return
    await update.message.reply_text(
        "سلام! برای ثبت بیت دستور /add را بزن.\n"
        "برای دریافت شناسه تلگرام /id را بزن."
    )


async def get_id(update, context):
    await update.message.reply_text(str(update.effective_user.id))


async def add(update, context):
    if not is_owner(update):
        return ConversationHandler.END

    context.user_data.clear()
    await update.message.reply_text("ویدیوی دمو یا فایل صوتی بیت را بفرست.")
    return VIDEO


async def receive_video(update, context):
    msg = update.message

    if msg.video:
        context.user_data["file_type"] = "video"
        context.user_data["file_id"] = msg.video.file_id
    elif msg.audio:
        context.user_data["file_type"] = "audio"
        context.user_data["file_id"] = msg.audio.file_id
    elif msg.document:
        context.user_data["file_type"] = "document"
        context.user_data["file_id"] = msg.document.file_id
    else:
        await msg.reply_text("لطفاً فایل یا ویدیو بفرست.")
        return VIDEO

    await msg.reply_text("اسم بیت چیه؟")
    return TITLE


async def title(update, context):
    context.user_data["title"] = update.message.text
    await update.message.reply_text("توضیحات بیت؟")
    return DESCRIPTION


async def description(update, context):
    context.user_data["description"] = update.message.text
    await update.message.reply_text("هشتگ‌ها را بفرست.")
    return TAGS


async def tags(update, context):
    context.user_data["tags"] = update.message.text
    await update.message.reply_text("سبک موسیقی چیه؟")
    return GENRE


async def genre(update, context):
    context.user_data["genre"] = update.message.text
    await update.message.reply_text("BPM چند است؟")
    return BPM


async def bpm(update, context):
    context.user_data["bpm"] = update.message.text
    await update.message.reply_text("گام موسیقی (Key) چیه؟")
    return KEY


async def key(update, context):
    context.user_data["key"] = update.message.text
    await update.message.reply_text("چند ورس دارد؟")
    return VERSES


async def verses(update, context):
    context.user_data["verses"] = update.message.text
    await update.message.reply_text("چند کورس دارد؟")
    return CHORUSES


async def choruses(update, context):
    context.user_data["choruses"] = update.message.text

    keyboard = [[
        InlineKeyboardButton("ارسال کاور", callback_data="yes"),
        InlineKeyboardButton("بدون کاور", callback_data="no")
    ]]

    await update.message.reply_text(
        "کاور جداگانه داری؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return COVER


async def cover_choice(update, context):
    query = update.callback_query
    await query.answer()

    if query.data == "yes":
        await query.edit_message_text("عکس کاور را بفرست.")
        return COVER

    context.user_data["cover"] = None
    return await show_preview(query, context)


async def cover_photo(update, context):
    if not update.message.photo:
        await update.message.reply_text("لطفاً عکس بفرست.")
        return COVER

    context.user_data["cover"] = update.message.photo[-1].file_id
    return await show_preview(update, context)


async def show_preview(target, context):
    d = context.user_data

    message = (
        f"پیش‌نمایش بیت:\n\n"
        f"نام: {d['title']}\n"
        f"توضیحات: {d['description']}\n"
        f"هشتگ: {d['tags']}\n"
        f"سبک: {d['genre']}\n"
        f"BPM: {d['bpm']}\n"
        f"Key: {d['key']}\n"
        f"ورس: {d['verses']}\n"
        f"کورس: {d['choruses']}"
    )

    keyboard = [[
        InlineKeyboardButton("تأیید و ذخیره", callback_data="approve"),
        InlineKeyboardButton("لغو", callback_data="reject")
    ]]

    markup = InlineKeyboardMarkup(keyboard)

    if hasattr(target, "edit_message_text"):
        await target.edit_message_text(message, reply_markup=markup)
    else:
        await target.message.reply_text(message, reply_markup=markup)

    return ConversationHandler.END


async def approve(update, context):
    query = update.callback_query
    await query.answer()

    if query.data == "reject":
        context.user_data.clear()
        await query.edit_message_text("ثبت لغو شد.")
        return

    d = context.user_data

    if not ARCHIVE_CHANNEL_ID:
        await query.edit_message_text("شناسه کانال آرشیو تنظیم نشده است.")
        return

    try:
        if d.get("cover"):
            await context.bot.send_photo(
                ARCHIVE_CHANNEL_ID,
                d["cover"],
                caption=d["title"]
            )

        caption = (
            f"{d['title']}\n{d['description']}\n"
            f"{d['tags']}\n{d['genre']} | {d['bpm']} BPM | {d['key']}\n"
            f"ورس: {d['verses']} | کورس: {d['choruses']}"
        )

        if d["file_type"] == "video":
            await context.bot.send_video(
                ARCHIVE_CHANNEL_ID, d["file_id"], caption=caption
            )
        elif d["file_type"] == "audio":
            await context.bot.send_audio(
                ARCHIVE_CHANNEL_ID, d["file_id"], caption=caption
            )
        else:
            await context.bot.send_document(
                ARCHIVE_CHANNEL_ID, d["file_id"], caption=caption
            )

        beats = load_beats()
        record = {
            k: v for k, v in d.items()
            if k != "file_id"
        }
        beats.append(record)
        save_beats(beats)

        await query.edit_message_text("بیت در کانال آرشیو ذخیره شد.")

    except Exception:
        logging.exception("Archive error")
        await query.edit_message_text("ارسال ناموفق بود. تنظیمات را بررسی کن.")

    context.user_data.clear()


async def cancel(update, context):
    context.user_data.clear()
    await update.message.reply_text("لغو شد.")
    return ConversationHandler.END


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN تنظیم نشده است")

    app = Application.builder().token(TOKEN).build()

    conversation = ConversationHandler(
        entry_points=[CommandHandler("add", add)],
        states={
            VIDEO: [MessageHandler(
                filters.VIDEO | filters.AUDIO | filters.Document.ALL,
                receive_video
            )],
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, title)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description)],
            TAGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, tags)],
            GENRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, genre)],
            BPM: [MessageHandler(filters.TEXT & ~filters.COMMAND, bpm)],
            KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, key)],
            VERSES: [MessageHandler(filters.TEXT & ~filters.COMMAND, verses)],
            CHORUSES: [MessageHandler(filters.TEXT & ~filters.COMMAND, choruses)],
            COVER: [
                CallbackQueryHandler(cover_choice, pattern="^(yes|no)$"),
                MessageHandler(filters.PHOTO, cover_photo)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(conversation)
    app.add_handler(CallbackQueryHandler(
        approve, pattern="^(approve|reject)$"
    ))

    app.run_polling()


if __name__ == "__main__":
    main()
