import os
import sys
import time
import json
import threading

# Ensure root path is accessible
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try both import styles
try:
    from sensors.utils.sensor_utils import SensorUtils
except ModuleNotFoundError:
    from utils.sensor_utils import SensorUtils

# --- Mode Detection ---
INTERACTIVE_MODE = __name__ == "__main__"
USE_REAL_BULB = os.getenv("BULB", "false").strip().lower() == "true"

# --- Sensor Utilities ---
utils = SensorUtils(
    sensor_name="bulb",
    topic_publish="petguardian/bulb",
    topic_trigger="petguardian/trigger/bulb"
)

# --- Bulb Simulation Logic ---
def turn_on_bulb():
    print("[BULB] 💡 Bulb turned ON")
    log_bulb_event("on")

def turn_off_bulb():
    print("[BULB] ❌ Bulb turned OFF")
    log_bulb_event("off")

def log_bulb_event(state):
    timestamp = utils.get_timestamp()
    data = {
        "sensor": "bulb",
        "timestamp": timestamp,
        "state": state
    }
    utils.log_locally("bulb_log.json", data)
    utils.send_to_mqtt(data)
    utils.send_to_azure(data)
    utils.send_to_cosmos(data)


# --- MQTT Trigger Listener ---
def start_bulb_listener():
    def on_bulb_trigger(client, userdata, msg):
        print(f"[MQTT] Trigger received on {msg.topic}")
        try:
            payload = json.loads(msg.payload.decode())
            cmd = payload.get("command", "").lower()
            if cmd == "turn_on":
                turn_on_bulb()
            elif cmd == "turn_off":
                turn_off_bulb()
        except Exception as e:
            print(f"[ERROR] Failed to handle bulb trigger: {e}")

    utils.start_mqtt_listener(on_bulb_trigger)


# --- Threaded entry for Guardian ---
def start_bulb_thread():
    thread = threading.Thread(target=start_bulb_listener, name="BulbListenerThread", daemon=True)
    thread.start()


# --- Developer Test Mode ---
if __name__ == "__main__":
    utils.mqtt_client.connect(utils.broker, utils.port, 60)
    utils.mqtt_client.loop_start()
    print("[MQTT] Bulb connected and waiting for trigger.")

    if INTERACTIVE_MODE:
        print("[INTERACTIVE] Type 'on' to turn bulb ON, 'off' to turn OFF, or 'x' to exit.")
        try:
            while True:
                cmd = input(">>> ").strip().lower()
                if cmd == "on":
                    turn_on_bulb()
                elif cmd == "off":
                    turn_off_bulb()
                elif cmd == "x":
                    print("[EXIT] Exiting bulb interactive mode.")
                    break
                else:
                    print("[INFO] Use 'on', 'off', or 'x'.")
        except KeyboardInterrupt:
            print("\n[EXIT] Bulb interactive loop interrupted.")
