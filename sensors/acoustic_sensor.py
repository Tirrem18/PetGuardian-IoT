import os
import sys
import time
import random
import threading

# Root path fix
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try import utils
try:
    from sensors.utils.sensor_utils import SensorUtils
except ModuleNotFoundError:
    from utils.sensor_utils import SensorUtils

# Mode detection
INTERACTIVE_MODE = __name__ == "__main__"
REAL_SENSOR_AVAILABLE = False

try:
    import RPi.GPIO as GPIO
    REAL_SENSOR_AVAILABLE = True
except ImportError:
    print("[INIT] RPi.GPIO not found. Real sensor support unavailable.")

# Always trust .env
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
        GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # <-- PULL UP now
        print("[MODE] Listening for real acoustic signals on GPIO pin 17 (active LOW)...")
        try:
            while True:
                if GPIO.input(self.gpio_pin) == GPIO.LOW:
                    print("[EVENT] Real sound detected.")
                    self.handle_sound_event()
                    time.sleep(1)  # Cooldown after detecting sound
                time.sleep(0.05)  # Light polling
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
                time.sleep(15)  # Rest period
        except KeyboardInterrupt:
            print("[EXIT] Virtual simulation interrupted.")

    def start_listener(self):
        """Start sensor listener in collar mode (threaded)."""
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
        """If running manually (__main__), still obey .env."""
        self.utils.mqtt_client.connect(self.utils.broker, self.utils.port, 60)
        self.utils.mqtt_client.loop_start()
        print("[MQTT] Acoustic sensor connected and publishing.")

        if USE_REAL_SENSOR and REAL_SENSOR_AVAILABLE:
            self.run_real_sensor()
        else:
            print("[MODE] Real sensor unavailable or disabled. Entering simulation mode.")
            self.run_virtual_sensor()

# --- CLI Entry ---
if __name__ == "__main__":
    sensor = AcousticSensor()
    sensor.dev_mode_run()
