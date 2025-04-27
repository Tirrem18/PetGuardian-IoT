import os
import sys
import time
import random
import threading

# Ensure root path is in sys.path for clean imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import SensorUtils from sensors.utils, fallback if necessary
try:
    from sensors.utils.sensor_utils import SensorUtils
except ModuleNotFoundError:
    from utils.sensor_utils import SensorUtils

# --- Mode Detection ---
INTERACTIVE_MODE = __name__ == "__main__"  # True if running this file directly
REAL_SENSOR_AVAILABLE = False  # Assume no real hardware sensor initially

# Try importing GPIO module to detect real sensor availability
try:
    import RPi.GPIO as GPIO
    REAL_SENSOR_AVAILABLE = True  # Real GPIO sensor available
except ImportError:
    print("[INIT] RPi.GPIO not found. Real sensor support unavailable.")

# Always prefer .env settings to control real or virtual mode
USE_REAL_SENSOR = os.getenv("SOUND", "false").strip().lower() == "true"

# --- Shared Utilities ---
# Initialize shared SensorUtils instance for acoustic sensor
utils = SensorUtils(
    sensor_name="acoustic",
    topic_publish="petguardian/acoustic"  # MQTT topic to publish acoustic events
)

# --- Event Logic ---
# Handles the entire workflow when a sound event is detected
def handle_sound_event():
    print("[ACOUSTIC] Sending sound event to MQTT...")
    timestamp = utils.get_timestamp()
    data = {
        "sensor": "acoustic",
        "event": "loud_noise",
        "timestamp": timestamp
    }
    # Save locally, then publish to cloud services
    utils.log_locally("sound_log.json", data)
    utils.send_to_mqtt(data)
    utils.send_to_azure(data)
    utils.send_to_cosmos(data)

# --- Real Sensor GPIO Mode ---
# Monitors a real hardware sensor connected to GPIO 17
def run_real_mode():
    GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering
    GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Setup GPIO 17 as input with pull-up resistor
    print("[MODE] Listening for real acoustic signals on GPIO 17 (LOW = sound detected)...")
    try:
        while True:
            if GPIO.input(17) == GPIO.LOW:  # A sound event is detected when pin reads LOW
                print("[EVENT] Real sound detected.")
                handle_sound_event()
                time.sleep(1)  # Cooldown to prevent spamming multiple events
            time.sleep(0.05)  # Polling delay between reads
    except KeyboardInterrupt:
        GPIO.cleanup()  # Clean up GPIO on exit
        print("[EXIT] Real mode interrupted.")

# --- Virtual Auto Simulation Mode ---
# Simulates sound events automatically for testing without hardware
def run_virtual_mode():
    time.sleep(2)  # Brief startup delay
    print("\n[SIMULATION] Generating 3 simulated sound events...\n")
    time.sleep(1.5)
    try:
        while True:
            for _ in range(3):  # Generate three quick simulated events
                time.sleep(random.uniform(1, 3))  # Random small delay between events
                print("\n[SIM] Simulated sound spike.")
                handle_sound_event()
            time.sleep(15)  # Longer pause after burst of events
    except KeyboardInterrupt:
        print("[EXIT] Virtual simulation interrupted.")

# --- Interactive Manual Mode ---
# Manual developer testing mode: manually trigger sound events by typing commands
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

# --- Start Acoustic Sensor in a Background Thread (for Collar Mode) ---
# Starts the acoustic sensor listening automatically when running inside live system
def start_acoustic_listener():
    print("[ACOUSTIC] Connecting MQTT from collar mode...")
    utils.mqtt_client.connect(utils.broker, utils.port, 60)  # Connect MQTT
    utils.mqtt_client.loop_start()  # Start MQTT background loop

    # Thread target function to run real or virtual mode based on environment
    def _acoustic_run_thread():
        if USE_REAL_SENSOR and REAL_SENSOR_AVAILABLE:
            run_real_mode()
        else:
            run_virtual_mode()

    # Start the acoustic listening thread
    thread = threading.Thread(
        target=_acoustic_run_thread,
        name="AcousticSensorThread",
        daemon=True  # Daemon threads automatically exit with the main program
    )
    thread.start()

# --- Entry Point: Manual Developer Testing ---
# Runs if this file is launched manually (not imported as a module)
if __name__ == "__main__":
    # Connect to MQTT first
    utils.mqtt_client.connect(utils.broker, utils.port, 60)
    utils.mqtt_client.loop_start()
    print("[MQTT] Acoustic sensor connected and publishing.")

    # Select real or simulated sensor mode based on environment and availability
    if USE_REAL_SENSOR and REAL_SENSOR_AVAILABLE:
        run_real_mode()
    else:
        print("[MODE] Real sensor unavailable or disabled. Entering simulation mode.")
        run_interactive_mode()
