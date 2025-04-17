import paho.mqtt.client as mqtt
import json
import time

client = mqtt.Client()
client.connect("broker.hivemq.com", 1883)

payload = json.dumps({
    "sensor": "acoustic",
    "event": "test_message_from_script",
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
})

print(f"Sending to: petguardian/iot")
client.publish("petguardian/iot", payload)
client.disconnect()

print("✅ Test MQTT message sent.")
