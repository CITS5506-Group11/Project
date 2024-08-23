import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, CallbackQueryHandler

TOKEN = "7204329201:AAGbPrA799T1wUJEbxdNlv0DOAykMAIYceA"
DB_NAME = 'securasense.db'

conn = sqlite3.connect(DB_NAME)


def get_secure_mode_status():
    return conn.execute('SELECT secure_mode FROM settings WHERE id = 1').fetchone()[0]


def set_secure_mode_status(status):
    conn.execute('UPDATE settings SET secure_mode = ? WHERE id = 1', (status,))
    conn.commit()


async def start(update: Update, context: CallbackContext):
    print(f"Received /start command from user: {update.message.from_user.username}")
    secure_mode = get_secure_mode_status()
    button_text = "Deactivate secure mode" if secure_mode else "Activate secure mode"
    keyboard = [[InlineKeyboardButton(button_text, callback_data="toggle_secure_mode")]]
    await update.message.reply_text("Welcome! Please choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))


async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    print(f"Button pressed by user: {query.from_user.username} - Data: {query.data}")
    await query.answer()

    new_status = not get_secure_mode_status()
    set_secure_mode_status(new_status)
    button_text = "Deactivate secure mode" if new_status else "Activate secure mode"
    await query.edit_message_text(f"Secure mode {'activated' if new_status else 'deactivated'}.",
                                  reply_markup=InlineKeyboardMarkup(
                                      [[InlineKeyboardButton(button_text, callback_data="toggle_secure_mode")]]))


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()
    conn.close()


if __name__ == "__main__":
    main()
