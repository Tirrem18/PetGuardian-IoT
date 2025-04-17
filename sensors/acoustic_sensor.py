import time
import json
import os
from azure.iot.device import IoTHubDeviceClient, Message

# Try to import Raspberry Pi GPIO library; if unavailable, use virtual mode
try:
    import RPi.GPIO as GPIO
    REAL_SENSOR = True  # True if running on a Raspberry Pi with real GPIO
except ImportError:
    import keyboard  # Used for virtual sound detection
    REAL_SENSOR = False

# GPIO Pin for the acoustic sound sensor
SOUND_SENSOR_PIN = 17

# Configure GPIO pin if using real sensor
if REAL_SENSOR:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SOUND_SENSOR_PIN, GPIO.IN)

# MQTT broker and topic configuration
import paho.mqtt.client as mqtt
BROKER = "broker.hivemq.com"
TOPIC = "petguardian/iot"

def send_data_to_cloud(event):
    """
    Send detected sound event to an MQTT broker.
    """
    client = mqtt.Client()
    client.connect(BROKER)

    payload = json.dumps({
        "sensor": "acoustic",
        "event": event,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })

    client.publish(TOPIC, payload)
    client.disconnect()
    print(f"Sent event to MQTT broker: {payload}")

def log_sound_event(event):
    """Logs detected sound events into a JSON file inside the /data/logs/ folder."""
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "event": event
    }

    # Dynamically find the base project root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(base_dir, "data", "logs")
    log_path = os.path.join(log_dir, "sound_log.json")

    os.makedirs(log_dir, exist_ok=True)

    logs = []
    if os.path.exists(log_path) and os.path.getsize(log_path) > 0:
        try:
            with open(log_path, "r") as log_file:
                logs = json.load(log_file)
            if not isinstance(logs, list):
                logs = []
        except Exception:
            logs = []

    logs.append(log_entry)

    with open(log_path, "w") as log_file:
        json.dump(logs, log_file, indent=4)

    print(f"Logged: {log_entry}")


def detect_sound():
    """
    Detect sound using either a real acoustic sensor or simulated key inputs.
    """
    if REAL_SENSOR:
        print("Listening for sound events via GPIO...")
        while True:
            sound_detected = GPIO.input(SOUND_SENSOR_PIN)
            if sound_detected == GPIO.HIGH:
                print("Sound detected (real sensor)")
                log_sound_event("real_sound")
                send_data_to_cloud("real_sound")
                send_data_to_azure("real_sound")
                time.sleep(0.3)
                return "real_sound"
            time.sleep(0.1)
    else:
        print("Simulated sound detection (keyboard input)")
        print("Press 'B' for Bark, 'C' for Car Noise, 'X' to Exit.")
        while True:
            event = keyboard.read_event()
            if event.event_type == keyboard.KEY_DOWN:
                if event.name == 'b':
                    print("Bark detected (simulated)")
                    log_sound_event("bark")
                    send_data_to_cloud("bark")
                    send_data_to_azure("bark")
                    time.sleep(0.3)
                    return "bark"
                elif event.name == 'c':
                    print("Car noise detected (simulated)")
                    log_sound_event("car_noise")
                    send_data_to_cloud("car_noise")
                    send_data_to_azure("car_noise")
                    time.sleep(0.3)
                    return "car_noise"
                elif event.name == 'x':
                    print("Exiting virtual sound detection...")
                    break
            time.sleep(0.1)

# Azure IoT Hub device connection string
CONNECTION_STRING = "HostName=IoTPawTrack.azure-devices.net;DeviceId=collar01;SharedAccessKey=ShzFs2jgI06rAjksNrEst8Byb8x2ljbHrBGYT+raQ1E="

def send_data_to_azure(event):
    """
    Send sound event to Azure IoT Hub using device connection string.
    """
    try:
        client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
        payload = json.dumps({
            "sensor": "acoustic",
            "event": event,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        message = Message(payload)
        client.send_message(message)
        print(f"Sent event to Azure IoT Hub: {payload}")
        client.disconnect()
    except Exception as e:
        print(f"Failed to send event to Azure IoT Hub: {e}")

# Run the sound detection system
if __name__ == "__main__":
    try:
        detect_sound()
    except KeyboardInterrupt:
        print("Stopping sound detection...")
        if REAL_SENSOR:
            GPIO.cleanup()
