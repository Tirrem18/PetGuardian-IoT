import os
import sys
import time
import random
import threading  # ✅ Added

# Ensure root path is in sys.path for clean imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try both import styles to support CLI and module execution
try:
    from sensors.utils.sensor_utils import SensorUtils
except ModuleNotFoundError:
    from utils.sensor_utils import SensorUtils

# --- Sensor Mode Detection ---
INTERACTIVE_MODE = __name__ == "__main__"
REAL_SENSOR_AVAILABLE = False

# Attempt to import GPIO if available
try:
    import RPi.GPIO as GPIO
    REAL_SENSOR_AVAILABLE = True
except ImportError:
    print("[INIT] RPi.GPIO not found. Real sensor support unavailable.")

# Default real mode is based on .env if used in collar mode
USE_REAL_SENSOR = os.getenv("SOUND", "false").strip().lower() == "true"

# --- Shared Utility Class ---
utils = SensorUtils(
    sensor_name="acoustic",
    topic_publish="petguardian/iot"
)

# --- Event Logic ---
def handle_sound_event():
    timestamp = utils.get_timestamp()
    data = {
        "sensor": "acoustic",
        "event": "loud_noise",
        "timestamp": timestamp
    }
    utils.log_locally("sound_log.json", data)
    utils.send_to_mqtt(data)
    utils.send_to_azure(data)
    utils.send_to_cosmos(data)

# --- Real Sensor GPIO Mode ---
def run_real_mode():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(17, GPIO.IN)
    print("[MODE] Listening for real acoustic signals on GPIO 17...")
    try:
        while True:
            if GPIO.input(17) == GPIO.HIGH:
                print("[EVENT] Real sound detected.")
                handle_sound_event()
                time.sleep(0.5)
    except KeyboardInterrupt:
        GPIO.cleanup()
        print("[EXIT] Real mode interrupted.")

# --- Interactive CLI Testing Mode ---
def run_interactive_mode():
    print("[INTERACTIVE] Type 'S' to simulate sound, or 'X' to exit.")
    try:
        while True:
            user_input = input(">>> ").strip().lower()
            if user_input == 's':
                print("[INPUT] Manual sound event triggered.")
                handle_sound_event()
            elif user_input == 'x':
                print("[EXIT] Interactive mode ended.")
                break
            else:
                print("[INFO] Unknown input. Use 'S' or 'X'.")
    except KeyboardInterrupt:
        print("\n[EXIT] Interactive mode interrupted.")

# --- Virtual Auto Simulation Mode ---
def run_virtual_mode():
    print("[SIMULATION] Generating simulated sound events...\n")
    try:
        while True:
            for _ in range(3):
                time.sleep(random.uniform(1, 3))
                print("[SIM] Simulated sound spike.")
                handle_sound_event()
            print("[SIM] Cooling down for 150 seconds.")
            time.sleep(150)
    except KeyboardInterrupt:
        print("[EXIT] Virtual simulation interrupted.")

# --- Prompt User for Real vs Virtual (if possible) ---
def prompt_sensor_mode():
    while True:
        choice = input("[SELECT MODE] Use real acoustic sensor? (Y/n): ").strip().lower()
        if choice in ("y", "yes"):
            return True
        elif choice in ("n", "no"):
            return False
        print("[INFO] Please enter 'Y' or 'N'.")

    
def start_acoustic_listener():
    """Start acoustic sensor listener as a daemon thread (real or virtual)."""
    def _acoustic_run_thread():
        if USE_REAL_SENSOR and REAL_SENSOR_AVAILABLE:
                run_real_mode()
        else:
                run_virtual_mode()

    thread = threading.Thread(
            target=_acoustic_run_thread,
            name="AcousticSensorThread",
            daemon=True
    )
    thread.start()


# --- Entry Point: Developer Testing ---
if __name__ == "__main__":
    utils.mqtt_client.connect(utils.broker, utils.port, 60)
    utils.mqtt_client.loop_start()
    print("[MQTT] Acoustic sensor connected and publishing.")

    if REAL_SENSOR_AVAILABLE:
        USE_REAL_SENSOR = prompt_sensor_mode()
        if USE_REAL_SENSOR:
            run_real_mode()
        else:
            run_interactive_mode()
    else:
        print("[MODE] Real sensor mode unavailable. Entering virtual test mode.")
        run_interactive_mode()

