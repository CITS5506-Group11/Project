import time
import smbus2
import bme280

address = 0x76

bus = smbus2.SMBus(1)

calibration_params = bme280.load_calibration_params(bus, address)

def celsius_to_fahrenheit(celsius):
    return (celsius * 9/5) + 32

while True:
    try:
        data = bme280.sample(bus, address, calibration_params)

        temperature_celsius = data.temperature
        pressure = data.pressure
        humidity = data.humidity

        temperature_fahrenheit = celsius_to_fahrenheit(temperature_celsius)

        print("Temperature: {:.2f} °C, {:.2f} °F".format(temperature_celsius, temperature_fahrenheit))
        print("Pressure: {:.2f} hPa".format(pressure))
        print("Humidity: {:.2f} %".format(humidity))

        time.sleep(2)

    except KeyboardInterrupt:
        print('Program stopped')
        break
    except Exception as e:
        print('An unexpected error occurred:', str(e))
        break