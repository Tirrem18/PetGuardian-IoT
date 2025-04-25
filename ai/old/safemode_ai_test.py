import time
import os
import json
import base64
import uuid
from math import sqrt
from azure.iot.device import IoTHubDeviceClient, Message
from azure.cosmos import CosmosClient
import paho.mqtt.client as mqtt

from ai.utils.threat_uploader import send_threat_to_cosmos, send_threat_to_azure

# MQTT + Azure setup
BROKER = "a5c9d1ea0e224376ad6285eb8aa83d55.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "username"
PASSWORD = "Password1"
BULB_TOPIC = "petguardian/trigger/bulb"

IOTHUB_CONNECTION_STRING = "HostName=IoTPawTrack.azure-devices.net;DeviceId=collar01;SharedAccessKey=ShzFs2jgI06rAjksNrEst8Byb8x2ljbHrBGYT+raQ1E="
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

cosmos_client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
database = cosmos_client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

mqtt_client = mqtt.Client("safemode_fusion")
mqtt_client.username_pw_set(USERNAME, PASSWORD)
mqtt_client.tls_set()
mqtt_client.connect(BROKER, PORT, 60)
mqtt_client.loop_start()


class SafeModeLightAI:
    def __init__(self, lux_threshold=30, imu_threshold=5, cooldown_seconds=30, safemode_enabled=True):
        self.lux_threshold = lux_threshold
        self.imu_threshold = imu_threshold
        self.cooldown_seconds = cooldown_seconds
        self.safemode_enabled = safemode_enabled

        self.last_trigger_time = 0
        self.awaiting_lux = False
        self.awaiting_lux_since = None
        self.last_accel_mag = None

    def handle(self, payload):
        if not self.safemode_enabled:
            print("⚠️ SafeMode is OFF — ignoring incoming data.")
            return False

        if payload.get("sensor") == "imu":
            return self._handle_imu(payload)
        elif payload.get("sensor") == "lux":
            return self._handle_lux(payload)

        return False

    def _handle_imu(self, data):
        try:
            mag = sqrt(data["accel_x"]**2 + data["accel_y"]**2 + data["accel_z"]**2)
        except KeyError:
            print("⚠️ IMU payload missing acceleration keys.")
            return False

        print(f"[IMU] Movement magnitude: {mag:.2f}")

        if mag >= self.imu_threshold and time.time() - self.last_trigger_time >= self.cooldown_seconds:
            print("📡 Movement detected — requesting lux reading...")
            self.awaiting_lux = True
            self.awaiting_lux_since = time.time()
            self.last_accel_mag = mag
            mqtt_client.publish("petguardian/trigger/lux", json.dumps({"command": "get_lux"}))
            return "awaiting_lux"

        return False

    def _handle_lux(self, data):
        if not self.awaiting_lux:
            return False

        lux = data.get("lux", 100)
        print(f"[LUX] Received lux: {lux}")

        self.awaiting_lux = False
        self.awaiting_lux_since = None

        if lux <= self.lux_threshold:
            print("🌙 Low light + movement — triggering bulb.")
            self._trigger_response(lux)
            return "bulb_triggered"
        else:
            print("🔆 Lux OK. Skipping bulb trigger.")
            return False

    def _trigger_response(self, lux):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        reason = f"IMU {self.last_accel_mag:.2f} + LUX {lux}"

        entry = {
            "timestamp": timestamp,
            "accel_magnitude": self.last_accel_mag,
            "lux": lux,
            "reason": reason
        }

        self._log_locally(entry)
        send_threat_to_cosmos(timestamp, ("N/A", "N/A"), reason)
        send_threat_to_azure(timestamp, ("N/A", "N/A"), reason)

        mqtt_client.publish(BULB_TOPIC, json.dumps({"command": "turn_on"}))
        self.last_trigger_time = time.time()

    def _log_locally(self, entry):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(base_dir, "data", "logs")
        os.makedirs(log_dir, exist_ok=True)
        path = os.path.join(log_dir, "safemode_log.json")

        logs = []
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    logs = json.load(f)
            except:
                logs = []

        logs.append(entry)
        with open(path, "w") as f:
            json.dump(logs, f, indent=4)
