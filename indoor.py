import time, smbus2, bme280, requests, sqlite3, threading, board, busio
from requests.exceptions import RequestException
import adafruit_ccs811

bus = smbus2.SMBus(1)
params = bme280.load_calibration_params(bus, 0x76)
i2c = busio.I2C(board.SCL, board.SDA)
ccs811 = adafruit_ccs811.CCS811(i2c)
outdoor_ip = None

conn = sqlite3.connect('data.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS data
             (timestamp TEXT, indoor_temp REAL, indoor_pressure REAL, indoor_humidity REAL,
              indoor_eco2 REAL, indoor_tvoc REAL,
              outdoor_temp REAL, outdoor_pressure REAL, outdoor_humidity REAL)''')
conn.commit()

while not ccs811.data_ready:
    print("Waiting for CCS811 sensor to stabilize...")
    time.sleep(1)

print("CCS811 sensor is ready.")

def find_outdoor_sensor():
    global outdoor_ip
    print("Searching for outdoor sensor...")
    while True:
        for i in range(1, 255):
            try:
                r = requests.get(f'http://192.168.1.{i}/data', timeout=0.5)
                if r.status_code == 200:
                    outdoor_ip = f"192.168.1.{i}"
                    print(f"Outdoor sensor found at {outdoor_ip}")
                    return
            except RequestException:
                continue
        time.sleep(10)

threading.Thread(target=find_outdoor_sensor, daemon=True).start()

while True:
    try:
        indoor = bme280.sample(bus, 0x76, params)
        indoor_temp, indoor_pres, indoor_hum = indoor.temperature, indoor.pressure, indoor.humidity
        indoor_eco2, indoor_tvoc = ccs811.eco2, ccs811.tvoc

        outdoor_temp = outdoor_pres = outdoor_hum = None
        if outdoor_ip:
            try:
                r = requests.get(f'http://{outdoor_ip}/data', timeout=0.5)
                if r.status_code == 200:
                    outdoor_data = r.json()
                    outdoor_temp, outdoor_pres, outdoor_hum = outdoor_data['temperature'], outdoor_data['pressure'], outdoor_data['humidity']
            except RequestException:
                outdoor_ip = None
                threading.Thread(target=find_outdoor_sensor, daemon=True).start()

        print(f"Indoor: {indoor_temp:.2f} °C, {indoor_pres:.2f} hPa, {indoor_hum:.2f} %, eCO2: {indoor_eco2} ppm, TVOC: {indoor_tvoc} ppb")
        if outdoor_temp is not None:
            print(f"Outdoor: {outdoor_temp:.2f} °C, {outdoor_pres:.2f} hPa, {outdoor_hum:.2f} %")

        if indoor_tvoc > 150 or indoor_eco2 > 1000:
            print("Warning: Potential smoke/fire detected!")

        c.execute('''INSERT INTO data (timestamp, indoor_temp, indoor_pressure, indoor_humidity,
                                      indoor_eco2, indoor_tvoc,
                                      outdoor_temp, outdoor_pressure, outdoor_humidity)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (time.strftime('%Y-%m-%d %H:%M:%S'), indoor_temp, indoor_pres, indoor_hum,
                   indoor_eco2, indoor_tvoc, outdoor_temp, outdoor_pres, outdoor_hum))
        conn.commit()

        time.sleep(10)
    except (KeyboardInterrupt, Exception) as e:
        print(f"Program stopped: {e}")
        break

conn.close()

