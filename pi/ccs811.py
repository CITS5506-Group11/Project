import time
import board
import busio
import adafruit_ccs811

# Initialize I2C and CCS811
i2c = busio.I2C(board.SCL, board.SDA)
ccs811 = adafruit_ccs811.CCS811(i2c)

# Set your detection thresholds (example values)
TVOC_THRESHOLD = 150  # Example threshold in ppb (adjust based on testing)
ECO2_THRESHOLD = 1000  # Example threshold in ppm (adjust based on testing)

# Wait for the sensor to be ready
while not ccs811.data_ready:
    print("Waiting for sensor to stabilize...")
    time.sleep(1)

print("Sensor is ready.")

# Main loop to monitor air quality
while True:
    try:
        # Get the current readings
        eco2 = ccs811.eco2
        tvoc = ccs811.tvoc

        # Print the readings
        print(f"eCO2: {eco2} ppm, TVOC: {tvoc} ppb")

        # Check if readings exceed thresholds
        if tvoc > TVOC_THRESHOLD or eco2 > ECO2_THRESHOLD:
            print("Warning: Potential smoke/fire detected!")
            # Trigger an alert (e.g., sound an alarm, send a notification)

    except RuntimeError:
        print("Error reading from sensor")
    
    time.sleep(2)
