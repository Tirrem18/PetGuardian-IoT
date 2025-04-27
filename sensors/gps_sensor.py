import os
import sys
import time
import random
import json
import threading

# Ensure project root path is included for clean imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try importing SensorUtils for both CLI execution and module usage
try:
    from sensors.utils.sensor_utils import SensorUtils
except ModuleNotFoundError:
    from utils.sensor_utils import SensorUtils

# --- Sensor Mode Detection ---
INTERACTIVE_MODE = __name__ == "__main__"  # True if running script directly
USE_REAL_SENSOR = os.getenv("GPS", "false").strip().lower() == "true"  # Read GPS mode setting from .env

# --- Default fallback simulation coordinates ---
HOME_LOCATION = (54.5742, -1.2345)  # Static coordinates for simulation if no real GPS

# --- Initialize helper class ---
# Create a SensorUtils instance configured for the GPS sensor
utils = SensorUtils(
    sensor_name="gps",
    topic_publish="petguardian/gps",
    topic_trigger="petguardian/trigger/gps"
)

# --- Try importing real GPS hardware library ---
# Attempt to connect to gpsd if using real GPS hardware
try:
    if USE_REAL_SENSOR:
        import gpsd
        gpsd.connect()
        REAL_SENSOR = True
        print("[INIT] Real GPS sensor mode enabled.")
    else:
        raise ImportError("Virtual mode forced")
except ImportError as e:
    REAL_SENSOR = False
    print(f"[INIT] Virtual GPS sensor mode. Reason: {e}")

# --- Core GPS Reading ---
# Obtain a GPS reading either from real sensor, manual input, or simulation
def get_gps_reading():
    if REAL_SENSOR:
        # Attempt to fetch real GPS coordinates
        try:
            packet = gpsd.get_current()
            return {
                "latitude": round(packet.lat, 6),
                "longitude": round(packet.lon, 6)
            }
        except Exception as e:
            print(f"[ERROR] Real GPS failed: {e}")
            return None

    elif INTERACTIVE_MODE:
        # Manually input GPS coordinates during interactive mode
        print("[INTERACTIVE] Manual GPS input mode. Press Enter or X to cancel.")
        try:
            lat = input("Latitude: ").strip()
            if lat.lower() in ["", "x"]:
                return None
            lon = input("Longitude: ").strip()
            if lon.lower() in ["", "x"]:
                return None
            return {
                "latitude": float(lat),
                "longitude": float(lon)
            }
        except ValueError:
            print("[INPUT ERROR] Invalid coordinates entered.")
            return None

    else:
        # Simulate slightly random GPS locations around HOME_LOCATION
        lat = HOME_LOCATION[0] + random.uniform(-0.001, 0.001)
        lon = HOME_LOCATION[1] + random.uniform(-0.001, 0.001)
        return {
            "latitude": round(lat, 6),
            "longitude": round(lon, 6)
        }

# --- Handle a GPS Event ---
# Process a GPS event: log it, send it to MQTT, Azure, and Cosmos
def handle_gps_event():
    timestamp = utils.get_timestamp()
    coords = get_gps_reading()

    if not coords:
        # If no location could be retrieved, use fallback
        print("[WARNING] No location detected. Using UNKNOWN fallback.")
        coords = {"latitude": "unknown", "longitude": "unknown"}

    data = {
        "sensor": "gps",
        "timestamp": timestamp,
        **coords
    }

    # Log locally and send data to cloud services
    utils.log_locally("gps_log.json", data)
    utils.send_to_mqtt(data)
    utils.send_to_azure(data)
    utils.send_to_cosmos(data)

# --- Passive MQTT Listener ---
# Listens for trigger messages to capture a GPS reading
def start_gps_listener():
    def on_trigger(client, userdata, msg):
        print(f"[MQTT] Trigger received on {msg.topic}")
        try:
            payload = json.loads(msg.payload.decode())
            if payload.get("command") == "get_gps":
                print("\n[TRIGGER] GPS request accepted.")
                handle_gps_event()
        except Exception as e:
            print(f"[MQTT ERROR] Could not decode message: {e}")

    # Start listening on the specified trigger topic
    utils.start_mqtt_listener(on_trigger)

# --- Interactive CLI Mode ---
# Developer manual mode to simulate GPS events by command input
def run_interactive_mode():
    print("[INTERACTIVE] Type 'G' to simulate GPS event, or 'X' to exit.")
    try:
        while True:
            cmd = input(">>> ").strip().lower()
            if cmd == "g":
                print("[INPUT] Manual GPS event triggered.")
                handle_gps_event()
            elif cmd == "x":
                print("[EXIT] Interactive mode ended.")
                break
            else:
                print("[INFO] Use 'G' to trigger or 'X' to quit.")
    except KeyboardInterrupt:
        print("\n[EXIT] Interactive mode interrupted.")

# --- Threadable entry for AI controller ---
# Allows GPS sensor to run in a background thread inside live systems
def start_gps_thread():
    thread = threading.Thread(target=start_gps_listener, name="GPSSensorThread", daemon=True)
    thread.start()

# --- Entry Point: Developer Testing ---
# Starts the sensor in manual mode if running as a standalone script
if __name__ == "__main__":
    utils.mqtt_client.connect(utils.broker, utils.port, 60)  # Connect to MQTT
    utils.mqtt_client.loop_start()  # Start MQTT message loop
    print("[MQTT] GPS sensor connected and waiting.")

    # Launch interactive manual mode
    run_interactive_mode()
