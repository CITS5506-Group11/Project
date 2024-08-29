import sqlite3, glob, os, pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters

TOKEN = "7204329201:AAHkpQ2TWtyDGz0wVYg4"
video_dir = "/tmp"

conn = sqlite3.connect('securasense.db')
chat_ids = set()
USER_INPUT_STAGE = {}


def get_secure_mode_status():
    return conn.execute('SELECT secure_mode FROM settings WHERE id = 1').fetchone()[0]


def set_secure_mode_status(status):
    conn.execute('UPDATE settings SET secure_mode = ? WHERE id = 1', (status,))
    conn.commit()


def build_keyboard():
    secure_mode = get_secure_mode_status()
    buttons = [
        [InlineKeyboardButton("Atmospheric conditions", callback_data="atmospheric_conditions")],
        [InlineKeyboardButton("Historic atmospheric conditions", callback_data="historic_conditions")],
        [InlineKeyboardButton("Create a notification", callback_data="create_notification")],
        [InlineKeyboardButton("Deactivate secure mode" if secure_mode else "Activate secure mode", callback_data="toggle_secure_mode")]
    ]
    if secure_mode:
        buttons.append([InlineKeyboardButton("Watch camera", callback_data="watch_camera")])
    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context: CallbackContext):
    chat_ids.add(update.message.chat_id)
    await update.message.reply_text("Welcome! Please, choose an option:", reply_markup=build_keyboard())


async def menu_buttons(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat_id if query else update.message.chat_id

    if query:
        await query.answer()
        chat_ids.add(chat_id)

    try:
        if query and query.data:
            if query.data == "toggle_secure_mode":
                set_secure_mode_status(not get_secure_mode_status())
                await query.edit_message_text(f"Secure mode {'activated' if get_secure_mode_status() else 'deactivated'}.", reply_markup=build_keyboard())
            elif query.data == "watch_camera":
                await query.edit_message_text("Loading live video, please wait...")
                await query.message.reply_video(video=open(max(glob.glob(os.path.join(video_dir, "live_*.mp4")), key=os.path.getmtime), 'rb'))
                await query.message.reply_text("Please, choose an option:", reply_markup=build_keyboard())
            elif query.data == "atmospheric_conditions":
                await send_atmospheric_conditions(query.message)
                await query.message.reply_text("Please, choose an option:", reply_markup=build_keyboard())
            elif query.data == "historic_conditions":
                await show_historic_conditions_menu(query.message)
            elif query.data.startswith("historic_"):
                await send_historic_conditions(query, query.data.split("_")[1])
            elif query.data == "create_notification":
                USER_INPUT_STAGE[chat_id] = "waiting_for_threshold"
                await query.message.reply_text("Enter 'indoor' or 'outdoor' followed by the temperature threshold. For example, 'indoor > 25' or 'outdoor < 18'.")
        else:
            if chat_id in USER_INPUT_STAGE:
                user_input = update.message.text

                if USER_INPUT_STAGE[chat_id] == "waiting_for_threshold":
                    if ('indoor >' in user_input or 'indoor <' in user_input or 'outdoor >' in user_input or 'outdoor <' in user_input):
                        USER_INPUT_STAGE[chat_id] = "waiting_for_text"
                        context.user_data['threshold'] = user_input
                        await update.message.reply_text("Threshold accepted. Now, enter the notification text.")
                    else:
                        await update.message.reply_text("Invalid format. Please enter 'indoor' or 'outdoor' followed by the temperature threshold, e.g., 'indoor > 25' or 'outdoor < 18'.")
                elif USER_INPUT_STAGE[chat_id] == "waiting_for_text":
                    threshold = context.user_data.get('threshold')
                    notification_text = user_input

                    conn.execute('INSERT INTO user_notifications (chat_id, threshold, text) VALUES (?, ?, ?)',(chat_id, threshold, notification_text))
                    conn.commit()

                    await update.message.reply_text("Notification created successfully.")
                    del USER_INPUT_STAGE[chat_id]
                    await update.message.reply_text("Please, choose an option:", reply_markup=build_keyboard())
            else:
                await query.message.reply_text("Please, choose an option:", reply_markup=build_keyboard())

    except Exception as e:
        print(e)
        await query.message.reply_text("An error occurred. Please try again.")
        await query.message.reply_text("Please, choose an option:", reply_markup=build_keyboard())


async def send_atmospheric_conditions(message):
    data = conn.execute('SELECT timestamp, indoor_temp, indoor_pressure, indoor_humidity, indoor_eco2, indoor_tvoc, outdoor_temp, outdoor_pressure, outdoor_humidity FROM sensor_data ORDER BY timestamp DESC LIMIT 1').fetchone()
    if data:
        response = (f"{data[0]}\n"
                    f"Indoor Temp: {data[1]:.2f}°C\n"
                    f"Indoor Pressure: {data[2]:.2f} hPa\n"
                    f"Indoor Humidity: {data[3]:.2f}%\n"
                    f"Indoor eCO2: {data[4]:.2f} ppm\n"
                    f"Indoor TVOC: {int(data[5])} ppb\n"
                    f"Outdoor Temp: {data[6]:.2f}°C\n"
                    f"Outdoor Pressure: {data[7]:.2f} hPa\n"
                    f"Outdoor Humidity: {data[8]:.2f}%")
        await message.reply_text(response)
    else:
        await message.reply_text("No atmospheric data available.")


async def show_historic_conditions_menu(message):
    buttons = [
        [InlineKeyboardButton("Hour", callback_data="historic_hour")],
        [InlineKeyboardButton("Day", callback_data="historic_day")],
        [InlineKeyboardButton("Week", callback_data="historic_week")],
        [InlineKeyboardButton("Month", callback_data="historic_month")]
    ]
    await message.reply_text("Select the period for the historic data:", reply_markup=InlineKeyboardMarkup(buttons))


async def generate_historic_report(period: str):
    f = ""
    if period == "hour":
        f = "%Y-%m-%d %H:00:00"
    elif period == "day":
        f = "%Y-%m-%d"
    elif period == "week":
        f = "%Y-%W"
    elif period == "month":
        f = "%Y-%m"

    query_sql = f'''
    SELECT strftime('{f}', timestamp) as period,
           avg(indoor_temp) as avg_indoor_temp,
           avg(indoor_pressure) as avg_indoor_pressure,
           avg(indoor_humidity) as avg_indoor_humidity,
           avg(indoor_eco2) as avg_indoor_eco2,
           avg(indoor_tvoc) as avg_indoor_tvoc,
           avg(outdoor_temp) as avg_outdoor_temp,
           avg(outdoor_pressure) as avg_outdoor_pressure,
           avg(outdoor_humidity) as avg_outdoor_humidity
    FROM sensor_data
    GROUP BY period
    ORDER BY period DESC
    '''

    df = pd.read_sql_query(query_sql, conn)
    file_path = f"/tmp/historic_conditions_{period}.csv"
    df.to_csv(file_path, index=False)
    return file_path


async def send_historic_conditions(query: Update, period: str):
    file_path = await generate_historic_report(period)
    await query.message.reply_document(document=open(file_path, 'rb'), filename=f"historic_conditions_{period}.csv")
    await query.message.reply_text("Please, choose an option:", reply_markup=build_keyboard())


async def send_notifications(context: CallbackContext):
    if not chat_ids:
        return
    cursor = conn.execute('SELECT id, timestamp, message, link FROM notifications')
    notifications = cursor.fetchall()
    for notification in notifications:
        for chat_id in chat_ids:
            await context.bot.send_message(chat_id=chat_id, text=f"{notification[1]}\n{notification[2]}")
            if notification[3]:
                await context.bot.send_video(chat_id=chat_id, video=open(notification[3], 'rb'))

        conn.execute('DELETE FROM notifications WHERE id = ?', (notification[0],))

    conn.commit()
    if notifications:
        for chat_id in chat_ids:
            await context.bot.send_message(chat_id=chat_id, text="Please, choose an option:", reply_markup=build_keyboard())


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_buttons))
    job_queue = app.job_queue
    job_queue.run_repeating(send_notifications, interval=5, first=5)
    app.run_polling()
    conn.close()


if __name__ == "__main__":
    main()
