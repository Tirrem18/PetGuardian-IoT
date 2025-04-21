import time
import json
import os
import random
import paho.mqtt.client as mqtt
from azure.iot.device import IoTHubDeviceClient, Message

# Configuration via environment variables
USE_REAL_SENSOR = os.getenv("SOUND", "true").strip().lower() == "true"
INTERACTIVE_MODE = os.getenv("SOUND_MODE", "").strip().lower() == "interactive"

try:
    if USE_REAL_SENSOR:
        import RPi.GPIO as GPIO
        REAL_SENSOR = True
        print("[INIT] Real sensor mode activated.")
    else:
        raise ImportError("Virtual mode forced explicitly by environment variable")
except ImportError as e:
    import keyboard
    REAL_SENSOR = False
    print(f"[INIT] Virtual sensor mode activated. Reason: {e}")


# MQTT Configuration
BROKER = "a5c9d1ea0e224376ad6285eb8aa83d55.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "username"
PASSWORD = "Password1"
TOPIC = "petguardian/iot"

# Azure IoT Hub Configuration
AZURE_CONNECTION_STRING = "HostName=IoTPawTrack.azure-devices.net;DeviceId=collar01;SharedAccessKey=ShzFs2jgI06rAjksNrEst8Byb8x2ljbHrBGYT+raQ1E="

# GPIO Configuration
SOUND_SENSOR_PIN = 17
mqtt_client = None



# Log sound event to local JSON file
def log_event(event, timestamp):
    log_entry = {"timestamp": timestamp, "event": event}

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(base_dir, "data", "logs")
    log_path = os.path.join(log_dir, "sound_log.json")
    os.makedirs(log_dir, exist_ok=True)

    logs = []
    if os.path.exists(log_path) and os.path.getsize(log_path) > 0:
        try:
            with open(log_path, "r") as f:
                logs = json.load(f)
        except Exception:
            logs = []

    logs.append(log_entry)

    with open(log_path, "w") as f:
        json.dump(logs, f, indent=4)

    print(f"[LOG] Recorded event: {log_entry}")

# Send event to Azure IoT Hub
def send_to_azure(event, timestamp):
    payload = json.dumps({"sensor": "acoustic", "event": event, "timestamp": timestamp})

    for attempt in range(3):
        try:
            client = IoTHubDeviceClient.create_from_connection_string(AZURE_CONNECTION_STRING)
            client.send_message(Message(payload))
            client.disconnect()
            print("[AZURE] Event sent.")
            break
        except Exception as e:
            print(f"[AZURE ERROR] Attempt {attempt+1} failed: {e}")
            time.sleep(1)

# Send event to MQTT broker
def send_to_broker(event, timestamp):
    payload = json.dumps({"sensor": "acoustic", "event": event, "timestamp": timestamp})

    for attempt in range(3):
        try:
            mqtt_client.publish(TOPIC, payload)
            print("[MQTT] Event published.")
            break
        except Exception as e:
            print(f"[MQTT ERROR] Attempt {attempt+1} failed: {e}")
            time.sleep(1)

# Unified event handler
def handle_sound_event():
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_event("loud_noise", timestamp)
    send_to_broker("loud_noise", timestamp)
    send_to_azure("loud_noise", timestamp)

# Acoustic sensor logic
def start_acoustic_sensor():
    if REAL_SENSOR:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(SOUND_SENSOR_PIN, GPIO.IN)
        print("[MODE] Real sensor mode active. Listening for sound events.")

        try:
            while True:
                if GPIO.input(SOUND_SENSOR_PIN) == GPIO.HIGH:
                    print("[EVENT] Real sound detected.")
                    handle_sound_event()
                    time.sleep(0.5)
        except KeyboardInterrupt:
            GPIO.cleanup()
            print("[EXIT] Real sensor listening stopped.")

    elif INTERACTIVE_MODE:
        print("[MODE] Interactive keyboard mode: Press 'S' to trigger event, 'X' to exit.")
        try:
            while True:
                event = keyboard.read_event()
                if event.event_type == keyboard.KEY_DOWN:
                    if event.name.lower() == 's':
                        print("[INPUT] Manually triggered sound event.")
                        handle_sound_event()
                    elif event.name.lower() == 'x':
                        print("[EXIT] Exiting interactive mode.")
                        break
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("[EXIT] Interactive mode stopped.")

    else:
        print("[MODE] Virtual simulation mode. Auto-generating sound events.")
        time.sleep(4)
        try:
            while True:
                for _ in range(3):
                    delay = random.uniform(1, 3)
                    time.sleep(delay)
                    print("[SIMULATION] Generated simulated sound event.")
                    handle_sound_event()
                cooldown = random.uniform(10, 15)
                time.sleep(cooldown)
        except KeyboardInterrupt:
            print("[EXIT] Simulation stopped.")

    if INTERACTIVE_MODE:
        if REAL_SENSOR:
            print("[MODE] Interactive mode: Press ENTER to simulate sound event.")
            while True:
                input("[INPUT] Press ENTER to simulate:")
                handle_sound_event()
        else:
            print("[MODE] Interactive keyboard mode: Press 'S' to simulate sound, 'X' to exit.")
            while True:
                event = keyboard.read_event()
                if event.event_type == keyboard.KEY_DOWN:
                    if event.name.lower() == 's':
                        print("[INPUT] Keyboard-triggered event.")
                        handle_sound_event()
                    elif event.name.lower() == 'x':
                        print("[EXIT] Exiting interactive mode.")
                        break
                time.sleep(0.1)

    elif REAL_SENSOR:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(SOUND_SENSOR_PIN, GPIO.IN)
        print("[MODE] Listening for real sensor events.")

        try:
            while True:
                if GPIO.input(SOUND_SENSOR_PIN) == GPIO.HIGH:
                    print("[EVENT] Detected sound event.")
                    handle_sound_event()
                    time.sleep(0.5)
        except KeyboardInterrupt:
            GPIO.cleanup()
            print("[EXIT] Sensor listening stopped.")

    else:
        print("[MODE] Virtual mode: Auto-generating sound events.")
        try:
            while True:
                for _ in range(3):
                    time.sleep(random.uniform(1, 3))
                    print("[SIMULATION] Generated sound event.")
                    handle_sound_event()
                    time.sleep(0.5)
                time.sleep(random.uniform(10, 15))
        except KeyboardInterrupt:
            print("[EXIT] Simulation stopped.")

# MQTT connection with retries
def start_acoustic_listener():
    global mqtt_client
    mqtt_client = mqtt.Client(client_id="acoustic_sensor")
    mqtt_client.username_pw_set(USERNAME, PASSWORD)
    mqtt_client.tls_set()

    for attempt in range(50):
        try:
            mqtt_client.connect(BROKER, PORT, 60)
            mqtt_client.loop_start()
            print("[MQTT] Connected successfully.")
            return
        except Exception as e:
            print(f"[MQTT ERROR] Attempt {attempt+1} failed: {e}")
            time.sleep(0.2)

    print("[MQTT ERROR] All connection attempts failed. Exiting.")

# Main execution
if __name__ == "__main__":
    start_acoustic_listener()
    start_acoustic_sensor()