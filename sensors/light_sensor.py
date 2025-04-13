import time
import json
import os
import random
import paho.mqtt.client as mqtt
import base64
import uuid
from azure.iot.device import IoTHubDeviceClient, Message
from azure.cosmos import CosmosClient

# Try to import Raspberry Pi I2C library; if unavailable, use virtual mode
try:
    from smbus2 import SMBus
    REAL_SENSOR = True
except ImportError:
    print("Light sensor module not found! Running in virtual mode...")
    REAL_SENSOR = False

# BH1750 I2C Address (For Physical Sensor)
BH1750_ADDR = 0x23  

# Azure IoT Hub connection
IOTHUB_CONNECTION_STRING = "HostName=IoTPawTrack.azure-devices.net;DeviceId=collar01;SharedAccessKey=ShzFs2jgI06rAjksNrEst8Byb8x2ljbHrBGYT+raQ1E="

# Cosmos DB connection
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

# MQTT
BROKER = "test.mosquitto.org"
TOPIC = "petguardian/light"

# Cosmos DB client
cosmos_client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
database = cosmos_client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

if REAL_SENSOR:
    bus = SMBus(1)  # I2C Bus on Raspberry Pi

# ----------------------------- FUNCTIONS -----------------------------

def send_light_to_azure(light_data):
    """Send light sensor data to Azure IoT Hub."""
    try:
        client = IoTHubDeviceClient.create_from_connection_string(IOTHUB_CONNECTION_STRING)
        payload = json.dumps({
            "sensor": "light",
            "lux": light_data["lux"],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        message = Message(payload)
        client.send_message(message)
        print(f"✅ Sent Light Data to Azure IoT Hub: {payload}")
        client.disconnect()
    except Exception as e:
        print(f"❌ Failed to send to Azure IoT Hub: {e}")

def send_light_to_cosmos(light_data):
    """Send light data to Cosmos DB (Base64-encoded)."""
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
        print("✅ Sent Light data to Cosmos DB")
    except Exception as e:
        print(f"❌ Failed to send to Cosmos DB: {e}")

def send_data_to_cloud(light_data):
    """Send light sensor data to MQTT broker."""
    client = mqtt.Client()
    try:
        client.connect(BROKER)
        payload = json.dumps({
            "sensor": "light",
            "lux": light_data["lux"],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        client.publish(TOPIC, payload)
        print(f"📡 Sent Light Data to MQTT Broker: {payload}")
    except Exception as e:
        print(f"❌ MQTT error: {e}")
    finally:
        client.disconnect()

def log_light_data(light_data):
    """Logs light sensor data into a JSON file."""
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "lux": light_data["lux"]
    }

    logs = []
    if os.path.exists("light_log.json"):
        try:
            with open("light_log.json", "r") as log_file:
                logs = json.load(log_file)
            if not isinstance(logs, list):
                logs = []
        except Exception:
            logs = []
    
    logs.append(log_entry)

    with open("light_log.json", "w") as log_file:
        json.dump(logs, log_file, indent=4)

    print(f"📝 Logged: {log_entry}")

def get_light_level():
    """Gets light sensor data from real sensor or generates mock data."""
    if REAL_SENSOR:
        data = bus.read_i2c_block_data(BH1750_ADDR, 0x10, 2)
        lux = (data[0] << 8) | data[1]
        return {"lux": lux}
    else:
        return {"lux": random.uniform(0, 1000)}

def light_tracking():
    """Tracks and logs light sensor data continuously."""
    print("🔆 Light Sensor Active...")

    while True:
        light_data = get_light_level()
        log_light_data(light_data)
        send_data_to_cloud(light_data)       # MQTT
        send_light_to_azure(light_data)      # Azure IoT Hub
        send_light_to_cosmos(light_data)     # Cosmos DB
        time.sleep(5)

# ----------------------------- ENTRY POINT -----------------------------

if __name__ == "__main__":
    try:
        light_tracking()
    except KeyboardInterrupt:
        print("\n🛑 Stopping light sensor tracking...")
