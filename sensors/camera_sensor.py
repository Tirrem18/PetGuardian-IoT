import os
import time
import json
import base64
import uuid
import paho.mqtt.client as mqtt

# Azure & Cosmos DB
from azure.iot.device import IoTHubDeviceClient, Message
from azure.cosmos import CosmosClient
from picamera2 import Picamera2

# Mode selection from environment
CAMERA_MODE = os.getenv("CAMERA_MODE", "").strip().lower() == "interactive"
USE_REAL_CAMERA = os.getenv("CAMERA", "true").strip().lower() == "true"

# MQTT (HiveMQ Cloud)
BROKER = "a5c9d1ea0e224376ad6285eb8aa83d55.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "username"
PASSWORD = "Password1"
TOPIC_PUBLISH = "petguardian/camera"
TOPIC_TRIGGER = "petguardian/trigger/camera"

# Azure IoT Hub
IOTHUB_CONNECTION_STRING = "HostName=IoTPawTrack.azure-devices.net;DeviceId=collar01;SharedAccessKey=ShzFs2jgI06rAjksNrEst8Byb8x2ljbHrBGYT+raQ1E="

# Cosmos DB
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVE_DIR = os.path.join(BASE_DIR, "data", "images")
TEST_DIR = os.path.join(BASE_DIR, "tests", "test_images")
os.makedirs(SAVE_DIR, exist_ok=True)

# Cosmos setup
cosmos_client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
database = cosmos_client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

# Attempt camera initialization
try:
    if USE_REAL_CAMERA:
        from picamera2 import PiCamera2
        REAL_CAMERA = True
        print("[INIT] Real camera mode activated.")
    else:
        raise ImportError("Virtual camera mode forced by environment")
except ImportError as e:
    import cv2
    REAL_CAMERA = False
    print(f"[INIT] Virtual camera mode activated. Reason: {e}")

# PiCamera setup
if REAL_CAMERA:
    camera = PiCamera2()
    camera.resolution = (640, 480)

# Base64 encoder
def encode_image_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# Sends image data to MQTT, Azure, and Cosmos DB
def send_data_all(image_path, timestamp):
    if image_path and os.path.exists(image_path):
        encoded_img = encode_image_to_base64(image_path)
    else:
        encoded_img = "no_image"

    payload = {
        "sensor": "camera",
        "timestamp": timestamp,
        "image_base64": encoded_img
    }
    payload_json = json.dumps(payload)

    # Azure send
    for attempt in range(3):
        try:
            azure = IoTHubDeviceClient.create_from_connection_string(IOTHUB_CONNECTION_STRING)
            azure.send_message(Message(payload_json))
            azure.disconnect()
            print("[AZURE] Image sent to IoT Hub.")
            break
        except Exception as e:
            print(f"[AZURE ERROR] Attempt {attempt+1} failed: {e}")
            time.sleep(1)

    # Cosmos DB send
    for attempt in range(3):
        try:
            encoded_doc = base64.b64encode(payload_json.encode()).decode()
            doc = {
                "id": str(uuid.uuid4()),
                "sensor": "camera",
                "timestamp": timestamp,
                "image_base64": encoded_img,
                "deviceId": "collar01"
            }
            container.create_item(body=doc)
            print("[COSMOS] Image saved to database.")
            break
        except Exception as e:
            print(f"[COSMOS ERROR] Attempt {attempt+1} failed: {e}")
            time.sleep(1)

# Capture or simulate image

def trigger_camera(timestamp):
    filename = f"{timestamp.replace(':', '-').replace(' ', '_')}.jpg"
    path = os.path.join(SAVE_DIR, filename)

    # Interactive mode with real camera
    if CAMERA_MODE and REAL_CAMERA:
        input("[INTERACTIVE] Press 'C' to manually trigger camera capture...")
        try:
            camera.capture(path)
            print(f"[CAPTURE] Real image saved: {path}")
        except Exception as e:
            print(f"[ERROR] Camera failed: {e}")
            path = None

    # Interactive mode with no real camera — manual image selection
    elif CAMERA_MODE and not REAL_CAMERA:
        print("[INTERACTIVE] Manual test image selection:")
        print("1. Angry Dog\n2. Dirt Bike\n3. Human")
        choice = input("[INPUT] Select image (1-3): ").strip()
        test_images = {"1": "dog.png", "2": "bike.png", "3": "human.png"}
        selected = test_images.get(choice)

        if not selected:
            print("[ERROR] Invalid choice.")
            return

        src_path = os.path.join(TEST_DIR, selected)
        try:
            with open(src_path, "rb") as src, open(path, "wb") as dst:
                dst.write(src.read())
            print(f"[TEST] Image copied: {path}")
        except Exception as e:
            print(f"[ERROR] Test image copy failed: {e}")
            path = None

    # Auto mode with real camera
    elif not CAMERA_MODE and REAL_CAMERA:
        try:
            camera.capture(path)
            print(f"[CAPTURE] Real image captured automatically: {path}")
        except Exception as e:
            print(f"[ERROR] Auto real camera capture failed: {e}")
            path = None

    # Auto mode with no real camera — simulate virtual result
    elif not CAMERA_MODE and not REAL_CAMERA:
        # Skip OpenCV entirely — just simulate "no image"
        print("[SIMULATION] Virtual mode active — no image generated.")
        path = None

    # Fallback if capture failed
    if not path:
        print("[WARNING] No image captured. Using fallback response.")

    # Send image (real or simulated)
    send_data_all(path, timestamp)


# MQTT setup and trigger listener
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[MQTT] Camera connected to broker.")
        client.subscribe(TOPIC_TRIGGER)
        print(f"[MQTT] Subscribed to: {TOPIC_TRIGGER}")
    else:
        print("[MQTT ERROR] Connection failed.")

def on_message(client, userdata, msg):
    print(f"[MQTT] Trigger received on {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode())
        if payload.get("command") == "get_camera":
            timestamp = payload.get("timestamp") or time.strftime("%Y-%m-%d %H:%M:%S")
            print("[TRIGGER] Capturing image...")
            trigger_camera(timestamp)
        else:
            print("[MQTT] No matching command found.")
    except Exception as e:
        print(f"[MQTT ERROR] Failed to handle message: {e}")

def start_camera_listener():
    print("[MQTT] Starting camera listener...")
    client = mqtt.Client(client_id="camera_sensor")
    client.username_pw_set(USERNAME, PASSWORD)
    client.tls_set()

    client.on_connect = on_connect
    client.on_message = on_message

    for attempt in range(50):
        try:
            print(f"[MQTT] Connection attempt {attempt+1}...")
            client.connect(BROKER, PORT, 60)
            client.loop_start()
            return
        except Exception as e:
            print(f"[MQTT ERROR] Attempt {attempt+1} failed: {e}")
            time.sleep(1)

    print("[MQTT ERROR] All connection attempts failed.")

# Main entry point
if __name__ == "__main__":
    start_camera_listener()

    # Start manual capture loop if interactive
    if CAMERA_MODE:
        import keyboard
        print("[INTERACTIVE] Press 'C' to capture, or 'X' to exit.")
        try:
            while True:
                if keyboard.is_pressed('c'):
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    trigger_camera(timestamp)
                    time.sleep(1)  # debounce
                elif keyboard.is_pressed('x'):
                    print("[EXIT] Exiting interactive mode.")
                    break
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("[EXIT] Manual mode interrupted.")
