import os
import sys
import time
import random
import threading

# Ensure root path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try both import styles
try:
    from sensors.utils.sensor_utils import SensorUtils
except ModuleNotFoundError:
    from utils.sensor_utils import SensorUtils

# --- Detect Interactive Mode ---
INTERACTIVE_MODE = __name__ == "__main__"
REAL_SENSOR_AVAILABLE = False

try:
    import RPi.GPIO as GPIO
    REAL_SENSOR_AVAILABLE = True
except ImportError:
    print("[INIT] RPi.GPIO not found. Real sensor support unavailable.")

USE_REAL_SENSOR = os.getenv("SOUND", "false").strip().lower() == "true"

class AcousticSensor:
    def __init__(self):
        self.utils = SensorUtils(
            sensor_name="acoustic",
            topic_publish="petguardian/acoustic"
        )
        self.gpio_pin = 17

    def handle_sound_event(self):
        print("[ACOUSTIC] 🔊 Sending sound event to MQTT...")
        timestamp = self.utils.get_timestamp()
        data = {
            "sensor": "acoustic",
            "event": "loud_noise",
            "timestamp": timestamp
        }
        self.utils.log_locally("sound_log.json", data)
        self.utils.send_to_mqtt(data)
        self.utils.send_to_azure(data)
        self.utils.send_to_cosmos(data)

    def run_real_sensor(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.gpio_pin, GPIO.IN)
        print("[MODE] Listening for real acoustic signals on GPIO pin 17...")
        try:
            while True:
                if GPIO.input(self.gpio_pin) == GPIO.HIGH:
                    time.sleep(0.1)  # Debounce delay
                    if GPIO.input(self.gpio_pin) == GPIO.HIGH:
                        print("[EVENT] Real sound detected.")
                        self.handle_sound_event()
                        time.sleep(1)  # Cooldown to avoid multiple triggers
                time.sleep(0.1)
        except KeyboardInterrupt:
            GPIO.cleanup()
            print("[EXIT] Real sensor mode interrupted.")

    def run_virtual_sensor(self):
        time.sleep(2)
        print("\n[SIMULATION] Generating 3 simulated sound events...\n")
        time.sleep(1.5)
        try:
            while True:
                for _ in range(3):
                    time.sleep(random.uniform(1, 3))
                    print("\n[SIM] Simulated sound spike.")
                    self.handle_sound_event()
                time.sleep(15)  # Rest period between bursts
        except KeyboardInterrupt:
            print("[EXIT] Virtual simulation interrupted.")

    def run_interactive_mode(self):
        print("[INTERACTIVE] Type 'S' to simulate sound, or 'X' to exit.")
        try:
            while True:
                user_input = input(">>> ").strip().lower()
                if user_input == 's':
                    print("[INPUT] Manual sound event triggered.")
                    self.handle_sound_event()
                elif user_input == 'x':
                    print("[EXIT] Interactive mode ended.")
                    break
                else:
                    print("[INFO] Unknown input. Use 'S' or 'X'.")
        except KeyboardInterrupt:
            print("\n[EXIT] Interactive mode interrupted.")

    def start_listener(self):
        """Start the acoustic sensor listener (threaded for collar mode)."""
        print("[ACOUSTIC] 📡 Connecting MQTT from collar mode...")
        self.utils.mqtt_client.connect(self.utils.broker, self.utils.port, 60)
        self.utils.mqtt_client.loop_start()

        def _run():
            if USE_REAL_SENSOR and REAL_SENSOR_AVAILABLE:
                self.run_real_sensor()
            else:
                self.run_virtual_sensor()

        thread = threading.Thread(
            target=_run,
            name="AcousticSensorThread",
            daemon=True
        )
        thread.start()

    def dev_mode_run(self):
        """Developer direct run from CLI (only when __main__)."""
        self.utils.mqtt_client.connect(self.utils.broker, self.utils.port, 60)
        self.utils.mqtt_client.loop_start()
        print("[MQTT] Acoustic sensor connected and publishing.")

        if REAL_SENSOR_AVAILABLE:
            use_real = self.prompt_sensor_mode()
            if use_real:
                self.run_real_sensor()
            else:
                self.run_interactive_mode()
        else:
            print("[MODE] Real sensor unavailable. Entering interactive mode.")
            self.run_interactive_mode()

    @staticmethod
    def prompt_sensor_mode():
        """Only for dev CLI. In collar mode, .env is trusted."""
        while True:
            choice = input("[SELECT MODE] Use real acoustic sensor? (Y/n): ").strip().lower()
            if choice in ("y", "yes"):
                return True
            elif choice in ("n", "no"):
                return False
            print("[INFO] Please enter 'Y' or 'N'.")

# --- Entry Point ---
if __name__ == "__main__":
    sensor = AcousticSensor()
    sensor.dev_mode_run()
