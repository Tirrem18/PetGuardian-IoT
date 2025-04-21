import paho.mqtt.client as mqtt
import json
import time
try:
    from ai.threat_detector_ai import ThreatDetector
except ModuleNotFoundError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ai.threat_detector_ai import ThreatDetector


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
threat_ai = ThreatDetector(
    home_location=(54.5742, -1.2345),
    safe_radius=30,
    threat_cooldown_seconds=30,
    sound_window=10,
    min_sounds=3,
    min_sound_interval=1
)

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

# Listener function
def start_ai_listener():
    print("🧠 Starting AI MQTT listener...")
    client = mqtt.Client(client_id="ai_controller")
    client.username_pw_set(USERNAME, PASSWORD)
    client.tls_set()

    client.on_connect = on_connect
    client.on_message = on_message

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


# Entry point
if __name__ == "__main__":
    start_ai_listener()
