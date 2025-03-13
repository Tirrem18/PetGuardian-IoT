import time
import json
import os

# Try to import Raspberry Pi GPIO library; if unavailable, use virtual mode
try:
    import RPi.GPIO as GPIO
    REAL_SENSOR = True  # Flag to indicate real sensor usage
except ImportError:
    print("RPi.GPIO not found! Running in virtual mode...")
    import keyboard  # Virtual mode: Simulate sound detection with keyboard
    REAL_SENSOR = False

# GPIO Pin for the sound sensor (Only used if running on a real Pi)
SOUND_SENSOR_PIN = 17

if REAL_SENSOR:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SOUND_SENSOR_PIN, GPIO.IN)

import paho.mqtt.client as mqtt

BROKER = "test.mosquitto.org"  # Free MQTT broker
TOPIC = "petguardian/iot"

def send_data_to_cloud(event):
    """Send detected sound event to an MQTT broker."""
    client = mqtt.Client()
    client.connect(BROKER)
    payload = json.dumps({
        "sensor": "acoustic", 
        "event": event, 
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    client.publish(TOPIC, payload)
    client.disconnect()
    print(f"Sent event to MQTT Broker: {payload}")

def log_sound_event(event):
    """Logs detected sound events into a JSON file with multiple entries."""
    log_entry = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "event": event}

    if os.path.exists("sound_log.json") and os.path.getsize("sound_log.json") > 0:
        try:
            with open("sound_log.json", "r") as log_file:
                logs = json.load(log_file)
            if not isinstance(logs, list):
                logs = []  
        except (json.JSONDecodeError, FileNotFoundError):
            logs = []  
    else:
        logs = []  

    logs.append(log_entry)

    with open("sound_log.json", "w") as log_file:
        json.dump(logs, log_file, indent=4)

    print(f"Logged: {event}")

def detect_sound():
    """Detects sound using either a real acoustic sensor or simulated key presses."""
    if REAL_SENSOR:
        print("Listening for real sound events on Raspberry Pi...")
        while True:
            sound_detected = GPIO.input(SOUND_SENSOR_PIN)
            if sound_detected == GPIO.HIGH:
                print("Real Sound Detected!")
                log_sound_event("real_sound")
                send_data_to_cloud("real_sound")
                time.sleep(0.3)  
                return "real_sound"
            time.sleep(0.1)
    else:
        print("Virtual Sound Detection Active...")
        print("Press 'B' for Bark, 'C' for Car Noise, 'X' to Exit.")
        while True:
            event = keyboard.read_event()  
            if event.event_type == keyboard.KEY_DOWN:  
                if event.name == 'b':  
                    print("Simulated Bark Detected!")
                    log_sound_event("bark")
                    send_data_to_cloud("bark") 
                    time.sleep(0.3)  
                    return "bark"
                elif event.name == 'c':
                    print("Simulated Car Noise Detected!")
                    log_sound_event("car_noise")
                    send_data_to_cloud("car_noise")  
                    time.sleep(0.3)
                    return "car_noise"
                elif event.name == 'x':
                    print("Exiting virtual sound detection.")
                    break
            time.sleep(0.1)

if __name__ == "__main__":
    try:
        detect_sound()
    except KeyboardInterrupt:
        print("\nStopping sound detection...")
        if REAL_SENSOR:
            GPIO.cleanup()
