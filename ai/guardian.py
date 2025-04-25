# ai/guardian.py

import time
import threading
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.utils.ai_utils import AIUtils

TOPICS = [
    ("petguardian/acoustic", 0),
    ("petguardian/imu", 0),
    ("petguardian/lux", 0),
    ("petguardian/camera", 0),
    ("petguardian/gps", 0)
]

class GuardianAI:
    def __init__(self):
        self.ai = AIUtils()
        self.enable_imu_thread = False
        self.enable_acoustic_thread = False
        self.verbose = False

    def handle_ai_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode(errors='ignore'))
            if self.verbose:
                print(f"\n📡 MQTT: {msg.topic}")
                print(json.dumps(payload, indent=2))
        except Exception as e:
            print(f"⚠️ Failed to parse message: {e}")

    def start_mqtt_listener(self):
        print("📡 Starting MQTT listener thread...")
        thread = threading.Thread(
            target=lambda: self.ai.connect_and_listen(
                on_message=self.handle_ai_message,
                topics=TOPICS
            ),
            name="MQTTListener",
            daemon=True
        )
        thread.start()

    def safe_start(self, name, func):
        """Start a sensor thread silently, only show if something goes wrong."""
        def run_wrapper():
            try:
                func()
            except Exception as e:
                print(f" [GUARDIAN ERROR] ❌ {name} crashed with exception: {e}")

        try:
            thread = threading.Thread(target=run_wrapper, name=name, daemon=True)
            thread.start()
        except Exception as e:
            print(f" [GUARDIAN ERROR] ❌ Failed to start {name}: {e}")

    def listen_only(self):
        print("\n👁️  Guardian AI (interactive mode)...")
        self.verbose = True
        self.ai.connect_and_listen(on_message=self.handle_ai_message, topics=TOPICS)
        print("📡 Guardian is listening to MQTT topics...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Guardian shutting down (test mode).")

    def start(self):
        print("\n🛡️ Guardian starting in collar mode (live system)...")
        self.verbose = False
        self.start_mqtt_listener()

        from sensors import imu_sensor, acoustic_sensor, gps_sensor, lux_sensor, camera_sensor, led_bulb

        if self.enable_imu_thread:
            self.safe_start("IMU Listener", imu_sensor.start_imu_listener)
            self.safe_start("LUX Listener", lux_sensor.start_lux_listener)
            self.safe_start("Bulb Listener", led_bulb.start_bulb_listener)

        if self.enable_acoustic_thread:
            self.safe_start("Acoustic Listener", acoustic_sensor.start_acoustic_listener)
            self.safe_start("Camera Listener", camera_sensor.start_camera_listener)

        self.safe_start("GPS Listener", gps_sensor.start_gps_listener)
        self.safe_start("LUX Listener", lux_sensor.start_lux_listener)
        self.safe_start("Bulb Listener", led_bulb.start_bulb_listener)
        self.safe_start("Camera Listener", camera_sensor.start_camera_listener)

        print("✅ Guardian AI sensors active.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Guardian shutting down (collar mode).")

def start_guardian():
    GuardianAI().start()

if __name__ == "__main__":
    GuardianAI().listen_only()
