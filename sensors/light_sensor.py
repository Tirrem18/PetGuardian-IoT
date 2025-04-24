import time
import json
import os
import random
import base64
import uuid
import paho.mqtt.client as mqtt
from datetime import datetime
import logging

from azure.iot.device import IoTHubDeviceClient, Message
from azure.cosmos import CosmosClient

logging.getLogger("azure").setLevel(logging.WARNING)

# --- Sensor Configuration ---
USE_REAL_SENSOR = os.getenv("LUX", "false").strip().lower() == "true"
INTERACTIVE_MODE = os.getenv("LUX_MODE", "").strip().lower() == "interactive"

try:
    if USE_REAL_SENSOR:
        import smbus
        from bh1750 import BH1750
        sensor = BH1750(1)
        REAL_SENSOR = True
        print("[INIT] Real BH1750 lux sensor activated.")
    else:
        raise ImportError("Virtual sensor mode forced")
except ImportError as e:
    REAL_SENSOR = False
    print(f"[INIT] Virtual BH1750 simulation mode activated. Reason: {e}")

# --- MQTT Configuration ---
BROKER = "a5c9d1ea0e224376ad6285eb8aa83d55.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "username"
PASSWORD = "Password1"
TOPIC_PUBLISH = "petguardian/lux_sensor"
TOPIC_TRIGGER = "petguardian/trigger/lux"

mqtt_client = mqtt.Client(client_id="lux_sensor")
mqtt_client.username_pw_set(USERNAME, PASSWORD)
mqtt_client.tls_set()

# --- Azure + Cosmos Configuration ---
IOTHUB_CONNECTION_STRING = "HostName=IoTPawTrack.azure-devices.net;DeviceId=collar01;SharedAccessKey=ShzFs2jgI06rAjksNrEst8Byb8x2ljbHrBGYT+raQ1E="
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

cosmos_client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
database = cosmos_client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

# --- Helper Functions ---
def get_lux_value():
    if REAL_SENSOR:
        try:
            lux = int(sensor.luminance(BH1750.ONCE_HIRES_1))
            scaled = min(max(int(lux / 655.35 * 100), 0), 100)
            return scaled
        except Exception as e:
            print(f"[ERROR] BH1750 reading failed: {e}")
            return random.randint(0, 100)
    elif INTERACTIVE_MODE:
        val = input("Enter lux level (0–100): ").strip()
        try:
            lux = int(val)
            if 0 <= lux <= 100:
                return lux
        except:
            pass
        print("[ERROR] Invalid lux. Using 50.")
        return 50
    else:
        return random.randint(0, 100)

def send_lux(lux_value):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    payload = json.dumps({
        "sensor": "lux",
        "lux": lux_value,
        "timestamp": timestamp
    })

    # MQTT
    mqtt_client.publish(TOPIC_PUBLISH, payload)
    print(f"[INPUT] Sent lux: {lux_value}")

    # Azure IoT Hub
    try:
        client = IoTHubDeviceClient.create_from_connection_string(IOTHUB_CONNECTION_STRING)
        client.send_message(Message(payload))
        client.disconnect()
        print("[AZURE] Lux data sent to IoT Hub.")
    except Exception as e:
        print(f"[AZURE ERROR] {e}")

    # Cosmos DB
    try:
        encoded = base64.b64encode(payload.encode()).decode()
        doc = {
            "id": str(uuid.uuid4()),
            "Body": encoded,
            "deviceId": "collar01",
            "timestamp": timestamp
        }
        container.create_item(body=doc)
        print("[COSMOS] Lux data stored.")
    except Exception as e:
        print(f"[COSMOS ERROR] {e}")

    # Local Logging
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(base_dir, "data", "logs")
        log_path = os.path.join(log_dir, "lux_log.json")
        os.makedirs(log_dir, exist_ok=True)

        log_entry = {"timestamp": timestamp, "lux": lux_value}
        logs = []
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                logs = json.load(f)
        logs.append(log_entry)
        with open(log_path, "w") as f:
            json.dump(logs, f, indent=4)
    except Exception as e:
        print(f"[LOG ERROR] Could not log lux data: {e}")

# --- MQTT Callback ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[MQTT] Lux sensor connected.")
        client.subscribe(TOPIC_TRIGGER)
        print(f"[MQTT] Subscribed to: {TOPIC_TRIGGER}")
    else:
        print("[MQTT ERROR] Connection failed with code", rc)

def on_message(client, userdata, msg):
    print(f"[MQTT] Trigger received on {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode())
        if payload.get("command") == "get_lux":
            lux = get_lux_value()
            send_lux(lux)
    except Exception as e:
        print(f"[ERROR] Could not handle trigger: {e}")

# --- Start Listener ---
def start_lux_listener():
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    for attempt in range(10):
        try:
            mqtt_client.connect(BROKER, PORT, 60)
            mqtt_client.loop_start()
            print("[MQTT] Lux listener started.")
            return
        except Exception as e:
            print(f"[MQTT ERROR] Attempt {attempt+1}: {e}")
            time.sleep(1)

    print("[MQTT ERROR] Could not connect to MQTT broker.")

# --- Main ---
if __name__ == "__main__":
    start_lux_listener()

    if INTERACTIVE_MODE:
        print("[INTERACTIVE] Type 'L' then Enter to trigger lux reading, or 'X' to exit.")
        try:
            while True:
                user_input = input("[INPUT] >> ").strip().lower()
                if user_input == 'l':
                    lux = get_lux_value()
                    send_lux(lux)
                elif user_input == 'x':
                    print("[EXIT] Exiting lux interactive mode.")
                    break
        except KeyboardInterrupt:
            print("[EXIT] Lux interactive loop interrupted.")