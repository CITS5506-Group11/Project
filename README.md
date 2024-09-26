# Integrated Smart Home Monitoring and Security System

## CITS5506 Group11 members

| UWA ID  | Name | Github Username |
|---------|------|-----------------|
|10994619 |Jay Lee|10994619|
|23884492 |Zihan Wu|Zihan22|
|23824629 |Gawen Hei|CallMeHeiSir|
|22496593 |Jordan Rigden|jordanrigden|
|24090236 |Konstantin Tagintsev|ktagintsev|

## Project Overview

The system aims to enhance home security and environmental monitoring by integrating a variety of sensors and communication modules. The system is controlled via a Telegram bot, offering real-time updates and remote management. The system continuously monitors environmental factors like temperature, pressure, humidity, and carbon dioxide levels while also ensuring security through real-time surveillance.

# How-To Guide

## Hardware Setup

### Indoor

1. **Components Required**:
   - Raspberry Pi
   - Raspberry Pi Camera
   - CCS811 CO2 Sensor
   - BME280 Sensor (temperature, pressure, humidity)
   - Breadboard and connectors
   - Power adapter

2. **Connections**:
   - Connect the BME280 and CCS811 sensors to the Raspberry Pi using the 3.3V power and ground pins.
   - Connect Pin 2 on the Raspberry Pi to the SDA pin of both sensors, and Pin 3 on the Raspberry Pi to the SCL pin of both sensors.
   - Connect the Wake pin of the CCS811 sensor to Ground to keep the sensor active.
   - Attach the Raspberry Pi Camera to the camera port.
   - Plug in the Raspberry Pi to power.

### Outdoor

1. **Components Required**:
   - TTGO T-Beam (ESP32 with Wi-Fi)
   - BME280 Sensor (temperature, pressure, humidity)
   - Breadboard Adapter for TTGO T-Beam
   - Breadboard and connectors
   - Battery for power

2. **Connections**:
   - Connect the BME280 sensor’s 3.3V, GND, SDA, and SCL pins to the corresponding pins on the TTGO T-Beam Adapter.

## Software Installation

### Indoor (Raspberry Pi)

1. **Download the `indoor.py` and `bot.py` scripts from GitHub**:
   - [https://github.com/CITS5506-Group11/Project](https://github.com/CITS5506-Group11/Project)

2. **Configure the Telegram Bot and update the `bot.py`**:
   - Open Telegram and search for BotFather.
   - Start a conversation with BotFather by typing `/start` to begin and `/newbot` to create a new bot.
   - BotFather will provide an API Token. Copy this token.
   - Replace the Telegram token in `bot.py` with yours.

3. **Install Python 3 and necessary libraries**:
   - `sudo apt-get update`
   - `sudo apt-get install python3-pip`
   - `pip3 install sqlite3 picamera requests python-telegram-bot`

4. **Use the crontab feature to auto-run the `indoor.py` and `bot.py` scripts on boot**:
   - Run `crontab -e`
   - Add the following lines:
     ```
     @reboot python3 /path/to/indoor.py &
     @reboot python3 /path/to/bot.py &
     ```
   - Replace `/path/to/` with the actual path to the `indoor.py` and `bot.py` scripts.

5. **Reboot the Raspberry Pi** to ensure the scripts auto-run.

### Outdoor (TTGO T-Beam)

1. **Install MicroPython**:
   - Download and flash MicroPython to the ESP32 using a terminal:
     ```
     esptool.py --chip esp32 erase_flash
     esptool.py --chip esp32 write_flash -z 0x1000 micropython.bin
     ```

2. **Download and update `outdoor.py`**:
   - Download the `outdoor.py` from [https://github.com/CITS5506-Group11/Project](https://github.com/CITS5506-Group11/Project)
   - Open the `outdoor.py` script and update the Wi-Fi SSID and password in the code.

3. **Use the Thonny IDE** to upload the `outdoor.py` script to the TTGO T-Beam.

## Running

Once the hardware is set up and the necessary scripts have been uploaded as described in the Software Installation section, the system is ready to operate.

1. **Indoor (Raspberry Pi)**:
   - After rebooting the Raspberry Pi, the `indoor.py` and `bot.py` scripts will run automatically due to the crontab setup.

2. **Outdoor (TTGO T-Beam)**:
   - Once powered on or restarted, the `outdoor.py` script will automatically start on the TTGO T-Beam.

3. **Telegram Bot**:
   - Open the Telegram app and interact with the bot by typing `/start`. This will display the interface menu for further interaction.

