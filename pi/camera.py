from picamera2 import Picamera2
import time
import numpy as np

# Initialize the camera
camera = Picamera2()
camera.start()

# Allow the camera to warm up
time.sleep(2)

# Capture the first frame
first_frame = camera.capture_array()

image_counter = 0  # Counter to create unique filenames

while True:
    # Capture a new frame
    new_frame = camera.capture_array()

    # Calculate the absolute difference between the first frame and the new frame
    diff = np.abs(first_frame.astype(np.int16) - new_frame.astype(np.int16))

    # Sum the differences and calculate the average
    diff_sum = np.sum(diff)
    diff_avg = diff_sum / diff.size

    # Define a threshold to detect movement
    threshold = 20

    if diff_avg > threshold:
        # Movement detected, save the new frame as an image with a unique filename
        filename = f'/home/pi/Desktop/movement_detected_{image_counter}.jpg'
        camera.capture_file(filename)
        print(f"Movement detected! Picture saved as {filename}")
        image_counter += 1  # Increment the counter for the next image

        # Add a delay to prevent multiple images from being saved too quickly
        time.sleep(3)  # Delay for 5 seconds (adjust as needed)

    # Update the first frame to be the current frame for the next iteration
    first_frame = new_frame

    # Pause for a short moment before capturing the next frame
    time.sleep(0.5)

camera.stop()
