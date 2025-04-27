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

# Load environment variables from .env file
load_dotenv()

# Configure logging to suppress unnecessary logs from Azure SDKs
logging.getLogger("azure").setLevel(logging.WARNING)  # General Azure SDK warnings only
logging.getLogger("azure.iot").setLevel(logging.ERROR)  # IoT SDK errors only
logging.getLogger("azure.iot.device").setLevel(logging.ERROR)  # Device-specific errors only


# Utility class for common sensor operations
class SensorUtils:
    def __init__(self, sensor_name, topic_publish=None, topic_trigger=None):
        # Store sensor name and optional MQTT topics
        self.sensor = sensor_name
        self.topic_publish = topic_publish
        self.topic_trigger = topic_trigger
        self.timestamp_format = "%Y-%m-%d %H:%M:%S"  # Standardized timestamp format for all events

        # --- MQTT Setup ---
        self.mqtt_client = mqtt.Client(client_id=f"{sensor_name}_client")  # Create MQTT client with unique ID
        self.mqtt_client.username_pw_set(
            os.getenv("MQTT_USERNAME", "username"),
            os.getenv("MQTT_PASSWORD", "Password1")
        )  # Set MQTT credentials from .env or defaults
        self.mqtt_client.tls_set()  # Enable encrypted communication (TLS)
        self.broker = os.getenv("MQTT_BROKER", "a5c9d1ea0e224376ad6285eb8aa83d55.s1.eu.hivemq.cloud")  # MQTT broker address
        self.port = int(os.getenv("MQTT_PORT", "8883"))  # MQTT broker secure port

        # --- Azure IoT Hub Setup ---
        self.azure_conn = os.getenv(
            "AZURE_CONN",
            "HostName=IoTPawTrack.azure-devices.net;DeviceId=collar01;SharedAccessKey=..."
        )  # IoT Hub connection string

        # --- Cosmos DB Setup ---
        self.cosmos_uri = os.getenv("COSMOS_URI", "https://petguardiandb.documents.azure.com:443/")  # Cosmos DB URI
        self.cosmos_key = os.getenv("COSMOS_KEY", "your-key")  # Cosmos DB key
        self.database_name = os.getenv("COSMOS_DB", "iotdata")  # Target database
        self.container_name = os.getenv("COSMOS_CONTAINER", "telemetry")  # Target container inside database

        # Initialize Cosmos DB client and container reference
        self.cosmos_client = CosmosClient(self.cosmos_uri, credential=self.cosmos_key)
        db = self.cosmos_client.get_database_client(self.database_name)
        self.container = db.get_container_client(self.container_name)

        # --- Local Log Directory Setup ---
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))  # Project root
        self.log_dir = os.path.join(root_dir, "data", "logs")  # Path for saving local JSON logs
        os.makedirs(self.log_dir, exist_ok=True)  # Create directory if missing

    # Generate a timestamp string based on current system time
    def get_timestamp(self):
        return time.strftime(self.timestamp_format)

    # Save a list of logs locally into a specified JSON file
    def log_locally(self, file_name, data):
        path = os.path.join(self.log_dir, file_name)
        logs = []
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    logs = json.load(f)  # Load existing logs
            except:
                pass  # Ignore file errors and start fresh if necessary
        logs.append(data)  # Append new data entry
        with open(path, "w") as f:
            json.dump(logs, f, indent=4)  # Save updated log list

    # Send a JSON payload to the configured MQTT topic
    def send_to_mqtt(self, payload_dict):
        payload = json.dumps(payload_dict)  # Convert dict to JSON string
        for attempt in range(3):  # Retry up to 3 times on failure
            try:
                self.mqtt_client.publish(self.topic_publish, payload)
                print(f"[MQTT] Published to {self.topic_publish}")
                break
            except Exception as e:
                print(f"[MQTT ERROR] Attempt {attempt+1}: {e}")
                time.sleep(1)  # Small delay between retries

    # Send a payload to Azure IoT Hub
    def send_to_azure(self, payload_dict):
        try:
            payload = json.dumps(payload_dict)
            client = IoTHubDeviceClient.create_from_connection_string(self.azure_conn)
            client.send_message(Message(payload))  # Send the message to IoT Hub
            client.disconnect()  # Disconnect cleanly
            print("[AZURE] Data sent to IoT Hub.")
        except Exception as e:
            print(f"[AZURE ERROR] {e}")

    # Store a payload as a document inside Cosmos DB
    def send_to_cosmos(self, payload_dict):
        try:
            encoded = base64.b64encode(json.dumps(payload_dict).encode()).decode()  # Encode data safely as base64
            doc = {
                "id": str(uuid.uuid4()),  # Unique document ID
                "Body": encoded,  # Payload encoded as string
                "sensor": self.sensor,  # Sensor name
                "deviceId": "collar01",  # Hardcoded device ID for now
                "timestamp": payload_dict.get("timestamp", self.get_timestamp())  # Use timestamp if present
            }
            self.container.create_item(body=doc)  # Insert document into Cosmos container
            print("[COSMOS] Data stored.")
        except Exception as e:
            print(f"[COSMOS ERROR] {e}")

    # Start MQTT client listener to handle trigger messages
    def start_mqtt_listener(self, on_message_callback):
        # Inner function to handle connection events
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print(f"[MQTT] {self.sensor} connected.")
                print(f"[MQTT] Subscribing to topic: {self.topic_trigger}")
                client.subscribe(self.topic_trigger)  # Subscribe to trigger topic
                client.message_callback_add(self.topic_trigger, on_message_callback)  # Add specific callback for trigger topic
            else:
                print(f"[MQTT ERROR] Connect failed with code {rc}")

        self.mqtt_client.on_connect = on_connect  # Assign connection callback

        # Assign fallback debug message handler
        self.mqtt_client.on_message = lambda client, userdata, msg: print(
            f"[DEBUG] Unhandled topic {msg.topic}: {msg.payload.decode(errors='ignore')}"
        )

        # Try to connect and start the MQTT loop
        for attempt in range(10):
            try:
                self.mqtt_client.connect(self.broker, self.port, 60)  # Connect to broker
                self.mqtt_client.loop_start()  # Start MQTT listening loop
                print(f"[MQTT] {self.sensor} listener started.")
                return
            except Exception as e:
                print(f"[MQTT ERROR] Attempt {attempt+1}: {e}")
                time.sleep(1)  # Wait before retrying
