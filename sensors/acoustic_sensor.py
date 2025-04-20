import time
import json
import os

# MQTT (HiveMQ Cloud) settings
import paho.mqtt.client as mqtt
BROKER = "a5c9d1ea0e224376ad6285eb8aa83d55.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "username"
PASSWORD = "Password1"
TOPIC = "petguardian/iot"

# Azure IoT Hub config
from azure.iot.device import IoTHubDeviceClient, Message
AZURE_CONNECTION_STRING = "HostName=IoTPawTrack.azure-devices.net;DeviceId=collar01;SharedAccessKey=ShzFs2jgI06rAjksNrEst8Byb8x2ljbHrBGYT+raQ1E="

# Try GPIO (Raspberry Pi), fallback to keyboard simulation
try:
    import RPi.GPIO as GPIO
    REAL_SENSOR = True
except ImportError:
    import keyboard
    print("⚠️ Acoustic module not found. Virtual mode enabled.")
    REAL_SENSOR = False

SOUND_SENSOR_PIN = 17

# Setup MQTT client
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(USERNAME, PASSWORD)
mqtt_client.tls_set()
mqtt_client.connect(BROKER, PORT)
mqtt_client.loop_start()


def send_to_broker(event, retries=3, delay=2):
    """
    Publish sound event to MQTT broker with retry logic.
    """
    payload = json.dumps({
        "sensor": "acoustic",
        "event": event,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })

    for attempt in range(1, retries + 1):
        try:
            mqtt_client.publish(TOPIC, payload)
            print(f"📤 Sent to broker (Attempt {attempt}): {payload}")
            return
        except Exception as e:
            print(f"⚠️ MQTT publish failed (Attempt {attempt}): {e}")
            time.sleep(delay)

    print("❌ Failed to send sound event to broker after multiple attempts.")



def send_to_azure(event):
    """
    Send sound event to Azure IoT Hub.
    """
    try:
        client = IoTHubDeviceClient.create_from_connection_string(AZURE_CONNECTION_STRING)
        payload = json.dumps({
            "sensor": "acoustic",
            "event": event,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        client.send_message(Message(payload))
        client.disconnect()
        print(f"☁️ Sent to Azure: {payload}")
    except Exception as e:
        print(f"⚠️ Failed to send to Azure: {e}")


def log_event(event):
    """
    Log event to local JSON file.
    """
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "event": event
    }

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(base_dir, "data", "logs")
    log_path = os.path.join(log_dir, "sound_log.json")
    os.makedirs(log_dir, exist_ok=True)

    logs = []
    if os.path.exists(log_path) and os.path.getsize(log_path) > 0:
        try:
            with open(log_path, "r") as f:
                logs = json.load(f)
            if not isinstance(logs, list):
                logs = []
        except Exception:
            logs = []

    logs.append(log_entry)
    with open(log_path, "w") as f:
        json.dump(logs, f, indent=4)

    print(f"📝 Logged: {log_entry}")


def start_acoustic_sensor():
    """
    Runs acoustic sensor mode: GPIO (real) or simulated keyboard.
    """
    if REAL_SENSOR:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(SOUND_SENSOR_PIN, GPIO.IN)
        print("🎧 Listening with real sound sensor...")

        try:
            while True:
                if GPIO.input(SOUND_SENSOR_PIN) == GPIO.HIGH:
                    print("🔊 Real loud sound detected!")
                    log_event("loud_noise")
                    send_to_broker("loud_noise")
                    send_to_azure("loud_noise")
                    time.sleep(0.5)
        except KeyboardInterrupt:
            GPIO.cleanup()

    else:
        while True:
            print("🎧 Simulated mode — Press 'S' to simulate loud noise, 'X' to exit.")
            event = keyboard.read_event()
            if event.event_type == keyboard.KEY_DOWN:
                if event.name.lower() == 's':
                    print("🔊 Simulated loud noise triggered.")
                    log_event("loud_noise")
                    send_to_broker("loud_noise")
                    send_to_azure("loud_noise")
                    time.sleep(0.5)
                elif event.name.lower() == 'x':
                    print("👋 Exiting simulated sound mode.")
                    break
            time.sleep(0.1)



if __name__ == "__main__":
    start_acoustic_sensor()
