import time
import json
import os
import random
import paho.mqtt.client as mqtt
from azure.iot.device import IoTHubDeviceClient, Message

# Try to import Raspberry Pi GPIO library
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    REAL_SENSOR = True
except ImportError:
    print("GPIO module not found! Running in virtual mode...")
    REAL_SENSOR = False

# Azure IoT Hub connection string
CONNECTION_STRING = "HostName=IoTPawTrack.azure-devices.net;DeviceId=collar01;SharedAccessKey=ShzFs2jgI06rAjksNrEst8Byb8x2ljbHrBGYT+raQ1E="

# Configuration
SENSOR_PIN = 17
BROKER = "broker.hivemq.com"
TOPIC = "petguardian/light"

if REAL_SENSOR:
    GPIO.setup(SENSOR_PIN, GPIO.IN)

def send_data_to_cloud(light_data):
    client = mqtt.Client()
    try:
        client.connect(BROKER, port=1883, keepalive=60)
        payload = json.dumps({
            "sensor": "led_light_sensor" if REAL_SENSOR else "simulated_led_light",
            "lux": light_data["lux"],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        client.publish(TOPIC, payload)
        print(f"✅ Sent to MQTT: {payload}")
    except Exception as e:
        print(f"❌ MQTT error: {e}")
    finally:
        client.disconnect()

def send_data_to_azure(light_data):
    try:
        client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
        payload = json.dumps({
            "deviceId": "collar01",
            "sensor": "led_light_sensor" if REAL_SENSOR else "simulated_led_light",
            "lux": light_data["lux"],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        print("📤 Sending to Azure:", payload)
        message = Message(payload)
        client.send_message(message)
        print("✅ Sent to Azure IoT Hub")
        client.disconnect()
    except Exception as e:
        print(f"❌ Azure send failed: {e}")

def log_light_data(light_data):
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "lux": light_data["lux"]
    }

    try:
        if os.path.exists("led_light_log.json"):
            with open("light_log.json", "r") as log_file:
                logs = json.load(log_file)
            if not isinstance(logs, list):
                logs = []
        else:
            logs = []
    except (json.JSONDecodeError, FileNotFoundError):
        logs = []

    logs.append(log_entry)
    with open("light_log.json", "w") as log_file:
        json.dump(logs, log_file, indent=4)

    print(f"📝 Logged: {log_entry}")

def get_light_level():
    if REAL_SENSOR:
        if GPIO.input(SENSOR_PIN):
            lux = random.uniform(300, 1000)
        else:
            lux = random.uniform(0, 299)
    else:
        lux = random.uniform(0, 1000)
    return {"lux": lux}

def light_tracking():
    print("🔆 Light Sensor (Physical/Virtual) Active...")
    while True:
        light_data = get_light_level()
        log_light_data(light_data)
        send_data_to_cloud(light_data)
        send_data_to_azure(light_data)  
        time.sleep(5)

if __name__ == "__main__":
    try:
        light_tracking()
    except KeyboardInterrupt:
        if REAL_SENSOR:
            GPIO.cleanup()
        print("\n🛑 Stopping light sensor tracking...")
