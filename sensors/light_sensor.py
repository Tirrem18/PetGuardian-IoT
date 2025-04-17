import os
import time
import json
import random
import base64
import uuid
import paho.mqtt.client as mqtt
from azure.iot.device import IoTHubDeviceClient, Message
from azure.cosmos import CosmosClient

# Try to import the real I2C library; fall back to virtual sensor
try:
    from smbus2 import SMBus
    REAL_SENSOR = True
except ImportError:
    print("Light sensor module not found. Running in virtual mode.")
    REAL_SENSOR = False

# BH1750 I2C address
BH1750_ADDR = 0x23

# Azure IoT Hub configuration
IOTHUB_CONNECTION_STRING = "HostName=IoTPawTrack.azure-devices.net;DeviceId=collar01;SharedAccessKey=ShzFs2jgI06rAjksNrEst8Byb8x2ljbHrBGYT+raQ1E="

# Cosmos DB configuration
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

# MQTT configuration
BROKER = "test.mosquitto.org"
TOPIC = "petguardian/light"

# Setup Cosmos DB connection
cosmos_client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
database = cosmos_client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

# Setup I2C for physical sensor
if REAL_SENSOR:
    bus = SMBus(1)

# Project-level log path setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "data", "logs")
LOG_PATH = os.path.join(LOG_DIR, "light_log.json")
os.makedirs(LOG_DIR, exist_ok=True)

def send_data_to_cloud(light_data):
    """Send light data to MQTT broker."""
    client = mqtt.Client()
    try:
        client.connect(BROKER)
        payload = json.dumps({
            "sensor": "light",
            "lux": light_data["lux"],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        client.publish(TOPIC, payload)
        print("Sent light data to MQTT broker.")
    except Exception as e:
        print(f"MQTT error: {e}")
    finally:
        client.disconnect()

def send_light_to_azure(light_data):
    """Send light data to Azure IoT Hub."""
    try:
        client = IoTHubDeviceClient.create_from_connection_string(IOTHUB_CONNECTION_STRING)
        payload = json.dumps({
            "sensor": "light",
            "lux": light_data["lux"],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        message = Message(payload)
        client.send_message(message)
        print("Sent light data to Azure IoT Hub.")
        client.disconnect()
    except Exception as e:
        print(f"Azure IoT Hub error: {e}")

def send_light_to_cosmos(light_data):
    """Send light data to Cosmos DB."""
    try:
        payload = {
            "sensor": "light",
            "lux": light_data["lux"],
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
        print("Sent light data to Cosmos DB.")
    except Exception as e:
        print(f"Cosmos DB error: {e}")

def log_light_data(light_data):
    """Log light data locally in JSON format."""
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "lux": light_data["lux"]
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

    print("Logged light data locally.")

def get_light_level():
    """Get current light level from sensor or simulate it."""
    if REAL_SENSOR:
        data = bus.read_i2c_block_data(BH1750_ADDR, 0x10, 2)
        lux = (data[0] << 8) | data[1]
        return {"lux": lux}
    else:
        return {"lux": random.uniform(0, 1000)}

def light_tracking():
    """Continuously track, log, and transmit light data."""
    print("Light sensor active...")
    while True:
        light_data = get_light_level()
        log_light_data(light_data)
        send_data_to_cloud(light_data)
        send_light_to_azure(light_data)
        send_light_to_cosmos(light_data)
        time.sleep(5)

if __name__ == "__main__":
    try:
        light_tracking()
    except KeyboardInterrupt:
        print("\nLight tracking stopped.")
