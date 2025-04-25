import os
import json
import uuid
import time
import base64
import logging
import paho.mqtt.client as mqtt
from azure.iot.device import IoTHubDeviceClient, Message
from azure.cosmos import CosmosClient
import logging
from dotenv import load_dotenv
load_dotenv()

# Suppress general Azure SDK logs to WARNING
logging.getLogger("azure").setLevel(logging.WARNING)
# Suppress specifically the IoT device SDK logs to ERROR
logging.getLogger("azure.iot").setLevel(logging.ERROR)
# You can also suppress any other verbose modules if needed
logging.getLogger("azure.iot.device").setLevel(logging.ERROR)


class SensorUtils:
    def __init__(self, sensor_name, topic_publish=None, topic_trigger=None):
        self.sensor = sensor_name
        self.topic_publish = topic_publish
        self.topic_trigger = topic_trigger
        self.timestamp_format = "%Y-%m-%d %H:%M:%S"

        # MQTT setup
        self.mqtt_client = mqtt.Client(client_id=f"{sensor_name}_client")
        self.mqtt_client.username_pw_set(os.getenv("MQTT_USERNAME", "username"), os.getenv("MQTT_PASSWORD", "Password1"))
        self.mqtt_client.tls_set()
        self.broker = os.getenv("MQTT_BROKER", "a5c9d1ea0e224376ad6285eb8aa83d55.s1.eu.hivemq.cloud")
        self.port = int(os.getenv("MQTT_PORT", "8883"))

        # Azure IoT Hub
        self.azure_conn = os.getenv("AZURE_CONN", "HostName=IoTPawTrack.azure-devices.net;DeviceId=collar01;SharedAccessKey=...")
        
        # Cosmos DB
        self.cosmos_uri = os.getenv("COSMOS_URI", "https://petguardiandb.documents.azure.com:443/")
        self.cosmos_key = os.getenv("COSMOS_KEY", "your-key")
        self.database_name = os.getenv("COSMOS_DB", "iotdata")
        self.container_name = os.getenv("COSMOS_CONTAINER", "telemetry")

        self.cosmos_client = CosmosClient(self.cosmos_uri, credential=self.cosmos_key)
        db = self.cosmos_client.get_database_client(self.database_name)
        self.container = db.get_container_client(self.container_name)

        # Local Logging
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.log_dir = os.path.join(root_dir, "data", "logs")

        os.makedirs(self.log_dir, exist_ok=True)

    def get_timestamp(self):
        return time.strftime(self.timestamp_format)

    def log_locally(self, file_name, data):
        path = os.path.join(self.log_dir, file_name)
        logs = []
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    logs = json.load(f)
            except:
                pass
        logs.append(data)
        with open(path, "w") as f:
            json.dump(logs, f, indent=4)

    def send_to_mqtt(self, payload_dict):
        payload = json.dumps(payload_dict)
        for attempt in range(3):
            try:
                self.mqtt_client.publish(self.topic_publish, payload)
                print(f"[MQTT] Published to {self.topic_publish}")
                break
            except Exception as e:
                print(f"[MQTT ERROR] Attempt {attempt+1}: {e}")
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

    def send_to_cosmos(self, payload_dict):
        try:
            encoded = base64.b64encode(json.dumps(payload_dict).encode()).decode()
            doc = {
                "id": str(uuid.uuid4()),
                "Body": encoded,
                "sensor": self.sensor,
                "deviceId": "collar01",
                "timestamp": payload_dict.get("timestamp", self.get_timestamp())
            }
            self.container.create_item(body=doc)
            print("[COSMOS] Data stored.\n")
        except Exception as e:
            print(f"[COSMOS ERROR] {e}")

    def start_mqtt_listener(self, on_message_callback):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print(f"[MQTT] {self.sensor} connected.")
                print(f"[MQTT] Subscribing to topic: {self.topic_trigger}")
                client.subscribe(self.topic_trigger)
                client.message_callback_add(self.topic_trigger, on_message_callback)
            else:
                print(f"[MQTT ERROR] Connect failed with code {rc}")

        self.mqtt_client.on_connect = on_connect

        # Optional debug (only one global handler is allowed)
        self.mqtt_client.on_message = lambda client, userdata, msg: print(
            f"[DEBUG] Unhandled topic {msg.topic}: {msg.payload.decode(errors='ignore')}"
        )

        for attempt in range(10):
            try:
                self.mqtt_client.connect(self.broker, self.port, 60)
                self.mqtt_client.loop_start()
                print(f"[MQTT] {self.sensor} listener started.")
                return
            except Exception as e:
                print(f"[MQTT ERROR] Attempt {attempt+1}: {e}")
            time.sleep(1)
