import paho.mqtt.client as mqtt
import json
from threat_detector_ai import ThreatDetector


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


# Initialize the AI with test settings
threat_ai = ThreatDetector(
    home_location=(54.5742, -1.2345),   # Replace with your actual home lat/lon
    safe_radius=30,
    threat_cooldown_seconds=30,
    sound_window=10,
    min_sounds=3,
    min_sound_interval=1
)

# Called when the client connects
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to MQTT broker.")
        for topic, qos in TOPICS:
            client.subscribe((topic, qos))
            print(f"📡 Subscribed to topic: {topic}")
    else:
        print(f"❌ Connection failed with code {rc}")

# Called when a message is received
def on_message(client, userdata, msg):
    print(f"\n📥 Raw MQTT message received from topic: {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode(errors='ignore'))
        print(f"📄 Parsed Message: {json.dumps(payload, indent=2)}")

        # Send data to AI
        result = threat_ai.handle(payload)

        if result == "awaiting_gps":
            print("🛰️ Waiting for GPS fix to confirm threat...")
        elif result == "threat_triggered":
            print("📸 Threat confirmed — triggering camera!")

    except Exception as e:
        print(f"⚠️ Error processing message: {e}")


# Setup secure client
client = mqtt.Client()
client.username_pw_set(USERNAME, PASSWORD)
client.tls_set()  # Enable TLS

client.on_connect = on_connect
client.on_message = on_message

# Connect to HiveMQ Cloud
try:
    client.connect(BROKER, PORT, 60)
    client.loop_forever()
except Exception as e:
    print(f"❌ Failed to connect to MQTT broker: {e}")

