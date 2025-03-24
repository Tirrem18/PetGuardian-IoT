import time
import json
import os
import random
import base64
import uuid
from azure.iot.device import IoTHubDeviceClient, Message
from azure.cosmos import CosmosClient
import paho.mqtt.client as mqtt

# Try to import real GPS sensor; fall back to virtual mode
try:
    import gpsd
    REAL_SENSOR = True
except ImportError:
    print("GPS module not found! Running in virtual mode...")
    REAL_SENSOR = False

# Azure IoT Hub connection
IOTHUB_CONNECTION_STRING = "HostName=IoTPawTrack.azure-devices.net;DeviceId=collar01;SharedAccessKey=ShzFs2jgI06rAjksNrEst8Byb8x2ljbHrBGYT+raQ1E="

# Cosmos DB connection
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

# MQTT
BROKER = "broker.hivemq.com"
TOPIC = "petguardian/gps"

# Cosmos DB client
cosmos_client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
database = cosmos_client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

def get_gps_location():
    """Gets GPS data from sensor or generates mock data."""
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
    print(f"Sent GPS Data to MQTT Broker: {payload}")

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
        print(f"Sent GPS Data to Azure IoT Hub: {payload}")
        client.disconnect()
    except Exception as e:
        print(f"Failed to send to Azure IoT Hub: {e}")

def send_data_to_cosmos(location):
    """Send GPS data to Cosmos DB (Base64-encoded)."""
    try:
        payload = {
            "sensor": "gps",
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        encoded_body = base64.b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8')
        document = {
            "id": str(uuid.uuid4()),  # ✅ Add a unique ID for the document
            "Body": encoded_body,
            "deviceId": "collar01",
            "timestamp": payload["timestamp"]
            }
        container.create_item(body=document)
        print("✅ Sent GPS data to Cosmos DB")
    except Exception as e:
        print(f"❌ Failed to send to Cosmos DB: {e}")

def log_gps_data(location):
    """Logs GPS data to local JSON file."""
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "latitude": location["latitude"],
        "longitude": location["longitude"]
    }
    logs = []
    if os.path.exists("gps_log.json") and os.path.getsize("gps_log.json") > 0:
        try:
            with open("gps_log.json", "r") as log_file:
                logs = json.load(log_file)
            if not isinstance(logs, list):
                logs = []
        except Exception:
            logs = []
    logs.append(log_entry)
    with open("gps_log.json", "w") as log_file:
        json.dump(logs, log_file, indent=4)
    print(f"Logged GPS Data: {log_entry}")

def gps_tracking():
    """Continuously tracks and sends GPS data."""
    print("GPS Tracking Active...")
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
        print("\nStopping GPS tracking...")
