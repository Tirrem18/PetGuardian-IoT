import os
import json
import time
import uuid
import base64
import logging
import paho.mqtt.client as mqtt
from azure.iot.device import IoTHubDeviceClient, Message
from azure.cosmos import CosmosClient
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Clean Azure logging
logging.getLogger("azure").setLevel(logging.WARNING)

class AIUtils:
    def __init__(self):
        self.timestamp_format = "%Y-%m-%d %H:%M:%S"

        # --- MQTT Setup ---
        self.broker = os.getenv("MQTT_BROKER")
        self.port = int(os.getenv("MQTT_PORT", "8883"))
        self.username = os.getenv("MQTT_USERNAME")
        self.password = os.getenv("MQTT_PASSWORD")
        self.client = mqtt.Client(client_id="ai_core")
        self.client.username_pw_set(self.username, self.password)
        self.client.tls_set()

        # --- Azure IoT Hub ---
        self.azure_conn = os.getenv("AZURE_CONN")

        # --- Cosmos DB Setup ---
        self.cosmos_uri = os.getenv("COSMOS_URI")
        self.cosmos_key = os.getenv("COSMOS_KEY")
        self.database_name = os.getenv("COSMOS_DB", "iotdata")
        self.container_name = os.getenv("COSMOS_CONTAINER", "telemetry")

        self.use_cosmos = True
        try:
            self.cosmos_client = CosmosClient(self.cosmos_uri, credential=self.cosmos_key)
            db = self.cosmos_client.get_database_client(self.database_name)
            self.container = db.get_container_client(self.container_name)
        except Exception as e:
            print(f"[COSMOS WARNING] Could not init Cosmos DB: {e}")
            self.use_cosmos = False

    def get_timestamp(self):
        return time.strftime(self.timestamp_format)

    def publish(self, topic, payload_dict):
        payload = json.dumps(payload_dict)
        for attempt in range(3):
            try:
                self.client.publish(topic, payload)
                print(f"[MQTT] Published to {topic}: {payload}")
                break
            except Exception as e:
                print(f"[MQTT ERROR] Attempt {attempt + 1} failed: {e}")
                time.sleep(1)

    def send_to_azure(self, payload_dict):
        try:
            payload = json.dumps(payload_dict)
            client = IoTHubDeviceClient.create_from_connection_string(self.azure_conn)
            client.send_message(Message(payload))
            client.disconnect()
            print("[AZURE] Data sent to IoT Hub.")
        except Exception as e:
            print(f"[AZURE ERROR] {e}")

    def send_to_cosmos(self, payload_dict, tag="ai"):
        if not self.use_cosmos:
            return
        try:
            encoded = base64.b64encode(json.dumps(payload_dict).encode()).decode()
            doc = {
                "id": str(uuid.uuid4()),
                "Body": encoded,
                "sensor": tag,
                "deviceId": "collar01",
                "timestamp": payload_dict.get("timestamp", self.get_timestamp())
            }
            self.container.create_item(body=doc)
            print("[COSMOS] AI telemetry stored.")
        except Exception as e:
            print(f"[COSMOS ERROR] {e}")

    def connect_and_listen(self, on_message, topics):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print("[MQTT] AI connected to broker.")
                for topic, qos in topics:
                    client.subscribe((topic, qos))
                    print(f"[MQTT] Subscribed to: {topic}")
            else:
                print(f"[MQTT ERROR] Failed with code {rc}")

        self.client.on_connect = on_connect
        self.client.on_message = on_message

        for attempt in range(10):
            try:
                print(f"[MQTT] Connecting (attempt {attempt+1})...")
                self.client.connect(self.broker, self.port, 60)
                self.client.loop_start()
                return
            except Exception as e:
                print(f"[MQTT ERROR] Attempt {attempt+1}: {e}")
                time.sleep(1)

        print("[MQTT ERROR] Failed to connect after 10 attempts.")
