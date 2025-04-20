import paho.mqtt.client as mqtt
import json

BROKER = "broker.hivemq.com"
PORT = 1883

TOPICS = [("petguardian/iot", 0),
          ("petguardian/gps", 0),
          ("petguardian/light", 0)]

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to MQTT broker.")
        for topic, qos in TOPICS:
            client.subscribe((topic, qos))
            print(f"📡 Subscribed to topic: {topic}")
    else:
        print(f"❌ Connection failed with code {rc}")

def on_message(client, userdata, msg):
    print(f"\n📥 Raw MQTT message received from topic: {msg.topic}")
    print(f"Payload (raw): {msg.payload.decode(errors='ignore')}")
    try:
        payload = json.loads(msg.payload.decode())
        print(f"📄 Parsed Message: {json.dumps(payload, indent=2)}")
    except Exception as e:
        print(f"⚠️ Error parsing message: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(BROKER, PORT, 60)
    client.loop_forever()
except Exception as e:
    print(f"❌ Failed to connect to MQTT broker: {e}")
