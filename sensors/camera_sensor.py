import os
import time
import json
import base64
import uuid
import paho.mqtt.client as mqtt

# Azure IoT and Cosmos DB
from azure.iot.device import IoTHubDeviceClient, Message
from azure.cosmos import CosmosClient

# Try to import Raspberry Pi Camera library
try:
    from picamera import PiCamera
    REAL_CAMERA = True
except ImportError:
    import cv2
    REAL_CAMERA = False

# MQTT broker details
BROKER = "broker.hivemq.com"
TOPIC = "petguardian/camera"

# Project-based image directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVE_DIR = os.path.join(BASE_DIR, "data", "images")
os.makedirs(SAVE_DIR, exist_ok=True)

# Azure connection info
IOTHUB_CONNECTION_STRING = "HostName=IoTPawTrack.azure-devices.net;DeviceId=collar01;SharedAccessKey=ShzFs2jgI06rAjksNrEst8Byb8x2ljbHrBGYT+raQ1E="
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

# Initialize PiCamera if available
if REAL_CAMERA:
    camera = PiCamera()
    camera.resolution = (640, 480)

# Connect to Cosmos DB
cosmos_client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
database = cosmos_client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

def encode_image_to_base64(image_path):
    """Convert a saved image file to a base64 string."""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

def send_data_all(image_path):
    """Send image data to MQTT, Azure IoT Hub, and Cosmos DB, then delete the image file."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    encoded_img = encode_image_to_base64(image_path)

    payload_dict = {
        "sensor": "camera",
        "timestamp": timestamp,
        "image_base64": encoded_img
    }
    payload_json = json.dumps(payload_dict)

    # Send to MQTT broker
    try:
        mqtt_client = mqtt.Client()
        mqtt_client.connect(BROKER)
        mqtt_client.publish(TOPIC, payload_json)
        mqtt_client.disconnect()
        print("Image sent to MQTT broker.")
    except Exception as e:
        print(f"MQTT error: {e}")

    # Send to Azure IoT Hub
    try:
        iot_client = IoTHubDeviceClient.create_from_connection_string(IOTHUB_CONNECTION_STRING)
        message = Message(payload_json)
        iot_client.send_message(message)
        iot_client.disconnect()
        print("Image sent to Azure IoT Hub.")
    except Exception as e:
        print(f"IoT Hub error: {e}")

    # Save to Cosmos DB
    try:
        encoded_doc = base64.b64encode(payload_json.encode('utf-8')).decode('utf-8')
        doc = {
            "id": str(uuid.uuid4()),
            "sensor": "camera",
            "timestamp": timestamp,
            "image_base64": encoded_img,
            "deviceId": "collar01"
        }
        container.create_item(body=doc)
        print("Image saved to Cosmos DB.")
    except Exception as e:
        print(f"Cosmos DB error: {e}")

    # Delete image file
    try:
        os.remove(image_path)
        print(f"Deleted image: {image_path}")
    except Exception as e:
        print(f"Error deleting image: {e}")

def capture_image():
    """Capture an image using PiCamera or OpenCV (test mode), then send it to all targets."""
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    image_path = os.path.join(SAVE_DIR, f"image_{timestamp}.jpg")

    if REAL_CAMERA:
        camera.capture(image_path)
    else:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(image_path, frame)
        cap.release()

    print(f"Captured image: {image_path}")
    send_data_all(image_path)

def camera_trigger():
    """Listen for manual input (virtual mode) or use a timed trigger (real Pi camera)."""
    print("Camera ready. Press 'P' to capture, 'X' to exit (virtual mode).")

    while True:
        if not REAL_CAMERA:
            import keyboard
            if keyboard.is_pressed('p'):
                capture_image()
                time.sleep(1)
            elif keyboard.is_pressed('x'):
                print("Exiting camera loop.")
                break
        else:
            time.sleep(10)
            capture_image()

if __name__ == "__main__":
    try:
        camera_trigger()
    except KeyboardInterrupt:
        print("\nCamera system stopped.")
