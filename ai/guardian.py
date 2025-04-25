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
        self.enable_imu_thread = True
        self.enable_acoustic_thread = True
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
        """Safely start a thread and catch fast exits or exceptions."""
        def run_wrapper():
            print(f" [GUARDIAN] ▶️ {name} starting...")
            try:
                func()
            except Exception as e:
                print(f" [GUARDIAN ERROR] ❌ {name} crashed with exception: {e}")
            else:
                if time.time() - start_time < 1:
                    print(f" [GUARDIAN WARNING] ⚠️ {name} exited immediately. Is it non-blocking?")
                else:
                    print(f" [GUARDIAN] ⛔️ {name} stopped unexpectedly.")

        try:
            start_time = time.time()
            thread = threading.Thread(target=run_wrapper, name=name, daemon=True)
            thread.start()
            print(f" [GUARDIAN] ✅ {name} thread launched.")
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

        from sensors import imu_sensor, acoustic_sensor

        print("\n▶️ Sensor Startup Summary:")
        print(f"   - IMU Enabled:    {self.enable_imu_thread}")
        print(f"   - Sound Enabled:  {self.enable_acoustic_thread}")

        if self.enable_imu_thread:
            self.safe_start("IMU Listener", imu_sensor.start_imu_listener)
        if self.enable_acoustic_thread:
            self.safe_start("Acoustic Listener", acoustic_sensor.start_acoustic_listener)

        # Give threads a moment to boot up
        time.sleep(2)

        print("\n📋 Thread Status Check:")
        for t in threading.enumerate():
            print(f"   - 🧵 {t.name} (alive: {t.is_alive()})")

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
