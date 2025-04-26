import os
import sys
import time
import json
import random
import threading

# Ensure root path is in sys.path for clean imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try both import styles to support CLI and module execution
try:
    from sensors.utils.sensor_utils import SensorUtils
except ModuleNotFoundError:
    from utils.sensor_utils import SensorUtils

# --- Sensor Mode Detection ---
INTERACTIVE_MODE = __name__ == "__main__"
USE_REAL_SENSOR = os.getenv("LUX", "false").strip().lower() == "true"

# --- Sensor utility class ---
utils = SensorUtils(
    sensor_name="lux",
    topic_publish="petguardian/lux",
    topic_trigger="petguardian/trigger/lux"
)

# --- Try to connect to BH1750 hardware sensor ---
try:
    if USE_REAL_SENSOR:
        import smbus
        from bh1750 import BH1750
        bh1750 = BH1750(1)
        REAL_SENSOR = True
        print("[INIT] Real BH1750 lux sensor enabled.")
    else:
        raise ImportError("Virtual mode forced")
except ImportError as e:
    REAL_SENSOR = False
    print(f"[INIT] Virtual lux sensor mode. Reason: {e}")


# --- Get Lux Value ---
def get_lux_reading():
    if REAL_SENSOR:
        try:
            raw = bh1750.luminance(BH1750.ONCE_HIRES_1)
            scaled = min(max(int(raw / 655.35 * 100), 0), 100)
            return scaled
        except Exception as e:
            print(f"[ERROR] BH1750 failed: {e}")
            return random.randint(0, 500)

    elif INTERACTIVE_MODE:
        val = input("Enter lux level (0–500): ").strip()
        try:
            lux = int(val)
            if 0 <= lux <= 500:
                return lux
        except:
            pass
        print("[ERROR] Invalid input. Using 50.")
        return 50

    else:
        return random.randint(0, 100)


# --- Handle Lux Event ---
def handle_lux_event():
    timestamp = utils.get_timestamp()
    lux = get_lux_reading()

    data = {
        "sensor": "lux",
        "timestamp": timestamp,
        "lux": lux
    }

    utils.log_locally("lux_log.json", data)
    utils.send_to_mqtt(data)
    utils.send_to_azure(data)
    utils.send_to_cosmos(data)


# --- MQTT Trigger Listener ---
def start_lux_listener():
    def on_lux_trigger(client, userdata, msg):
        print(f"[MQTT] Trigger received on {msg.topic}")
        try:
            payload = json.loads(msg.payload.decode())
            if payload.get("command") == "get_lux":
                print("[TRIGGER] Lux trigger accepted.")
                handle_lux_event()
        except Exception as e:
            print(f"[ERROR] Trigger processing failed: {e}")

    utils.start_mqtt_listener(on_lux_trigger)


# --- Interactive Mode ---
def run_interactive_mode():
    print("[INTERACTIVE] Type 'L' to simulate lux reading, or 'X' to exit.")
    try:
        while True:
            cmd = input(">>> ").strip().lower()
            if cmd == "l":
                print("[INPUT] Manual lux event triggered.")
                handle_lux_event()
            elif cmd == "x":
                print("[EXIT] Interactive mode ended.")
                break
            else:
                print("[INFO] Use 'L' to trigger or 'X' to quit.")
    except KeyboardInterrupt:
        print("\n[EXIT] Interactive loop interrupted.")


# --- Thread entrypoint for guardian.py ---
def start_lux_thread():
    thread = threading.Thread(target=start_lux_listener, name="LuxSensorThread", daemon=True)
    thread.start()


# --- Main entrypoint ---
if __name__ == "__main__":
    utils.mqtt_client.connect(utils.broker, utils.port, 60)
    utils.mqtt_client.loop_start()
    print("[MQTT] Lux sensor connected and ready.")

    run_interactive_mode()
