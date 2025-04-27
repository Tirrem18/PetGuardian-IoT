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

# Load environment variables from .env file
load_dotenv()

# Suppress Azure SDK logs to avoid clutter
logging.getLogger("azure").setLevel(logging.WARNING)

# --- AI Utility Class ---
class AIUtils:
    def __init__(self, client_id="ai_core"):
        self.timestamp_format = "%Y-%m-%d %H:%M:%S"  # Timestamp format for logs

        # --- MQTT Setup ---
        self.broker = os.getenv("MQTT_BROKER")
        self.port = int(os.getenv("MQTT_PORT", "8883"))
        self.username = os.getenv("MQTT_USERNAME")
        self.password = os.getenv("MQTT_PASSWORD")
        self.client = mqtt.Client(client_id=client_id)  # Create MQTT client with provided ID
        self.client.username_pw_set(self.username, self.password)
        self.client.tls_set()

        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            print("[MQTT] AIUtils MQTT client connected and loop started.")
        except Exception as e:
            print(f"[MQTT ERROR] Could not connect in AIUtils init: {e}")

        # --- Azure IoT Hub Setup ---
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

    # --- Generate Current Timestamp ---
    def get_timestamp(self):
        return time.strftime(self.timestamp_format)

    # --- Publish to MQTT ---
    def publish(self, topic, payload_dict):
        payload = json.dumps(payload_dict)
        for attempt in range(3):  # Retry up to 3 times
            try:
                result = self.client.publish(topic, payload)
                print(f"[MQTT] Published to {topic}")
                return True
            except Exception as e:
                print(f"[MQTT ERROR] Attempt {attempt + 1} failed: {e}")
                time.sleep(1)
        print(f"[MQTT ERROR] Failed to publish to {topic}")
        return False

    # --- Send to Azure IoT Hub ---
    def send_to_azure(self, payload_dict):
        try:
            payload = json.dumps(payload_dict)
            client = IoTHubDeviceClient.create_from_connection_string(self.azure_conn)
            client.send_message(Message(payload))
            client.disconnect()
        except Exception as e:
            print(f"[AZURE ERROR] {e}")

    # --- Send to Azure Cosmos DB ---
    def send_to_cosmos(self, payload_dict, tag="ai"):
        if not self.use_cosmos:
            return
        try:
            encoded = base64.b64encode(json.dumps(payload_dict).encode()).decode()
            doc = {
                "id": str(uuid.uuid4()),  # Unique ID for document
                "Body": encoded,  # Store payload base64 encoded
                "sensor": tag,  # Label (default 'ai')
                "deviceId": "collar01",  # Hardcoded device ID
                "timestamp": payload_dict.get("timestamp", self.get_timestamp())
            }
            self.container.create_item(body=doc)
        except Exception as e:
            print(f"[COSMOS ERROR] {e}")

    # --- Connect and Listen to MQTT Topics ---
    def connect_and_listen(self, on_message, topics):
        # Topics should be a list of tuples: [(topic, qos)]
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                for topic, qos in topics:
                    client.subscribe((topic, qos))
            else:
                print(f"[MQTT ERROR] Failed to connect with code {rc}")

        self.client.on_connect = on_connect
        self.client.on_message = on_message

        for attempt in range(10):
            try:
                self.client.connect(self.broker, self.port, 60)
                self.client.loop_start()
                return
            except Exception as e:
                print(f"[MQTT ERROR] Attempt {attempt + 1}: {e}")
                time.sleep(1)

        print("[MQTT ERROR] Failed to connect after 10 attempts.")

    # --- Local Logging ---
    def log_locally(self, file_name, data):
        try:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            log_dir = os.path.join(root_dir, "data", "logs")
            os.makedirs(log_dir, exist_ok=True)
            path = os.path.join(log_dir, file_name)

            logs = []
            if os.path.exists(path):
                with open(path, "r") as f:
                    try:
                        logs = json.load(f)
                    except:
                        logs = []  # Start fresh if file corrupted

            logs.append(data)
            with open(path, "w") as f:
                json.dump(logs, f, indent=4)

        except Exception as e:
            print(f"[LOCAL LOG ERROR] {e}")
