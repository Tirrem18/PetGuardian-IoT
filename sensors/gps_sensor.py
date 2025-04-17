import os
import time
import json
import base64
import uuid
import random
import paho.mqtt.client as mqtt
from azure.iot.device import IoTHubDeviceClient, Message
from azure.cosmos import CosmosClient

# Check for real GPS sensor
try:
    import gpsd
    REAL_SENSOR = True
except ImportError:
    print("GPS module not found. Running in virtual mode.")
    REAL_SENSOR = False

# Azure IoT Hub configuration
IOTHUB_CONNECTION_STRING = "HostName=IoTPawTrack.azure-devices.net;DeviceId=collar01;SharedAccessKey=ShzFs2jgI06rAjksNrEst8Byb8x2ljbHrBGYT+raQ1E="

# Cosmos DB configuration
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

# MQTT configuration
BROKER = "broker.hivemq.com"
TOPIC = "petguardian/gps"

# Cosmos DB client setup
cosmos_client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
database = cosmos_client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

# Log file path setup using absolute project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "data", "logs")
LOG_PATH = os.path.join(LOG_DIR, "gps_log.json")
os.makedirs(LOG_DIR, exist_ok=True)

def get_gps_location():
    """Retrieve GPS location from sensor or simulate data."""
    if REAL_SENSOR:
        gpsd.connect()
        packet = gpsd.get_current()
        return {"latitude": packet.lat, "longitude": packet.lon}
    else:
        return {
            "latitude": 51.5074 + random.uniform(-0.01, 0.01),
            "longitude": -0.1278 + random.uniform(-0.01, 0.01)
        }

def send_data_to_mqtt(location):
    """Send GPS data to MQTT broker."""
    client = mqtt.Client()
    client.connect(BROKER)
    payload = json.dumps({
        "sensor": "gps",
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    client.publish(TOPIC, payload)
    client.disconnect()
    print("Sent GPS data to MQTT broker.")

def send_data_to_azure(location):
    """Send GPS data to Azure IoT Hub."""
    try:
        client = IoTHubDeviceClient.create_from_connection_string(IOTHUB_CONNECTION_STRING)
        payload = json.dumps({
            "sensor": "gps",
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        message = Message(payload)
        client.send_message(message)
        print("Sent GPS data to Azure IoT Hub.")
        client.disconnect()
    except Exception as e:
        print(f"Azure IoT Hub error: {e}")

def send_data_to_cosmos(location):
    """Send GPS data to Cosmos DB (base64-encoded payload)."""
    try:
        payload = {
            "sensor": "gps",
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        encoded_body = base64.b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8')
        document = {
            "id": str(uuid.uuid4()),
            "Body": encoded_body,
            "deviceId": "collar01",
            "timestamp": payload["timestamp"]
        }
        container.create_item(body=document)
        print("Sent GPS data to Cosmos DB.")
    except Exception as e:
        print(f"Cosmos DB error: {e}")

def log_gps_data(location):
    """Log GPS data locally to a JSON file."""
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "latitude": location["latitude"],
        "longitude": location["longitude"]
    }

    logs = []
    if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 0:
        try:
            with open(LOG_PATH, "r") as log_file:
                logs = json.load(log_file)
            if not isinstance(logs, list):
                logs = []
        except Exception:
            logs = []

    logs.append(log_entry)

    with open(LOG_PATH, "w") as log_file:
        json.dump(logs, log_file, indent=4)

    print("Logged GPS data locally.")

def gps_tracking():
    """Continuously track, log, and send GPS data to all targets."""
    print("GPS tracking active.")
    while True:
        location = get_gps_location()
        log_gps_data(location)
        send_data_to_mqtt(location)
        send_data_to_azure(location)
        send_data_to_cosmos(location)
        time.sleep(10)

if __name__ == "__main__":
    try:
        gps_tracking()
    except KeyboardInterrupt:
        print("\nGPS tracking stopped.")
