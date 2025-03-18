import time
import json
import os
import paho.mqtt.client as mqtt

# Try to import Raspberry Pi Camera library; if unavailable, use OpenCV for virtual mode
try:
    from picamera import PiCamera
    REAL_CAMERA = True
except ImportError:
    print(" Raspberry Pi Camera module not found! Running in virtual mode...")
    import cv2  # OpenCV for image simulation
    REAL_CAMERA = False

BROKER = "test.mosquitto.org"
TOPIC = "petguardian/camera"
SAVE_DIR = "captured_images"

# Ensure directory exists
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

if REAL_CAMERA:
    camera = PiCamera()
    camera.resolution = (640, 480)

import os

def send_data_to_cloud(image_path):
    """Send camera event metadata to MQTT broker and delete image after sending."""
    client = mqtt.Client()
    client.connect(BROKER)
    payload = json.dumps({
        "sensor": "camera",
        "image_path": image_path,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    client.publish(TOPIC, payload)
    client.disconnect()
    print(f"Sent Camera Data to MQTT Broker: {payload}")

    # Delete image after sending
    try:
        os.remove(image_path)
        print(f"Deleted Image: {image_path}")
    except Exception as e:
        print(f"Error deleting image: {e}")


def capture_image():
    """Captures an image using the camera module or OpenCV."""
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    image_path = f"{SAVE_DIR}/image_{timestamp}.jpg"

    if REAL_CAMERA:
        camera.capture(image_path)
    else:
        cap = cv2.VideoCapture(0)  # Open webcam
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(image_path, frame)
        cap.release()

    print(f" Image Captured: {image_path}")
    send_data_to_cloud(image_path)

def camera_trigger():
    """Continuously checks for an event to trigger the camera."""
    print(" Camera Sensor Active... (Press 'P' to Capture an Image, 'X' to Exit)")

    while True:
        if not REAL_CAMERA:
            import keyboard
            if keyboard.is_pressed('p'):
                capture_image()
            elif keyboard.is_pressed('x'):
                print("Exiting camera sensor.")
                break
        else:
            # On Raspberry Pi, trigger capture based on sound/motion event
            time.sleep(5)  # Placeholder for real event detection

if __name__ == "__main__":
    try:
        camera_trigger()
    except KeyboardInterrupt:
        print("\n Stopping camera sensor...")
