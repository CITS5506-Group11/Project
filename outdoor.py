import time, network, socket, bme280, json
from machine import Pin, SoftI2C

# Initialize the BME280 sensor with I2C communication
sensor = bme280.BME280(i2c=SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000), address=0x77)

def connect_wifi(ssid, password):
    """
    Connect to a Wi-Fi network.

    Args:
        ssid (str): The SSID of the Wi-Fi network.
        password (str): The password of the Wi-Fi network.

    Returns:
        str: The IP address assigned to the device.
    """
    station = network.WLAN(network.STA_IF)
    station.active(True)
    station.connect(ssid, password)
    while not station.isconnected():
        time.sleep(1)
    return station.ifconfig()[0]

def get_data():
    """
    Read data from the BME280 sensor and return it as a JSON string.

    Returns:
        str: JSON string containing temperature, pressure, and humidity data.
        If an error occurs, returns a JSON string with the error message.
    """
    try:
        t, p, h = sensor.read_compensated_data()
        return json.dumps({"temperature": t, "pressure": p / 100, "humidity": h})
    except Exception as e:
        return json.dumps({"error": str(e)})

def server():
    """
    Start a simple HTTP server that listens for incoming connections.
    Responds with sensor data in JSON format if the '/data' endpoint is requested.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 80))
    s.listen(5)
    while True:
        conn, _ = s.accept()
        request = conn.recv(1024)
        response = "HTTP/1.1 200 OK\nContent-Type: application/json\n\n" + get_data() if b'/data' in request else "HTTP/1.1 404 NOT FOUND\n\n"
        conn.send(response.encode('utf-8'))
        conn.close()

# Connect to Wi-Fi and print the IP address
ip = connect_wifi('KT', '12345678')
print(f"Access the data at: http://{ip}/data")

# Start the HTTP server
server()