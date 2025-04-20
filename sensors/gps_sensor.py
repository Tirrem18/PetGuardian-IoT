import os
import time
import json
import base64
import uuid
import random
import paho.mqtt.client as mqtt
from azure.iot.device import IoTHubDeviceClient, Message
from azure.cosmos import CosmosClient

INTERACTIVE_MODE = False

BROKER = "a5c9d1ea0e224376ad6285eb8aa83d55.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "username"
PASSWORD = "Password1"
TOPIC_PUBLISH = "petguardian/gps"
TOPIC_TRIGGER = "petguardian/trigger/gps"

IOTHUB_CONNECTION_STRING = "HostName=IoTPawTrack.azure-devices.net;DeviceId=collar01;SharedAccessKey=ShzFs2jgI06rAjksNrEst8Byb8x2ljbHrBGYT+raQ1E="

COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

cosmos_client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
database = cosmos_client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "data", "logs")
LOG_PATH = os.path.join(LOG_DIR, "gps_log.json")
os.makedirs(LOG_DIR, exist_ok=True)

HOME_LOCATION = (54.5742, -1.2345)

try:
    import gpsd
    REAL_SENSOR = True
except ImportError:
    print("⚠️ GPS module not found. Virtual mode enabled.")
    REAL_SENSOR = False

def get_gps_location():
    if REAL_SENSOR:
        try:
            gpsd.connect()
            packet = gpsd.get_current()
            return {"latitude": packet.lat, "longitude": packet.lon}
        except Exception as e:
            print(f"❌ GPS error: {e} — assuming location unavailable.")
            return None
    elif INTERACTIVE_MODE:
        print("🧪 Manual GPS input mode. Press Enter or type 'x' to exit.")
        while True:
            try:
                lat_input = input("Latitude: ").strip()
                if lat_input == "" or lat_input.lower() == "x":
                    return None
                lon_input = input("Longitude: ").strip()
                if lon_input == "" or lon_input.lower() == "x":
                    return None
                lat = float(lat_input)
                lon = float(lon_input)
                return {"latitude": lat, "longitude": lon}
            except ValueError:
                print("❌ Invalid input. Try again.")
    else:
        lat = HOME_LOCATION[0] + random.uniform(0.03, 0.1)
        lon = HOME_LOCATION[1] + random.uniform(0.03, 0.1)
        return {"latitude": round(lat, 6), "longitude": round(lon, 6)}

def log_gps_data(location):
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "latitude": location["latitude"],
        "longitude": location["longitude"]
    }
    logs = []
    if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 0:
        try:
            with open(LOG_PATH, "r") as f:
                logs = json.load(f)
            if not isinstance(logs, list):
                logs = []
        except Exception:
            logs = []
    logs.append(log_entry)
    with open(LOG_PATH, "w") as f:
        json.dump(logs, f, indent=4)
    print("📝 Logged GPS.")

def run_gps_once():
    location = get_gps_location()
    if not location:
        print("⚠️ No GPS location. Skipping.")
        return

    log_gps_data(location)

    payload = json.dumps({
        "sensor": "gps",
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })

    try:
        azure = IoTHubDeviceClient.create_from_connection_string(IOTHUB_CONNECTION_STRING)
        azure.send_message(Message(payload))
        azure.disconnect()
        print("☁️ Sent GPS to Azure.")
    except Exception as e:
        print(f"❌ Azure send error: {e}")

    try:
        encoded = base64.b64encode(payload.encode()).decode()
        doc = {
            "id": str(uuid.uuid4()),
            "Body": encoded,
            "deviceId": "collar01",
            "timestamp": json.loads(payload)["timestamp"]
        }
        container.create_item(body=doc)
        print("📦 Sent GPS to Cosmos DB.")
    except Exception as e:
        print(f"❌ Cosmos error: {e}")

    try:
        client = mqtt.Client(client_id="gps_client")
        client.username_pw_set(USERNAME, PASSWORD)
        client.tls_set()
        client.connect(BROKER, PORT)
        client.loop_start()
        time.sleep(1)
        client.publish(TOPIC_PUBLISH, payload)
        client.loop_stop()
        client.disconnect()
        print("📤 Sent GPS to MQTT broker.")
    except Exception as e:
        print(f"⚠️ MQTT error: {e}")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("GPS Connected to MQTT broker.")
        client.subscribe(TOPIC_TRIGGER)
        print(f"📡 Subscribed to: {TOPIC_TRIGGER}")
    else:
        print("❌ Connection failed")

def on_message(client, userdata, msg):
    print(f"📥 Received message on {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode())
        if payload.get("command") == "get_gps":
            print("🛰️ Trigger received. Collecting GPS...")
            run_gps_once()
    except Exception as e:
        print(f"⚠️ Error in message: {e}")

def start_gps_listener():
    print("📡 GPS Listener running. Waiting for 'get_gps' ping...")
    try:
        client = mqtt.Client(client_id="gps_sensor")
        client.username_pw_set(USERNAME, PASSWORD)
        client.tls_set()
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(BROKER, PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("🛑 Exiting GPS listener.")

if __name__ == "__main__":
    INTERACTIVE_MODE = True
    start_gps_listener()
