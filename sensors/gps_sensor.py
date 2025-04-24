import os
import time
import json
import base64
import uuid
import random
import paho.mqtt.client as mqtt
from azure.iot.device import IoTHubDeviceClient, Message
from azure.cosmos import CosmosClient
import logging
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("azure.iot").setLevel(logging.ERROR)



# Environment-based mode selection
GPS_MODE = os.getenv("GPS_MODE", "").strip().lower() == "interactive"
USE_REAL_GPS = os.getenv("GPS", "true").strip().lower() == "true"

# MQTT (HiveMQ Cloud)
BROKER = "a5c9d1ea0e224376ad6285eb8aa83d55.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "username"
PASSWORD = "Password1"
TOPIC_PUBLISH = "petguardian/gps"
TOPIC_TRIGGER = "petguardian/trigger/gps"

# Azure IoT Hub
IOTHUB_CONNECTION_STRING = "HostName=IoTPawTrack.azure-devices.net;DeviceId=collar01;SharedAccessKey=ShzFs2jgI06rAjksNrEst8Byb8x2ljbHrBGYT+raQ1E="

# Cosmos DB
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

# Local logging paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "data", "logs")
LOG_PATH = os.path.join(LOG_DIR, "gps_log.json")
os.makedirs(LOG_DIR, exist_ok=True)

# Define fallback home location for simulation
HOME_LOCATION = (54.5742, -1.2345)

# Cosmos DB setup
cosmos_client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
database = cosmos_client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

# MQTT client setup
mqtt_client = mqtt.Client(client_id="gps_sensor")
mqtt_client.username_pw_set(USERNAME, PASSWORD)
mqtt_client.tls_set()

# GPS hardware check
try:
    if USE_REAL_GPS:
        import gpsd
        REAL_SENSOR = True
        print("[INIT] Real GPS sensor activated.")
    else:
        raise ImportError("Virtual GPS mode forced by environment")
except ImportError as e:
    REAL_SENSOR = False
    print(f"[INIT] Virtual GPS mode activated. Reason: {e}")

# Get location depending on mode
def get_gps_location():
    if REAL_SENSOR:
        try:
            gpsd.connect()
            packet = gpsd.get_current()
            return {"latitude": packet.lat, "longitude": packet.lon}
        except Exception as e:
            print(f"[ERROR] GPS failure: {e}. Using fallback logic.")
            return None
    elif GPS_MODE:
        print("[INTERACTIVE] Manual GPS input. Press Enter or X to skip.")
        while True:
            try:
                lat = input("Latitude: ").strip()
                if lat.lower() in ["", "x"]:
                    return None
                lon = input("Longitude: ").strip()
                if lon.lower() in ["", "x"]:
                    return None
                return {"latitude": float(lat), "longitude": float(lon)}
            except ValueError:
                print("[INPUT ERROR] Please enter valid numbers.")
    else:
        lat = HOME_LOCATION[0] + random.uniform(-0.001, 0.0001)
        lon = HOME_LOCATION[1] + random.uniform(-0.001, 0.0001)

        return {"latitude": round(lat, 6), "longitude": round(lon, 6)}

# Save data to local log file
def log_gps_data(location, timestamp):
    log_entry = {
        "timestamp": timestamp,
        "latitude": location.get("latitude", "unknown"),
        "longitude": location.get("longitude", "unknown")
    }

    logs = []
    if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 0:
        try:
            with open(LOG_PATH, "r") as f:
                logs = json.load(f)
        except Exception:
            logs = []

    logs.append(log_entry)
    with open(LOG_PATH, "w") as f:
        json.dump(logs, f, indent=4)

    print("[LOG] GPS data saved.")

# Core logic to fetch and send GPS data
def run_gps_once():
    location = get_gps_location()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    if not location:
        print("[WARNING] No location data — using fallback UNKNOWN location.")
        location = {"latitude": "unknown", "longitude": "unknown"}

    log_gps_data(location, timestamp)

    payload = json.dumps({
        "sensor": "gps",
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "timestamp": timestamp
    })

    # Azure send
    try:
        azure = IoTHubDeviceClient.create_from_connection_string(IOTHUB_CONNECTION_STRING)
        azure.send_message(Message(payload))
        azure.disconnect()
        print("[AZURE] GPS data sent.")
    except Exception as e:
        print(f"[AZURE ERROR] {e}")

    # Cosmos write
    try:
        encoded = base64.b64encode(payload.encode()).decode()
        doc = {
            "id": str(uuid.uuid4()),
            "Body": encoded,
            "deviceId": "collar01",
            "timestamp": timestamp
        }
        container.create_item(body=doc)
        print("[COSMOS] GPS data stored.")
    except Exception as e:
        print(f"[COSMOS ERROR] {e}")

    # MQTT publish
    for attempt in range(3):
        try:
            mqtt_client.publish(TOPIC_PUBLISH, payload)
            print("[MQTT] GPS data published.")
            break
        except Exception as e:
            print(f"[MQTT ERROR] Attempt {attempt+1}: {e}")
            if attempt < 2:
                time.sleep(1)
            else:
                print("[MQTT ERROR] Final attempt failed.")

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[MQTT] GPS connected successfully.")
        client.subscribe(TOPIC_TRIGGER)
        print(f"[MQTT] Subscribed to: {TOPIC_TRIGGER}")
    else:
        print("[MQTT ERROR] Connection failed.")

def on_message(client, userdata, msg):
    print(f"[MQTT] Message received on {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode())
        if payload.get("command") == "get_gps":
            print("[TRIGGER] GPS request received.")
            run_gps_once()
    except Exception as e:
        print(f"[MQTT ERROR] Failed to process message: {e}")

# MQTT listener

def start_gps_listener():
    print("[MQTT] Starting GPS listener...")

    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    for attempt in range(50):
        try:
            print(f"[MQTT] Connection attempt {attempt+1}...")
            mqtt_client.connect(BROKER, PORT, 60)
            mqtt_client.loop_start()
            return
        except Exception as e:
            print(f"[MQTT ERROR] Attempt {attempt+1} failed: {e}")
            time.sleep(1)

    print("[MQTT ERROR] Could not connect to MQTT broker.")

# Main entry point
if __name__ == "__main__":
    start_gps_listener()

    # Interactive mode logic
    if GPS_MODE:
        print("[INTERACTIVE] Type 'G' then Enter to trigger GPS, or 'X' to exit.")
        try:
            while True:
                user_input = input("[INPUT] >> ").strip().lower()
                if user_input == 'g':
                    print("[INPUT] Manual GPS trigger activated.")
                    run_gps_once()
                elif user_input == 'x':
                    print("[EXIT] Exiting GPS interactive mode.")
                    break
        except KeyboardInterrupt:
            print("[EXIT] GPS interactive loop interrupted.")

