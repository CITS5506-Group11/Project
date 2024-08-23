import time, smbus2, bme280, requests, sqlite3, threading, board, busio
from requests.exceptions import RequestException
import adafruit_ccs811

DB_NAME = 'securasense.db'
TVOC_THRESHOLD = 150
ECO2_THRESHOLD = 1000
WORKING_INTERVAL = 10
BME280_ADDRESS = 0x76
outdoor_ip = None


def init_sensors():
    bus = smbus2.SMBus(1)
    params = bme280.load_calibration_params(bus, BME280_ADDRESS)
    i2c = busio.I2C(board.SCL, board.SDA)
    ccs811 = adafruit_ccs811.CCS811(i2c)
    while not ccs811.data_ready:
        time.sleep(1)
    return bus, params, ccs811


def init_db():
    conn = sqlite3.connect(DB_NAME)
    with conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS sensor_data (timestamp TEXT, indoor_temp REAL, indoor_pressure REAL, 
                        indoor_humidity REAL, indoor_eco2 REAL, indoor_tvoc REAL, outdoor_temp REAL, outdoor_pressure REAL, 
                        outdoor_humidity REAL)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS notifications (timestamp TEXT, message TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, secure_mode INTEGER DEFAULT 0)''')
        conn.execute('INSERT OR IGNORE INTO settings (id, secure_mode) VALUES (1, 0)')
    return conn


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


def insert_sensor_data(cursor, indoor, outdoor=None):
    cursor.execute('''INSERT INTO sensor_data (timestamp, indoor_temp, indoor_pressure, indoor_humidity, indoor_eco2, 
                    indoor_tvoc, outdoor_temp, outdoor_pressure, outdoor_humidity) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                   (time.strftime('%Y-%m-%d %H:%M:%S'), *indoor, *(outdoor or (None, None, None))))


def is_security_mode_active(cursor):
    cursor.execute('SELECT secure_mode FROM settings WHERE id = 1')
    return cursor.fetchone()[0] == 1


def insert_notification(cursor, message):
    print(message)
    cursor.execute('INSERT INTO notifications (timestamp, message) VALUES (?, ?)',
                   (time.strftime('%Y-%m-%d %H:%M:%S'), message))


def main():
    global outdoor_ip
    bus, params, ccs811 = init_sensors()
    conn = init_db()
    cursor = conn.cursor()

    threading.Thread(target=find_outdoor_sensor, daemon=True).start()

    try:
        while True:
            indoor = bme280.sample(bus, BME280_ADDRESS, params)
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

            insert_sensor_data(cursor, (indoor_temp, indoor_pres, indoor_hum, indoor_eco2, indoor_tvoc), (outdoor_temp, outdoor_pres, outdoor_hum))

            if is_security_mode_active(cursor) and (indoor_tvoc > TVOC_THRESHOLD or indoor_eco2 > ECO2_THRESHOLD):
                insert_notification(cursor, "Warning: Potential smoke/fire detected!")

            conn.commit()
            time.sleep(WORKING_INTERVAL)

    except (KeyboardInterrupt, Exception) as e:
        print(f"Program stopped: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
