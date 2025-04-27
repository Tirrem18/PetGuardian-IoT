import os
import sys
import time
import json
import threading

# Ensure project root is in sys.path for clean imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Internal Imports ---
from ai.threats_ai import ThreatAI
from ai.illuminator_ai import IlluminatorAI
from ai.utils.ai_utils import AIUtils
from dashboard.util.dashboard_data import DashboardData

# --- MQTT Topics Subscribed ---
TOPICS = [
    ("petguardian/acoustic", 0),
    ("petguardian/imu", 0),
    ("petguardian/lux", 0),
    ("petguardian/camera", 0),
    ("petguardian/gps", 0)
]

# --- GuardianAI Main Class ---
class GuardianAI:
    def __init__(self, client_id="guardian_core"):
        self.ai = AIUtils(client_id=client_id)
        print(f"[MQTT] Using client_id: {client_id}")

        # Initialize internal AI modules
        self.threat_ai = ThreatAI(client_id="threats_core")
        self.illuminator_ai = IlluminatorAI(client_id="illuminator_core")

        # Feature toggles (default disabled)
        self.enable_illuminator = False
        self.enable_threats = False
        self.verbose = False

        self.load_feature_config()

    # --- Load Feature Toggles from Dashboard ---
    def load_feature_config(self):
        try:
            config = DashboardData().load_dashboard_settings()
            self.enable_illuminator = config.get("illumination_mode", False)
            self.enable_threats = config.get("threats_mode", False)

            print(f"[CONFIG] Illuminator enabled: {self.enable_illuminator}")
            print(f"[CONFIG] Threat detection enabled: {self.enable_threats}")

        except Exception as e:
            print(f"[CONFIG ERROR] Failed to load config: {e}")
            print("[CONFIG] Using default settings (both disabled)")

    # --- Handle Incoming MQTT Messages ---
    def handle_ai_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode(errors='ignore'))
            topic = msg.topic

            if self.verbose:
                print(f"\n[MQTT] Message on topic {topic}")
                print(json.dumps(payload, indent=2))

            if self.enable_threats:
                if topic == "petguardian/acoustic":
                    self.threat_ai.handle_acoustic_event(payload)
                elif topic == "petguardian/gps":
                    self.threat_ai.handle_gps_event(payload)

            if self.enable_illuminator:
                if topic == "petguardian/imu":
                    self.illuminator_ai.handle_imu_event(payload)
                elif topic == "petguardian/lux":
                    self.illuminator_ai.handle_lux_event(payload)
                elif topic == "petguardian/gps":
                    self.illuminator_ai.handle_gps_event(payload)

        except Exception as e:
            print(f"[ERROR] Failed to handle message: {e}")

    # --- Start Background MQTT Listener Thread ---
    def start_mqtt_listener(self):
        topic_list = [topic for topic, _ in TOPICS]
        print(f"[MQTT] Subscribed to topics: {', '.join(topic_list)}")
        print("[MQTT] Starting MQTT listener thread...\n")

        thread = threading.Thread(
            target=lambda: self.ai.connect_and_listen(
                on_message=self.handle_ai_message,
                topics=TOPICS
            ),
            name="MQTTListener",
            daemon=True
        )
        thread.start()

    # --- Safe Thread Starter for Sensor Components ---
    def safe_start(self, name, func):
        def run_wrapper():
            try:
                func()
            except Exception as e:
                print(f"[GUARDIAN ERROR] {name} crashed with exception: {e}")

        try:
            thread = threading.Thread(target=run_wrapper, name=name, daemon=True)
            thread.start()
        except Exception as e:
            print(f"[GUARDIAN ERROR] Failed to start {name}: {e}")

    # --- Developer Mode: Listen Only ---
    def listen_only(self):
        print("\n[GUARDIAN] Starting in interactive listen mode...")
        self.verbose = True

        self.ai.connect_and_listen(on_message=self.handle_ai_message, topics=TOPICS)
        print("Guardian is actively listening to MQTT topics.")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[GUARDIAN] Shutdown requested (listen mode).")

    # --- Full Live Startup: Collar Mode ---
    def start(self):
        print("\n[GUARDIAN] Starting in collar mode (live system)...\n")
        self.verbose = False
        self.start_mqtt_listener()

        # Import sensor modules only when starting
        from sensors import imu_sensor, acoustic_sensor, gps_sensor, lux_sensor, camera_sensor, led_bulb

        # Conditionally start each sensor
        if self.enable_illuminator:
            self.safe_start("IMU Listener", imu_sensor.start_imu_listener)

        if self.enable_threats:
            self.safe_start("Acoustic Listener", acoustic_sensor.start_acoustic_listener)

        self.safe_start("LUX Listener", lux_sensor.start_lux_listener)
        self.safe_start("Bulb Listener", led_bulb.start_bulb_listener)
        self.safe_start("Camera Listener", camera_sensor.start_camera_listener)
        self.safe_start("GPS Listener", gps_sensor.start_gps_listener)

        print("\n[GUARDIAN] All sensors active.\n")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[GUARDIAN] Shutdown requested (collar mode).")

# --- External Entrypoint ---
def start_guardian():
    GuardianAI().start()

# --- Manual Developer Test Entrypoint ---
if __name__ == "__main__":
    GuardianAI().listen_only()
