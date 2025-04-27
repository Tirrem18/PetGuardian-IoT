import os
import sys
import time
import json
import threading

# Ensure project root path is accessible
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try both import styles for SensorUtils
try:
    from sensors.utils.sensor_utils import SensorUtils
except ModuleNotFoundError:
    from utils.sensor_utils import SensorUtils

# --- Mode Detection ---
INTERACTIVE_MODE = __name__ == "__main__"  # True if running manually
USE_REAL_BULB = os.getenv("BULB", "false").strip().lower() == "true"  # Read bulb mode from .env

# --- Attempt to setup real GPIO control if enabled ---
try:
    if USE_REAL_BULB:
        import RPi.GPIO as GPIO

        BULB_PIN = 27  # GPIO pin used for controlling the bulb relay

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BULB_PIN, GPIO.OUT)
        GPIO.output(BULB_PIN, GPIO.LOW)  # Ensure bulb starts OFF

        REAL_BULB = True
        print("[INIT] Real bulb control via GPIO activated.")
    else:
        raise ImportError("Virtual mode forced or GPIO library unavailable.")
except ImportError as e:
    REAL_BULB = False
    print(f"[INIT] Virtual bulb mode activated. Reason: {e}")

# --- Sensor Utilities ---
# Create SensorUtils instance for bulb
utils = SensorUtils(
    sensor_name="bulb",
    topic_publish="petguardian/bulb",
    topic_trigger="petguardian/trigger/bulb"
)

# --- Bulb State and Timer Logic ---
bulb_timer = None  # Timer to auto turn off bulb after duration
bulb_lock = threading.Lock()  # Thread safety lock

# --- Bulb control functions ---
def turn_on_bulb():
    if REAL_BULB:
        GPIO.output(BULB_PIN, GPIO.HIGH)  # Turn ON real bulb via relay
    print("[BULB] Bulb turned ON")
    log_bulb_event("on")

def turn_off_bulb():
    if REAL_BULB:
        GPIO.output(BULB_PIN, GPIO.LOW)  # Turn OFF real bulb via relay
    print("[BULB] Bulb turned OFF")
    log_bulb_event("off")

# --- Event Logging ---
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

# --- Bulb Timer Management ---
# Restart timer whenever bulb is turned on
def restart_bulb_timer(duration):
    global bulb_timer
    with bulb_lock:
        if bulb_timer is not None:
            bulb_timer.cancel()
        bulb_timer = threading.Timer(duration, auto_turn_off)
        bulb_timer.start()
        print(f"[BULB] Timer set/reset for {duration} seconds.")

# Cancel timer manually when bulb is turned off
def cancel_bulb_timer():
    global bulb_timer
    with bulb_lock:
        if bulb_timer is not None:
            bulb_timer.cancel()
            bulb_timer = None
            print("[BULB] Timer cancelled.")

# Automatically turn off bulb when timer expires
def auto_turn_off():
    with bulb_lock:
        turn_off_bulb()

# --- MQTT Trigger Listener ---
# Listens for MQTT messages to control bulb
def start_bulb_listener():
    def on_bulb_trigger(client, userdata, msg):
        print(f"[MQTT] Trigger received on {msg.topic}")
        try:
            payload = json.loads(msg.payload.decode())
            cmd = payload.get("command", "").lower()
            duration = int(payload.get("duration", 10))  # Default auto-off after 10 seconds

            if cmd == "turn_on":
                turn_on_bulb()
                restart_bulb_timer(duration)
            elif cmd == "turn_off":
                cancel_bulb_timer()
                turn_off_bulb()
        except Exception as e:
            print(f"[ERROR] Failed to handle bulb trigger: {e}")

    utils.start_mqtt_listener(on_bulb_trigger)

# --- Threaded entry for Guardian ---
# Runs the MQTT listener in a background thread
def start_bulb_thread():
    thread = threading.Thread(target=start_bulb_listener, name="BulbListenerThread", daemon=True)
    thread.start()

# --- Developer Test Mode ---
# Manual developer testing mode
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
                    restart_bulb_timer(10)  # Default timer for manual testing
                elif cmd == "off":
                    cancel_bulb_timer()
                    turn_off_bulb()
                elif cmd == "x":
                    print("[EXIT] Exiting bulb interactive mode.")
                    break
                else:
                    print("[INFO] Use 'on', 'off', or 'x'.")
        except KeyboardInterrupt:
            print("\n[EXIT] Bulb interactive loop interrupted.")
        finally:
            if REAL_BULB:
                GPIO.cleanup()  # Always cleanup GPIO pins properly on exit
