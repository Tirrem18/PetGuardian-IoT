import json
import base64
import uuid
import time
from azure.iot.device import IoTHubDeviceClient, Message
from azure.cosmos import CosmosClient

# Azure IoT Hub
IOTHUB_CONN_STR = "HostName=IoTPawTrack.azure-devices.net;DeviceId=collar01;SharedAccessKey=ShzFs2jgI06rAjksNrEst8Byb8x2ljbHrBGYT+raQ1E="

# Cosmos DB
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

cosmos_client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
container = cosmos_client.get_database_client(DATABASE_NAME).get_container_client(CONTAINER_NAME)

def send_threat_to_cosmos(timestamp, gps, reason):
    item = {
        "id": str(uuid.uuid4()),
        "sensor": "threat",
        "timestamp": timestamp,
        "latitude": gps[0],
        "longitude": gps[1],
        "reason": reason,
        "deviceId": "collar01"
    }

    try:
        container.create_item(body=item)
        print("[COSMOS] Threat logged successfully.")
    except Exception as e:
        print(f"[COSMOS ERROR] {e}")

def send_threat_to_azure(timestamp, gps, reason):
    payload = {
        "sensor": "threat",
        "timestamp": timestamp,
        "latitude": gps[0],
        "longitude": gps[1],
        "reason": reason
    }

    msg = Message(json.dumps(payload))

    try:
        client = IoTHubDeviceClient.create_from_connection_string(IOTHUB_CONN_STR)
        client.send_message(msg)
        client.disconnect()
        print("[AZURE] Threat sent to IoT Hub.")
    except Exception as e:
        print(f"[AZURE ERROR] {e}")
