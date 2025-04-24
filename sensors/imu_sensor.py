import time
import json
import os
import random
import base64
import uuid
import paho.mqtt.client as mqtt
from azure.iot.device import IoTHubDeviceClient, Message
from azure.cosmos import CosmosClient
import logging

logging.getLogger("azure").setLevel(logging.WARNING)

# --- Configuration ---
USE_REAL_SENSOR = os.getenv("IMU", "false").strip().lower() == "true"
INTERACTIVE_MODE = os.getenv("IMU_MODE", "").strip().lower() == "interactive"

try:
    if USE_REAL_SENSOR:
        import smbus  # placeholder for actual IMU lib
        REAL_SENSOR = True
        print("[INIT] Real IMU sensor activated.")
    else:
        raise ImportError("Virtual mode forced")
except ImportError as e:
    REAL_SENSOR = False
    print(f"[INIT] Virtual IMU mode activated. Reason: {e}")

# --- MQTT ---
BROKER = "a5c9d1ea0e224376ad6285eb8aa83d55.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "username"
PASSWORD = "Password1"
TOPIC = "petguardian/imu"

mqtt_client = None

# --- Azure ---
AZURE_CONNECTION_STRING = "HostName=IoTPawTrack.azure-devices.net;DeviceId=collar01;SharedAccessKey=ShzFs2jgI06rAjksNrEst8Byb8x2ljbHrBGYT+raQ1E="
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

cosmos_client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
database = cosmos_client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

# --- Generate IMU Reading ---
def get_imu_reading():
    if REAL_SENSOR:
        # Placeholder for real IMU reading logic
        return {
            "accel_x": round(random.uniform(-2, 2), 6),
            "accel_y": round(random.uniform(-2, 2), 6),
            "accel_z": round(random.uniform(-2, 2), 6),
        }
    elif INTERACTIVE_MODE:
        try:
            ax = float(input("accel_x: ").strip())
            ay = float(input("accel_y: ").strip())
            az = float(input("accel_z: ").strip())
            return {"accel_x": ax, "accel_y": ay, "accel_z": az}
        except ValueError:
            print("[INPUT ERROR] Invalid float. Using zeros.")
            return {"accel_x": 0.0, "accel_y": 0.0, "accel_z": 0.0}
    else:
        return {
            "accel_x": round(random.uniform(0, 9), 6),
            "accel_y": round(random.uniform(0, 1), 6),
            "accel_z": round(random.uniform(0, 9), 6),
        }

# --- Handle IMU Event ---
def handle_imu_event():
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    imu = get_imu_reading()
    imu["timestamp"] = timestamp

    print(f"[LOG] IMU Event: {json.dumps(imu)}")
    log_to_file(imu)
    send_to_mqtt(imu)
    send_to_azure(imu)
    send_to_cosmos(imu)

# --- Log Locally ---
def log_to_file(data):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(base_dir, "data", "logs")
    log_path = os.path.join(log_dir, "imu_log.json")
    os.makedirs(log_dir, exist_ok=True)

    logs = []
    if os.path.exists(log_path):
        try:
            with open(log_path, "r") as f:
                logs = json.load(f)
        except:
            logs = []

    logs.append(data)
    with open(log_path, "w") as f:
        json.dump(logs, f, indent=4)

# --- Send to MQTT ---
def send_to_mqtt(data):
    payload = json.dumps({
        "sensor": "imu",
        **data
    })
    for attempt in range(3):
        try:
            mqtt_client.publish(TOPIC, payload)
            print("[MQTT] IMU event published.")
            break
        except Exception as e:
            print(f"[MQTT ERROR] Attempt {attempt+1}: {e}")
            time.sleep(1)

# --- Send to Azure ---
def send_to_azure(data):
    try:
        payload = json.dumps({"sensor": "imu", **data})
        client = IoTHubDeviceClient.create_from_connection_string(AZURE_CONNECTION_STRING)
        client.send_message(Message(payload))
        client.disconnect()
        print("[AZURE] IMU event sent.")
    except Exception as e:
        print(f"[AZURE ERROR] {e}")

# --- Send to Cosmos ---
def send_to_cosmos(data):
    try:
        payload = json.dumps({"sensor": "imu", **data})
        encoded = base64.b64encode(payload.encode()).decode()
        doc = {
            "id": str(uuid.uuid4()),
            "Body": encoded,
            "deviceId": "collar01",
            "timestamp": data["timestamp"]
        }
        container.create_item(body=doc)
        print("[COSMOS] IMU event stored.")
    except Exception as e:
        print(f"[COSMOS ERROR] {e}")

# --- IMU Simulator ---
def start_imu_sensor():
    if INTERACTIVE_MODE:
        print("[INTERACTIVE] Type 'I' to enter IMU values, or 'X' to exit.")
        try:
            while True:
                cmd = input("[INPUT] >> ").strip().lower()
                if cmd == "i":
                    handle_imu_event()
                elif cmd == "x":
                    print("[EXIT] IMU interactive mode ended.")
                    break
        except KeyboardInterrupt:
            print("[EXIT] IMU interactive loop interrupted.")
    else:
        print("[MODE] Virtual IMU mode. Generating 3 readings at random intervals, then cooling down...")
        try:
            while True:
                for _ in range(3):
                    delay = random.uniform(1, 3)
                    time.sleep(delay)
                    print(f"[SIMULATION] Generating IMU event...")
                    handle_imu_event()
                cooldown = 120  # cooldown period in seconds
                print(f"[SIMULATION] Cooling down for {cooldown} seconds...\n")
                time.sleep(cooldown)
        except KeyboardInterrupt:
            print("[EXIT] IMU simulation stopped.")


# --- MQTT Listener ---
def start_imu_listener():
    global mqtt_client
    mqtt_client = mqtt.Client(client_id="imu_sensor")
    mqtt_client.username_pw_set(USERNAME, PASSWORD)
    mqtt_client.tls_set()

    for attempt in range(50):
        try:
            mqtt_client.connect(BROKER, PORT, 60)
            mqtt_client.loop_start()
            print("[MQTT] IMU connected successfully.")
            return
        except Exception as e:
            print(f"[MQTT ERROR] Attempt {attempt+1} failed: {e}")
            time.sleep(0.5)
    print("[MQTT ERROR] MQTT connection failed.")

# --- Main ---
if __name__ == "__main__":
    start_imu_listener()
    start_imu_sensor()