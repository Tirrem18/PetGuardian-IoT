import paho.mqtt.client as mqtt
import json
import time

# HiveMQ Cloud credentials
USERNAME = "username"
PASSWORD = "Password1"

# Broker and topic setup
BROKER = "a5c9d1ea0e224376ad6285eb8aa83d55.s1.eu.hivemq.cloud"
PORT = 8883
TOPIC = "petguardian/iot"

# Set up secure MQTT client
client = mqtt.Client()
client.username_pw_set(USERNAME, PASSWORD)
client.tls_set()  # Enable TLS encryption

# Connect to broker
client.connect(BROKER, PORT)

# Prepare payload
payload = json.dumps({
    "sensor": "acoustic",
    "event": "test_message_from_script",
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
})

# Publish to topic
print(f"Sending to: {TOPIC}")
client.publish(TOPIC, payload)

# Give time for transmission
time.sleep(2)
client.disconnect()
print("✅ Test MQTT message sent.")
