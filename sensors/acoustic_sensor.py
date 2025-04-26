import os
import sys
import time
import random
import threading

# Ensure root path for clean imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try import styles
try:
    from sensors.utils.sensor_utils import SensorUtils
except ModuleNotFoundError:
    from utils.sensor_utils import SensorUtils

# --- Mode Detection ---
INTERACTIVE_MODE = __name__ == "__main__"
REAL_SENSOR_AVAILABLE = False

try:
    import RPi.GPIO as GPIO
    REAL_SENSOR_AVAILABLE = True
except ImportError:
    print("[INIT] RPi.GPIO not found. Real sensor support unavailable.")

# Always trust .env for real or virtual
USE_REAL_SENSOR = os.getenv("SOUND", "false").strip().lower() == "true"

# --- Shared Utils ---
utils = SensorUtils(
    sensor_name="acoustic",
    topic_publish="petguardian/acoustic"
)

# --- Event Logic ---
def handle_sound_event():
    print("[ACOUSTIC] Sending sound event to MQTT...")
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
    GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Use PULL-UP
    print("[MODE] Listening for real acoustic signals on GPIO 17 (LOW = sound)...")
    try:
        while True:
            if GPIO.input(17) == GPIO.LOW:  # Sound detected when LOW
                print("[EVENT] Real sound detected.")
                handle_sound_event()
                time.sleep(1)  # Cooldown after sound
            time.sleep(0.05)
    except KeyboardInterrupt:
        GPIO.cleanup()
        print("[EXIT] Real mode interrupted.")

# --- Virtual Auto Simulation Mode ---
def run_virtual_mode():
    time.sleep(2)
    print("\n[SIMULATION] Generating 3 simulated sound events...\n")
    time.sleep(1.5)
    try:
        while True:
            for _ in range(3):
                time.sleep(random.uniform(1, 3))
                print("\n[SIM] Simulated sound spike.")
                handle_sound_event()
            time.sleep(15)
    except KeyboardInterrupt:
        print("[EXIT] Virtual simulation interrupted.")

# --- Interactive Manual Mode (only if you run manually) ---
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

# --- Start Acoustic Sensor in a Thread (for Collar Mode) ---
def start_acoustic_listener():
    print("[ACOUSTIC] Connecting MQTT from collar mode...")
    utils.mqtt_client.connect(utils.broker, utils.port, 60)
    utils.mqtt_client.loop_start()

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

# --- Entry Point: Manual Developer Testing ---
if __name__ == "__main__":
    utils.mqtt_client.connect(utils.broker, utils.port, 60)
    utils.mqtt_client.loop_start()
    print("[MQTT] Acoustic sensor connected and publishing.")

    if USE_REAL_SENSOR and REAL_SENSOR_AVAILABLE:
        run_real_mode()
    else:
        print("[MODE] Real sensor unavailable or disabled. Entering simulation mode.")
        run_interactive_mode()
