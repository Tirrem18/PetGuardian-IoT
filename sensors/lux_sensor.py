import os
import sys
import time
import json
import random
import threading

# Ensure root path is included for clean imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import SensorUtils for both CLI and module usage
try:
    from sensors.utils.sensor_utils import SensorUtils
except ModuleNotFoundError:
    from utils.sensor_utils import SensorUtils

# --- Sensor Mode Detection ---
INTERACTIVE_MODE = __name__ == "__main__"  # True if running manually
USE_REAL_SENSOR = os.getenv("LUX", "false").strip().lower() == "true"  # Read real/virtual mode from .env

# --- Initialize Sensor Utility ---
utils = SensorUtils(
    sensor_name="lux",
    topic_publish="petguardian/lux",
    topic_trigger="petguardian/trigger/lux"
)

# --- Try to connect to real BH1750 sensor ---
try:
    if USE_REAL_SENSOR:
        import smbus  # Required for I2C communication
        from bh1750 import BH1750  # Custom driver for BH1750 lux sensor

        bh1750 = BH1750(1)  # Initialize BH1750 on I2C bus 1
        REAL_SENSOR = True
        print("[INIT] Real BH1750 lux sensor enabled.")
    else:
        raise ImportError("Virtual mode forced.")
except ImportError as e:
    REAL_SENSOR = False
    print(f"[INIT] Virtual lux sensor mode. Reason: {e}")

# --- Get Lux Value ---
# Returns real sensor reading or simulated value
def get_lux_reading():
    if REAL_SENSOR:
        try:
            # Read raw lux from BH1750 sensor
            raw = bh1750.luminance(BH1750.ONCE_HIRES_1)
            # Scale raw value to approximate 0–500 range
            scaled = min(max(int(raw / 655.35 * 500), 0), 500)
            return scaled
        except Exception as e:
            print(f"[ERROR] BH1750 reading failed: {e}")
            return random.randint(0, 500)

    elif INTERACTIVE_MODE:
        # Manual input during developer testing
        val = input("Enter lux level (0–500): ").strip()
        try:
            lux = int(val)
            if 0 <= lux <= 500:
                return lux
        except:
            pass
        print("[ERROR] Invalid input. Defaulting to 50 lux.")
        return 50

    else:
        # Virtual auto-simulation mode
        return random.randint(0, 500)

# --- Handle Lux Event ---
# Logs and sends lux data to cloud services
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
# Listens for MQTT triggers to send lux data
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

# --- Interactive Developer Mode ---
# Manual testing mode for developers
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

# --- Thread entrypoint for Guardian System ---
# Starts lux sensor listening in background thread
def start_lux_thread():
    thread = threading.Thread(target=start_lux_listener, name="LuxSensorThread", daemon=True)
    thread.start()

# --- Main Developer Entrypoint ---
# If running directly, launch MQTT connection and manual mode
if __name__ == "__main__":
    utils.mqtt_client.connect(utils.broker, utils.port, 60)
    utils.mqtt_client.loop_start()
    print("[MQTT] Lux sensor connected and ready.")

    run_interactive_mode()
