import time, smbus2, bme280, requests, sqlite3, threading, board, busio, adafruit_ccs811, os, glob, cv2, re
from picamera2 import Picamera2, encoders as enc, outputs as out
from requests.exceptions import RequestException

# Threshold values for TVOC and eCO2 levels
TVOC_THRESHOLD = 150
ECO2_THRESHOLD = 1000

# Global variables for live video thread, event, outdoor sensor IP, detected movement, and file path
live_video_thread = None
live_video_event = threading.Event()
outdoor_ip = None
detected_movement = None
detected_movement_file_path = None
movement_detection_lock = threading.Lock()
video_dir = "/tmp"

# SQLite connection to the database
conn = sqlite3.connect("securasense.db")
cam = Picamera2()


def init_db():
    """
    Initialize the database with required tables if they do not exist.
    """
    conn.execute('''CREATE TABLE IF NOT EXISTS sensor_data (timestamp TEXT, indoor_temp REAL, indoor_pressure REAL,
                    indoor_humidity REAL, indoor_eco2 REAL, indoor_tvoc REAL, outdoor_temp REAL, outdoor_pressure REAL,
                    outdoor_humidity REAL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, 
                    message TEXT, link TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS user_notifications (chat_id INTEGER, threshold TEXT, text TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, secure_mode INTEGER DEFAULT 0)''')
    conn.execute('INSERT OR IGNORE INTO settings (id, secure_mode) VALUES (1, 0)')
    conn.commit()


def init_sensors():
    """
    Initialize the sensors for indoor environment monitoring.

    Returns:
        tuple: A tuple containing the SMBus object, BME280 calibration parameters, and CCS811 sensor object.
    """
    bus = smbus2.SMBus(1)
    params = bme280.load_calibration_params(bus, 0x76)
    i2c = busio.I2C(board.SCL, board.SDA)
    ccs811 = adafruit_ccs811.CCS811(i2c)
    while not ccs811.data_ready:
        time.sleep(1)
    return bus, params, ccs811


def find_outdoor_sensor():
    """
    Continuously search for the outdoor sensor on the local network.
    """
    global outdoor_ip
    print("Searching for outdoor sensor...")
    while True:
        for i in range(1, 255):
            ip = f'192.168.1.{i}'
            try:
                if requests.get(f'http://{ip}/data', timeout=0.5).status_code == 200:
                    outdoor_ip = ip
                    print(f"Outdoor sensor found at {outdoor_ip}")
                    return
            except RequestException:
                pass
        time.sleep(10)


def insert_sensor_data(indoor, outdoor=None):
    """
    Insert sensor data into the database.

    Args:
        indoor (tuple): A tuple containing indoor sensor data.
        outdoor (tuple, optional): A tuple containing outdoor sensor data. Defaults to None.
    """
    conn.execute('''INSERT INTO sensor_data (timestamp, indoor_temp, indoor_pressure, indoor_humidity, indoor_eco2,
                    indoor_tvoc, outdoor_temp, outdoor_pressure, outdoor_humidity) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (time.strftime('%Y-%m-%d %H:%M:%S'), *indoor, *(outdoor or (None, None, None))))
    conn.commit()


def get_secure_mode_status():
    """
    Get the current status of the secure mode setting.

    Returns:
        int: The secure mode status (0 or 1).
    """
    return conn.execute('SELECT secure_mode FROM settings WHERE id = 1').fetchone()[0]


def insert_notification(message, link=None):
    """
    Insert a notification into the database.

    Args:
        message (str): The notification message.
        link (str, optional): An optional link associated with the notification. Defaults to None.
    """
    print(message)
    conn.execute('INSERT INTO notifications (timestamp, message, link) VALUES (?, ?, ?)',
                 (time.strftime('%Y-%m-%d %H:%M:%S'), message, link))
    conn.commit()


def check_user_notifications(indoor_temp, outdoor_temp):
    """
    Check user-defined notifications and trigger alerts if conditions are met.

    Args:
        indoor_temp (float): The current indoor temperature.
        outdoor_temp (float): The current outdoor temperature.
    """
    for chat_id, threshold, text in conn.execute('SELECT chat_id, threshold, text FROM user_notifications').fetchall():
        match = re.match(r'(indoor|outdoor)\s*([><])\s*(\d+(\.\d+)?)', threshold)
        if not match:
            continue

        condition_type, operator, condition_value = match.groups()[0], match.groups()[1], float(match.groups()[2])

        if (condition_type == 'indoor' and
                ((operator == '>' and indoor_temp > condition_value) or
                 (operator == '<' and indoor_temp < condition_value))):
            insert_notification(f"Alert: {text}. Indoor temperature {indoor_temp:.2f} °C")
            conn.execute('DELETE FROM user_notifications WHERE chat_id = ?', (chat_id,))

        elif (condition_type == 'outdoor' and outdoor_temp is not None and
              ((operator == '>' and outdoor_temp > condition_value) or
               (operator == '<' and outdoor_temp < condition_value))):
            insert_notification(f"Alert: {text}. Outdoor temperature {outdoor_temp:.2f} °C")
            conn.execute('DELETE FROM user_notifications WHERE chat_id = ?', (chat_id,))

    conn.commit()


def detect_movement():
    """
    Detect movement in the recorded video and update the detected movement status.
    """
    global detected_movement, detected_movement_file_path

    with movement_detection_lock:
        file_path = max(glob.glob(os.path.join(video_dir, "live_*.mp4")), key=os.path.getmtime)

        if file_path == detected_movement_file_path:
            return

        cap = cv2.VideoCapture(file_path)
        first_frame = None

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (21, 21), 0)
            if first_frame is None:
                first_frame = gray
                continue

            contours, _ = cv2.findContours(cv2.threshold(cv2.absdiff(first_frame, gray), 25, 255, cv2.THRESH_BINARY)[1],
                                           cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if any(cv2.contourArea(c) >= 1000 for c in contours):
                detected_movement_file_path = file_path
                new_file_path = file_path.replace("live_", "detected_movement_")
                os.rename(file_path, new_file_path)
                detected_movement = ("Movement detected!", new_file_path)
                break

        cap.release()


def delete_old_video():
    """
    Delete old video files to manage storage space.
    """
    videos = sorted([f for f in os.listdir(video_dir) if f.startswith("live") and f.endswith(".mp4")])
    while len(videos) > 3:
        os.remove(os.path.join(video_dir, videos.pop(0)))


def record_and_manage_video():
    """
    Record and manage video, including movement detection and old video deletion.
    """
    detect_movement_thread = None

    while live_video_event.is_set():
        cam.configure(cam.create_preview_configuration())
        cam.start()
        cam.start_recording(enc.H264Encoder(10000000), output=out.FfmpegOutput(os.path.join(video_dir, "recording.mp4")))
        time.sleep(10)
        cam.stop_recording()
        os.rename(os.path.join(video_dir, "recording.mp4"), os.path.join(video_dir, f"live_{time.strftime('%Y%m%d_%H%M%S')}.mp4"))

        if detect_movement_thread is None or not detect_movement_thread.is_alive():
            detect_movement_thread = threading.Thread(target=detect_movement, daemon=True)
            detect_movement_thread.start()

        delete_old_video()


def video_security():
    """
    Manage video security based on the secure mode status.
    """
    global live_video_thread
    if get_secure_mode_status():
        if live_video_thread is None or not live_video_thread.is_alive():
            live_video_event.set()
            live_video_thread = threading.Thread(target=record_and_manage_video, daemon=True)
            live_video_thread.start()
    elif live_video_thread is not None and live_video_thread.is_alive():
        live_video_event.clear()
        live_video_thread.join()


def main():
    """
    Main function to initialize sensors, database, and start the monitoring process.
    """
    global outdoor_ip, detected_movement

    # Initialize sensors and database
    bus, params, ccs811 = init_sensors()
    init_db()

    # Start a thread to find the outdoor sensor
    threading.Thread(target=find_outdoor_sensor, daemon=True).start()

    try:
        while True:
            # Sample indoor sensor data
            indoor = bme280.sample(bus, 0x76, params)
            indoor_temp, indoor_pres, indoor_hum = indoor.temperature, indoor.pressure, indoor.humidity
            indoor_eco2, indoor_tvoc = ccs811.eco2, ccs811.tvoc
            print(f"Indoor: {indoor_temp:.2f} °C, {indoor_pres:.2f} hPa, {indoor_hum:.2f} %, eCO2: {indoor_eco2} ppm, TVOC: {indoor_tvoc} ppb")

            # Initialize outdoor sensor data to None
            outdoor_temp = outdoor_pres = outdoor_hum = None

            # If outdoor sensor IP is known, fetch outdoor sensor data
            if outdoor_ip:
                try:
                    outdoor_response = requests.get(f'http://{outdoor_ip}/data', timeout=0.5).json()
                    outdoor_temp, outdoor_pres, outdoor_hum = (outdoor_response['temperature'], outdoor_response['pressure'],
                                                               outdoor_response['humidity'])
                    print(f"Outdoor: {outdoor_temp:.2f} °C, {outdoor_pres:.2f} hPa, {outdoor_hum:.2f} %")
                except RequestException:
                    outdoor_ip = None
                    threading.Thread(target=find_outdoor_sensor, daemon=True).start()

            # Insert sensor data into the database
            insert_sensor_data((indoor_temp, indoor_pres, indoor_hum, indoor_eco2, indoor_tvoc),(outdoor_temp, outdoor_pres, outdoor_hum))

            # Check for high TVOC or eCO2 levels and insert a notification if thresholds are exceeded
            if indoor_tvoc > TVOC_THRESHOLD or indoor_eco2 > ECO2_THRESHOLD:
                insert_notification("Warning: Potential smoke/fire detected!")

            # Check user-defined notifications and trigger alerts if conditions are met
            check_user_notifications(indoor_temp, outdoor_temp)

            # If movement is detected, insert a notification
            if detected_movement:
                insert_notification(*detected_movement)
                detected_movement = None

            # Manage video security based on the secure mode status
            video_security()

            # Wait for 10 seconds before the next iteration
            time.sleep(10)

    except (KeyboardInterrupt, Exception) as e:
        # Handle program interruption or exceptions
        print(f"Program stopped: {e}")
    finally:
        # Close the database connection
        conn.close()


if __name__ == "__main__":
    main()
