import sqlite3, glob, os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, CallbackQueryHandler

TOKEN = "7204329201:AAFzn6CPmvSnJ9VtT_j5xI1sDu96dCwfPuE"
video_dir = "/tmp"

conn = sqlite3.connect('securasense.db')


def get_secure_mode_status():
    return conn.execute('SELECT secure_mode FROM settings WHERE id = 1').fetchone()[0]


def set_secure_mode_status(status):
    conn.execute('UPDATE settings SET secure_mode = ? WHERE id = 1', (status,))
    conn.commit()


def build_keyboard():
    secure_mode = get_secure_mode_status()
    buttons = [[InlineKeyboardButton("Deactivate secure mode" if secure_mode else "Activate secure mode", callback_data="toggle_secure_mode")]]
    if secure_mode:
        buttons.append([InlineKeyboardButton("Watch camera", callback_data="watch_camera")])
    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome! Please, choose an option:", reply_markup=build_keyboard())


async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == "toggle_secure_mode":
        set_secure_mode_status(not get_secure_mode_status())
        await query.edit_message_text(f"Secure mode {'activated' if get_secure_mode_status() else 'deactivated'}.", reply_markup=build_keyboard())
    elif query.data == "watch_camera":
        await query.edit_message_text("Loading live video, please wait...")
        await query.message.reply_video(video=open(max(glob.glob(os.path.join(video_dir, "live_*.mp4")), key=os.path.getmtime), 'rb'))
        await query.message.reply_text("Please, choose an option:", reply_markup=build_keyboard())


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()
    conn.close()


if __name__ == "__main__":
    main()
