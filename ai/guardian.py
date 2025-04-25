import time
import threading
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.threats_ai import ThreatAI
from ai.utils.ai_utils import AIUtils


TOPICS = [
    ("petguardian/acoustic", 0),
    ("petguardian/imu", 0),
    ("petguardian/lux", 0),
    ("petguardian/camera", 0),
    ("petguardian/gps", 0)
]

class GuardianAI:
    def __init__(self, client_id="guardian_core"):
        
        self.ai = AIUtils(client_id="guardian_core")
        print(f"[MQTT] Using client_id: {client_id}")


        self.threat_ai = ThreatAI(client_id="threats_core")

        self.enable_illuminator = False
        self.enable_threats = False
        self.verbose = False

        self.load_feature_config()

    def load_feature_config(self):
        """Simulate loading config from Cosmos DB or another source."""
        try:
            # Placeholder config fetch (replace with Cosmos fetch in future)
            config = {
                "illuminator_enabled": False,
                "threats_enabled": True  # ENABLE THREAT AI by default for testing
            }

            self.enable_illuminator = config.get("illuminator_enabled", False)
            self.enable_threats = config.get("threats_enabled", False)

            print(f"[CONFIG] Illuminator enabled: {self.enable_illuminator}")
            print(f"[CONFIG] Threat detection enabled: {self.enable_threats}")

        except Exception as e:
            print(f"[CONFIG ERROR] Failed to load config: {e}")
            print("[CONFIG] Using default settings (both off)")

    def handle_ai_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode(errors='ignore'))
            topic = msg.topic

            if self.verbose:
                print(f"\n📡 MQTT: {topic}")
                print(json.dumps(payload, indent=2))

            # Route messages to Threat AI
            if self.enable_threats:
                if topic == "petguardian/acoustic":
                    self.threat_ai.handle_acoustic_event(payload)

                elif topic == "petguardian/gps":
                    self.threat_ai.handle_gps_event(payload)

        except Exception as e:
            print(f"⚠️ Failed to parse or handle message: {e}")

    def start_mqtt_listener(self):
        topic_list = [topic for topic, _ in TOPICS]
        print(f"[MQTT] Subscribed to: {', '.join(topic_list)}")
        print("[MQTT] Enabled MQTT listener thread for topics...\n")
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
        print("\n🛡️ Guardian starting in collar mode (live system)...\n")
        self.verbose = False
        self.start_mqtt_listener()

        from sensors import imu_sensor, acoustic_sensor, gps_sensor, lux_sensor, camera_sensor, led_bulb

        if self.enable_illuminator:
            self.safe_start("IMU Listener", imu_sensor.start_imu_listener)
            

        if self.enable_threats:
            self.safe_start("Acoustic Listener", acoustic_sensor.start_acoustic_listener)

        self.safe_start("LUX Listener", lux_sensor.start_lux_listener)
        self.safe_start("Bulb Listener", led_bulb.start_bulb_listener)
        self.safe_start("Camera Listener", camera_sensor.start_camera_listener)
        self.safe_start("GPS Listener", gps_sensor.start_gps_listener)

        print("\n✅ Guardian AI sensors active.\n")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Guardian shutting down (collar mode).")

def start_guardian():
    GuardianAI().start()

if __name__ == "__main__":
    GuardianAI().listen_only()