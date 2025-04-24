import os
import time
import json
import logging
import paho.mqtt.client as mqtt
from datetime import datetime

logging.getLogger("azure").setLevel(logging.WARNING)

# --- Configuration ---
USE_REAL_BULB = os.getenv("BULB", "false").strip().lower() == "true"
INTERACTIVE_MODE = os.getenv("BULB_MODE", "").strip().lower() == "interactive"

# --- MQTT Configuration ---
BROKER = "a5c9d1ea0e224376ad6285eb8aa83d55.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "username"
PASSWORD = "Password1"
TOPIC_TRIGGER = "petguardian/trigger/bulb"

mqtt_client = mqtt.Client(client_id="led_bulb")
mqtt_client.username_pw_set(USERNAME, PASSWORD)
mqtt_client.tls_set()

# --- Bulb Actions ---
def turn_on_bulb():
    status = "[BULB] 💡 Bulb turned ON"
    print(status)
    log_bulb_event("on")

def turn_off_bulb():
    status = "[BULB] ❌ Bulb turned OFF"
    print(status)
    log_bulb_event("off")

def log_bulb_event(state):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = {"timestamp": timestamp, "state": state}

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(base_dir, "data", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "bulb_log.json")

    logs = []
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            try:
                logs = json.load(f)
            except:
                logs = []

    logs.append(entry)
    with open(log_path, "w") as f:
        json.dump(logs, f, indent=4)

# --- MQTT Callbacks ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[MQTT] Bulb connected to broker.")
        client.subscribe(TOPIC_TRIGGER)
        print(f"[MQTT] Subscribed to: {TOPIC_TRIGGER}")
    else:
        print("[MQTT ERROR] Connection failed with code", rc)

def on_message(client, userdata, msg):
    print(f"[MQTT] Bulb trigger received on topic {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode())
        command = payload.get("command", "")
        if command == "turn_on":
            turn_on_bulb()
        elif command == "turn_off":
            turn_off_bulb()
    except Exception as e:
        print(f"[ERROR] Failed to process bulb trigger: {e}")

# --- Listener ---
def start_bulb_listener():
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    for attempt in range(10):
        try:
            mqtt_client.connect(BROKER, PORT, 60)
            mqtt_client.loop_start()
            print("[MQTT] Bulb listener started.")
            return
        except Exception as e:
            print(f"[MQTT ERROR] Attempt {attempt+1}: {e}")
            time.sleep(1)

    print("[MQTT ERROR] Could not connect to MQTT broker.")

# --- Entry Point ---
if __name__ == "__main__":
    start_bulb_listener()

    if INTERACTIVE_MODE:
        print("[INTERACTIVE] Type 'ON' to turn on bulb, 'OFF' to turn off, or 'X' to exit.")
        try:
            while True:
                user_input = input("[INPUT] >> ").strip().lower()
                if user_input == 'on':
                    turn_on_bulb()
                elif user_input == 'off':
                    turn_off_bulb()
                elif user_input == 'x':
                    print("[EXIT] Exiting bulb control.")
                    break
        except KeyboardInterrupt:
            print("[EXIT] Bulb interactive loop interrupted.")