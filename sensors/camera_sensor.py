import os
import time
import json
import base64
import uuid
import paho.mqtt.client as mqtt

# Azure & Cosmos DB
from azure.iot.device import IoTHubDeviceClient, Message
from azure.cosmos import CosmosClient

# Enable interactive input if run directly
INTERACTIVE_MODE = False

# Try PiCamera, fallback to OpenCV
try:
    from picamera import PiCamera
    REAL_CAMERA = True
except ImportError:
    import cv2
    print("⚠️ Camera module not found. Virtual mode enabled.")
    REAL_CAMERA = False

# MQTT (HiveMQ Cloud)
BROKER = "a5c9d1ea0e224376ad6285eb8aa83d55.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "username"
PASSWORD = "Password1"
TOPIC_PUBLISH = "petguardian/camera"
TOPIC_TRIGGER = "petguardian/trigger/camera"

# Azure
IOTHUB_CONNECTION_STRING = "HostName=IoTPawTrack.azure-devices.net;DeviceId=collar01;SharedAccessKey=ShzFs2jgI06rAjksNrEst8Byb8x2ljbHrBGYT+raQ1E="

# Cosmos
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

# PiCamera init
if REAL_CAMERA:
    camera = PiCamera()
    camera.resolution = (640, 480)

def encode_image_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

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

    # Azure IoT Hub Retry
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            azure = IoTHubDeviceClient.create_from_connection_string(IOTHUB_CONNECTION_STRING)
            azure.send_message(Message(payload_json))
            azure.disconnect()
            print("☁️ Image sent to Azure IoT Hub.")
            break
        except Exception as e:
            print(f"❌ Azure error (attempt {attempt}): {e}")
            if attempt < max_retries:
                time.sleep(1)
            else:
                print("🛑 Azure send failed after max retries.")

    # Cosmos DB Retry
    for attempt in range(1, max_retries + 1):
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
            print("📦 Image saved to Cosmos DB.")
            break
        except Exception as e:
            print(f"❌ Cosmos DB error (attempt {attempt}): {e}")
            if attempt < max_retries:
                time.sleep(1)
            else:
                print("🛑 Cosmos write failed after max retries.")


def trigger_camera(timestamp):
    filename = f"{timestamp.replace(':', '-').replace(' ', '_')}.jpg"
    path = os.path.join(SAVE_DIR, filename)

    if REAL_CAMERA:
        try:
            camera.capture(path)
            print(f"📸 Real image saved: {path}")
        except Exception as e:
            print(f"❌ Real camera error: {e}")
            path = None

    elif INTERACTIVE_MODE:
        print("🧪 Manual Camera Test Mode:")
        print("1. Angry Dog")
        print("2. Dirt Bike")
        print("3. Human")
        choice = input("Select image (1-3): ").strip()

        test_images = {
            "1": "dog.png",
            "2": "bike.png",
            "3": "human.png"
        }

        selected = test_images.get(choice)
        if not selected:
            print("❌ Invalid choice.")
            return

        src_path = os.path.join(TEST_DIR, selected)
        try:
            with open(src_path, "rb") as src, open(path, "wb") as dst:
                dst.write(src.read())
            print(f"🧪 Test image copied: {path}")
        except Exception as e:
            print(f"❌ Failed to copy test image: {e}")
            path = None

    else:
        try:
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            if ret:
                cv2.imwrite(path, frame)
                print(f"🧪 Simulated webcam image saved: {path}")
            else:
                print("❌ Simulated capture failed.")
                path = None
            cap.release()
        except Exception as e:
            print(f"❌ OpenCV error: {e}")
            path = None

    if not path:
        print("⚠️ No image captured — using fallback.")
    send_data_all(path, timestamp)

# MQTT logic
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("📡 CAMERA Connected to broker.")
        client.subscribe(TOPIC_TRIGGER)
        print(f"📡 Subscribed to: {TOPIC_TRIGGER}")
    else:
        print("❌ MQTT connection failed.")

def on_message(client, userdata, msg):
    print(f"📥 Trigger received on {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode())
        if payload.get("command") == "get_camera":
            timestamp = payload.get("timestamp")
            if not timestamp:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print("📸 Trigger received. Capturing image...")
            trigger_camera(timestamp)
        else:
            print("⚠️ Ignored: no matching command.")
    except Exception as e:
        print(f"❌ Failed to handle camera trigger: {e}")

def start_camera_listener():
    print("📡 Starting CAMERA MQTT listener...")

    client = mqtt.Client(client_id="camera_sensor")
    client.username_pw_set(USERNAME, PASSWORD)
    client.tls_set()

    client.on_connect = on_connect
    client.on_message = on_message

    max_retries = 10
    retry_delay = 1

    for attempt in range(1, max_retries + 1):
        try:
            print(f"🔄 CAMERA MQTT connect attempt {attempt}...")
            client.connect(BROKER, PORT, 60)
            client.loop_forever()
            break  # Successful connection exits loop
        except Exception as e:
            print(f"❌ CAMERA attempt {attempt} failed: {e}")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                print("🛑 Max retries reached. CAMERA MQTT connection failed.")


# Entry
if __name__ == "__main__":
    INTERACTIVE_MODE = True
    start_camera_listener()
