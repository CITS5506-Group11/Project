import time, smbus2, bme280, requests, sqlite3, threading, board, busio, adafruit_ccs811, os, glob, cv2
from picamera2 import Picamera2, encoders as enc, outputs as out
from requests.exceptions import RequestException


TVOC_THRESHOLD = 150
ECO2_THRESHOLD = 1000

live_video_thread = None
live_video_event = threading.Event()
outdoor_ip = None
detected_movement = None
video_dir = "/tmp"

conn = sqlite3.connect("securasense.db")
cam = Picamera2()


def init_db():
    conn.execute('''CREATE TABLE IF NOT EXISTS sensor_data (timestamp TEXT, indoor_temp REAL, indoor_pressure REAL, 
                    indoor_humidity REAL, indoor_eco2 REAL, indoor_tvoc REAL, outdoor_temp REAL, outdoor_pressure REAL, 
                    outdoor_humidity REAL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS notifications (timestamp TEXT, message TEXT, image BLOB)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, secure_mode INTEGER DEFAULT 0)''')
    conn.execute('INSERT OR IGNORE INTO settings (id, secure_mode) VALUES (1, 0)')
    conn.commit()


def init_sensors():
    bus = smbus2.SMBus(1)
    params = bme280.load_calibration_params(bus, 0x76)
    i2c = busio.I2C(board.SCL, board.SDA)
    ccs811 = adafruit_ccs811.CCS811(i2c)
    while not ccs811.data_ready:
        time.sleep(1)
    return bus, params, ccs811


def find_outdoor_sensor():
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
    conn.execute('''INSERT INTO sensor_data (timestamp, indoor_temp, indoor_pressure, indoor_humidity, indoor_eco2, 
                    indoor_tvoc, outdoor_temp, outdoor_pressure, outdoor_humidity) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                   (time.strftime('%Y-%m-%d %H:%M:%S'), *indoor, *(outdoor or (None, None, None))))
    conn.commit()


def get_secure_mode_status():
    return conn.execute('SELECT secure_mode FROM settings WHERE id = 1').fetchone()[0]


def insert_notification(message, image=None):
    print(message)
    conn.execute('INSERT INTO notifications (timestamp, message, image) VALUES (?, ?, ?)',
                   (time.strftime('%Y-%m-%d %H:%M:%S'), message, image))
    conn.commit()


def detect_movement():
    global detected_movement

    cap = cv2.VideoCapture(max(glob.glob(os.path.join(video_dir, "live_*.mp4")), key=os.path.getmtime))
    first_frame = None

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (21, 21), 0)
        if first_frame is None:
            first_frame = gray
            continue

        contours, _ = cv2.findContours(cv2.threshold(cv2.absdiff(first_frame, gray), 25, 255, cv2.THRESH_BINARY)[1], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if any(cv2.contourArea(c) >= 500 for c in contours):
            _, buffer = cv2.imencode('.jpg', frame)
            detected_movement = ("Movement detected!", buffer.tobytes())
            break

    cap.release()


def delete_old_video():
    videos = sorted([f for f in os.listdir(video_dir) if f.startswith("live") and f.endswith(".mp4")])
    while len(videos) > 2:
        os.remove(os.path.join(video_dir, videos.pop(0)))


def record_and_manage_video():
    while live_video_event.is_set():
        cam.configure(cam.create_preview_configuration())
        cam.start()
        cam.start_recording(enc.H264Encoder(10000000), output=out.FfmpegOutput(os.path.join(video_dir, "recording.mp4")))
        time.sleep(10)
        cam.stop_recording()
        os.rename(os.path.join(video_dir, "recording.mp4"), os.path.join(video_dir, f"live_{time.strftime('%Y%m%d_%H%M%S')}.mp4"))
        detect_movement()
        delete_old_video()


def video_security():
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
    global outdoor_ip, detected_movement
    bus, params, ccs811 = init_sensors()
    init_db()

    threading.Thread(target=find_outdoor_sensor, daemon=True).start()

    try:
        while True:
            indoor = bme280.sample(bus, 0x76, params)
            indoor_temp, indoor_pres, indoor_hum = indoor.temperature, indoor.pressure, indoor.humidity
            indoor_eco2, indoor_tvoc = ccs811.eco2, ccs811.tvoc
            print(f"Indoor: {indoor_temp:.2f} °C, {indoor_pres:.2f} hPa, {indoor_hum:.2f} %, eCO2: {indoor_eco2} ppm, TVOC: {indoor_tvoc} ppb")

            outdoor_temp = outdoor_pres = outdoor_hum = None
            if outdoor_ip:
                try:
                    outdoor_response = requests.get(f'http://{outdoor_ip}/data', timeout=0.5).json()
                    outdoor_temp, outdoor_pres, outdoor_hum = outdoor_response['temperature'], outdoor_response['pressure'], outdoor_response['humidity']
                    print(f"Outdoor: {outdoor_temp:.2f} °C, {outdoor_pres:.2f} hPa, {outdoor_hum:.2f} %")
                except RequestException:
                    outdoor_ip = None
                    threading.Thread(target=find_outdoor_sensor, daemon=True).start()

            insert_sensor_data((indoor_temp, indoor_pres, indoor_hum, indoor_eco2, indoor_tvoc), (outdoor_temp, outdoor_pres, outdoor_hum))

            if indoor_tvoc > TVOC_THRESHOLD or indoor_eco2 > ECO2_THRESHOLD:
                insert_notification("Warning: Potential smoke/fire detected!")

            if detected_movement:
                insert_notification(*detected_movement)
                detected_movement = None

            video_security()

            time.sleep(10)

    except (KeyboardInterrupt, Exception) as e:
        print(f"Program stopped: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
