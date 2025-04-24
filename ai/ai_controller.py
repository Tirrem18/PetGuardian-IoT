import paho.mqtt.client as mqtt
import json
import time
import threading
from dashboard.dashboard_data import load_threat_config_from_cosmos

try:
    from ai.threat_detector_ai import ThreatDetector
except ModuleNotFoundError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ai.threat_detector_ai import ThreatDetector

from sensors import gps_sensor, camera_sensor, acoustic_sensor

# HiveMQ Cloud Configuration
BROKER = "a5c9d1ea0e224376ad6285eb8aa83d55.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "username"
PASSWORD = "Password1"

TOPICS = [
    ("petguardian/iot", 0),
    ("petguardian/gps", 0),
    ("petguardian/light", 0)
]

# Initialize the AI
cfg = load_threat_config_from_cosmos()
print("[AI CONFIG LOADED]", json.dumps(cfg, indent=2))

if cfg:
    threat_ai = ThreatDetector(
        home_location=(cfg["home_lat"], cfg["home_lon"]),
        safe_radius=cfg["safe_radius"],
        threat_cooldown_seconds=cfg["cooldown"],
        sound_window=cfg["sound_window"],
        min_sounds=cfg["min_sounds"],
        min_sound_interval=cfg["min_interval"],
        threat_enabled=cfg.get("threat_enabled", True)
    )
else:
    raise RuntimeError("Failed to load threat detection config.")

# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ AI Connected to MQTT broker.")
        for topic, qos in TOPICS:
            client.subscribe((topic, qos))
            print(f"🔔 AI Subscribed to topic: {topic}")
    else:
        print(f"❌ AI connection failed with code {rc}")

def on_message(client, userdata, msg):
    print(f"\n📥 Raw MQTT message received from topic: {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode(errors='ignore'))
        print(f"📄 Parsed Message: {json.dumps(payload, indent=2)}")

        result = threat_ai.handle(payload)

        if result == "awaiting_gps":
            print("🛰️ Waiting for GPS fix to confirm threat...")
            publish_with_retry(client, "petguardian/trigger/gps", { "command": "get_gps" })

        elif result == "threat_triggered":
            print("📸 Threat confirmed — triggering camera!")
            publish_with_retry(client, "petguardian/trigger/camera", { "command": "get_camera" })

    except Exception as e:
        print(f"⚠️ Error processing message: {e}")

def publish_with_retry(client, topic, payload_dict, max_retries=3):
    payload = json.dumps(payload_dict)
    for attempt in range(1, max_retries + 1):
        try:
            result = client.publish(topic, payload)
            status = result[0]
            if status == 0:
                print(f"📤 Published to {topic}: {payload}")
                break
            else:
                raise Exception(f"Publish returned error status {status}")
        except Exception as e:
            print(f"⚠️ MQTT publish error (attempt {attempt}): {e}")
            if attempt < max_retries:
                time.sleep(1)
            else:
                print(f"🛑 Failed to publish to {topic} after {max_retries} attempts.")

def safe_start(name, func):
    try:
        print(f" [AI] Starting {name} listener thread...")
        func()
    except Exception as e:
        print(f" [AI] {name} thread crashed: {e}")

def start_ai_listener():
    print("🧠 Starting AI MQTT listener...")
    client = mqtt.Client(client_id="ai_controller")
    client.username_pw_set(USERNAME, PASSWORD)
    client.tls_set()

    client.on_connect = on_connect
    client.on_message = on_message

    if threat_ai.threat_enabled:
        gps_thread = threading.Thread(target=lambda: safe_start("GPS", gps_sensor.start_gps_listener))
        cam_thread = threading.Thread(target=lambda: safe_start("Camera", camera_sensor.start_camera_listener))

        def run_acoustic_full():
            acoustic_sensor.start_acoustic_listener()
            acoustic_sensor.start_acoustic_sensor()

        acoustic_thread = threading.Thread(target=lambda: safe_start("Acoustic", run_acoustic_full))

        gps_thread.start()
        time.sleep(1)
        cam_thread.start()
        time.sleep(1)
        acoustic_thread.start()

        print(" [AI] All sensor threads running (Threat Detection enabled).")
    else:
        print(" 🛑 Threat Detection is OFF — sensor threads will not start.")

    if cfg.get("safemode_enabled", False):
        print("🌙 SafeMode is ON — Starting light fusion system...")

        # Import here to avoid circular import errors at the top
        from sensors import lux_sensor, imu_sensor, led_bulb, safemode_fusion

        lux_thread = threading.Thread(target=lambda: safe_start("Lux", lux_sensor.start_lux_listener))
        imu_thread = threading.Thread(target=lambda: safe_start("IMU", imu_sensor.start_imu_listener))
        led_thread = threading.Thread(target=lambda: safe_start("LED Bulb", led_bulb.start_led_listener))
        fusion_thread = threading.Thread(target=lambda: safe_start("SafeMode Fusion", safemode_fusion.start_fusion_monitor))

        lux_thread.start()
        time.sleep(1)
        imu_thread.start()
        time.sleep(1)
        fusion_thread.start()
        time.sleep(1)
        led_thread.start()

        print(" [AI] All SafeMode sensor threads running (Light Fusion system active).")

    else:
        print("🌙 SafeMode is OFF — light sensor, IMU, and LED threads skipped.")

    max_retries = 10
    retry_delay = 1

    for attempt in range(1, max_retries + 1):
        try:
            print(f"🔄 AI MQTT connect attempt {attempt}...")
            client.connect(BROKER, PORT, 60)
            client.loop_forever()
            break
        except Exception as e:
            print(f"❌ Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                print("🛑 Max retries reached. MQTT connection failed.")

if __name__ == "__main__":
    start_ai_listener()