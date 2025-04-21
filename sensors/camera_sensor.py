# PetGuardian Camera Sensor (Refactored)
# Matches GPS & Acoustic Structure — MQTT + Interactive support

import os
import time
import json
import base64
import uuid
import paho.mqtt.client as mqtt
from azure.iot.device import IoTHubDeviceClient, Message
from azure.cosmos import CosmosClient
import logging
logging.getLogger("azure").setLevel(logging.WARNING)


# --- ENVIRONMENT CONFIG ---
CAMERA_MODE = os.getenv("CAMERA_MODE", "").strip().lower() == "interactive"
USE_REAL_CAMERA = os.getenv("CAMERA", "true").strip().lower() == "true"

# --- MQTT CONFIG ---
BROKER = "a5c9d1ea0e224376ad6285eb8aa83d55.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "username"
PASSWORD = "Password1"
TOPIC_PUBLISH = "petguardian/camera"
TOPIC_TRIGGER = "petguardian/trigger/camera"

# --- AZURE CONFIG ---
IOTHUB_CONNECTION_STRING = "HostName=IoTPawTrack.azure-devices.net;DeviceId=collar01;SharedAccessKey=ShzFs2jgI06rAjksNrEst8Byb8x2ljbHrBGYT+raQ1E="
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

# --- FILE PATHS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVE_DIR = os.path.join(BASE_DIR, "data", "images")
TEST_DIR = os.path.join(BASE_DIR, "tests", "test_images")
os.makedirs(SAVE_DIR, exist_ok=True)

# --- COSMOS SETUP ---
cosmos_client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
database = cosmos_client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

# --- CAMERA CHECK ---
try:
    if USE_REAL_CAMERA:
        import cv2
        cap_test = cv2.VideoCapture(0)
        if cap_test.isOpened():
            cap_test.release()
            REAL_CAMERA = True
            print("[INIT] Real camera mode activated.")
        else:
            raise Exception("No accessible USB camera found.")
    else:
        raise ImportError("Virtual camera mode forced by environment")
except Exception as e:
    REAL_CAMERA = False
    print(f"[INIT] Virtual camera mode activated. Reason: {e}")

# --- BASE64 ENCODER ---
def encode_image_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# --- SEND IMAGE ---
def send_data_all(image_path, timestamp):
    encoded_img = encode_image_to_base64(image_path) if image_path and os.path.exists(image_path) else "no_image"
    payload_json = json.dumps({"sensor": "camera", "timestamp": timestamp, "image_base64": encoded_img})

    # Azure
    for attempt in range(3):
        try:
            client = IoTHubDeviceClient.create_from_connection_string(IOTHUB_CONNECTION_STRING)
            client.send_message(Message(payload_json))
            client.disconnect()
            print("[AZURE] Image sent to IoT Hub.")
            break
        except Exception as e:
            print(f"[AZURE ERROR] Attempt {attempt+1}: {e}")
            time.sleep(1)

    # Cosmos
    for attempt in range(3):
        try:
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
            print(f"[COSMOS ERROR] Attempt {attempt+1}: {e}")
            time.sleep(1)

    # MQTT
    try:
        mqtt_client.publish(TOPIC_PUBLISH, payload_json)
        print("[MQTT] Image published.")
    except Exception as e:
        print(f"[MQTT ERROR] {e}")

# --- CAPTURE OR SIMULATE IMAGE ---
def trigger_camera(timestamp):
    filename = f"{timestamp.replace(':', '-').replace(' ', '_')}.jpg"
    path = os.path.join(SAVE_DIR, filename)

    if CAMERA_MODE and REAL_CAMERA:
        input("[INTERACTIVE] Press Enter to capture image...")
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        if ret:
            cv2.imwrite(path, frame)
            print(f"[CAPTURE] Webcam image saved: {path}")
        else:
            print("[ERROR] Failed to capture image.")
            path = None

    elif CAMERA_MODE and not REAL_CAMERA:
        print("[INTERACTIVE] Select test image: 1-Dog, 2-Bike, 3-Human")
        choice = input("Choice (1-3): ").strip()
        file_map = {"1": "dog.png", "2": "bike.png", "3": "human.png"}
        src = file_map.get(choice)
        if src:
            try:
                src_path = os.path.join(TEST_DIR, src)
                with open(src_path, "rb") as fsrc, open(path, "wb") as fdst:
                    fdst.write(fsrc.read())
                print(f"[TEST] Image copied to: {path}")
            except Exception as e:
                print(f"[ERROR] Copy failed: {e}")
                path = None
        else:
            print("[ERROR] Invalid selection.")
            return

    elif not CAMERA_MODE and REAL_CAMERA:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        if ret:
            cv2.imwrite(path, frame)
            print(f"[CAPTURE] Auto image saved: {path}")
        else:
            print("[ERROR] Auto capture failed.")
            path = None

    elif not CAMERA_MODE and not REAL_CAMERA:
        print("[SIMULATION] Virtual mode active. No image generated.")
        path = None

    if not path:
        print("[WARNING] No image captured.")

    send_data_all(path, timestamp)

# --- MQTT ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[MQTT] Camera connected.")
        client.subscribe(TOPIC_TRIGGER)
        print(f"[MQTT] Subscribed to: {TOPIC_TRIGGER}")
    else:
        print("[MQTT ERROR] Failed to connect.")

def on_message(client, userdata, msg):
    print(f"[MQTT] Trigger received on {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode())
        if payload.get("command") == "get_camera":
            timestamp = payload.get("timestamp") or time.strftime("%Y-%m-%d %H:%M:%S")
            trigger_camera(timestamp)
    except Exception as e:
        print(f"[MQTT ERROR] Failed to process message: {e}")

def start_camera_listener():
    global mqtt_client
    mqtt_client = mqtt.Client(client_id="camera_sensor")
    mqtt_client.username_pw_set(USERNAME, PASSWORD)
    mqtt_client.tls_set()

    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    for attempt in range(50):
        try:
            print(f"[MQTT] Connect attempt {attempt+1}...")
            mqtt_client.connect(BROKER, PORT, 60)
            mqtt_client.loop_start()
            return
        except Exception as e:
            print(f"[MQTT ERROR] Attempt {attempt+1} failed: {e}")
            time.sleep(1)

    print("[MQTT ERROR] Connection attempts exhausted.")

# --- MAIN ENTRY ---
if __name__ == "__main__":
    start_camera_listener()

    if CAMERA_MODE:
        print("[INTERACTIVE] Type 'C' to capture, or 'X' to exit.")
        try:
            while True:
                cmd = input("[INPUT] >> ").strip().lower()
                if cmd == 'c':
                    trigger_camera(time.strftime("%Y-%m-%d %H:%M:%S"))
                elif cmd == 'x':
                    print("[EXIT] Exiting camera interactive mode.")
                    break
        except KeyboardInterrupt:
            print("[EXIT] Manual mode interrupted.")