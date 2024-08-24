import sqlite3, os, threading, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, CallbackQueryHandler
from picamera2 import Picamera2, encoders as enc, outputs as out

TOKEN = ""
DB_NAME = 'securasense.db'
VIDEO_PATH_1 = "/tmp/video1.mp4"
VIDEO_PATH_2 = "/tmp/video2.mp4"

conn = sqlite3.connect(DB_NAME)
cam = Picamera2()

active_video = VIDEO_PATH_1
inactive_video = VIDEO_PATH_2


def get_secure_mode_status():
    return conn.execute('SELECT secure_mode FROM settings WHERE id = 1').fetchone()[0]


def set_secure_mode_status(status):
    conn.execute('UPDATE settings SET secure_mode = ? WHERE id = 1', (status,))
    conn.commit()


def record_in_segments():
    global active_video, inactive_video
    while True:
        cam.configure(cam.create_preview_configuration())
        cam.start()
        cam.start_recording(enc.H264Encoder(10000000), output=out.FfmpegOutput(inactive_video))
        time.sleep(10)  # Record for 10 seconds
        cam.stop_recording()

        # Swap active and inactive videos
        active_video, inactive_video = inactive_video, active_video


def start_recording_thread():
    thread = threading.Thread(target=record_in_segments, daemon=True)
    thread.start()


def build_keyboard():
    secure_mode = get_secure_mode_status()
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Deactivate secure mode" if secure_mode else "Activate secure mode", callback_data="toggle_secure_mode")],
        [InlineKeyboardButton("Watch camera", callback_data="watch_camera")]
    ])


async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome! Please choose an option:", reply_markup=build_keyboard())


async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == "toggle_secure_mode":
        set_secure_mode_status(not get_secure_mode_status())
        await query.edit_message_text(f"Secure mode {'activated' if get_secure_mode_status() else 'deactivated'}.",
                                      reply_markup=build_keyboard())

    elif query.data == "watch_camera":
        await query.edit_message_text("Preparing video, please wait...")
        if os.path.exists(active_video):
            await query.message.reply_video(video=open(active_video, 'rb'))
        await query.message.reply_text("Please choose an option:", reply_markup=build_keyboard())


def main():
    start_recording_thread()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()
    conn.close()


if __name__ == "__main__":
    main()

