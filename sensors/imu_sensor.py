import os
import sys
import time
import random
import threading  # ✅ Added

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from sensors.utils.sensor_utils import SensorUtils
except ModuleNotFoundError:
    from utils.sensor_utils import SensorUtils

# --- Sensor Mode Detection ---
USE_REAL_SENSOR = os.getenv("IMU", "false").strip().lower() == "true"
INTERACTIVE_MODE = __name__ == "__main__"

# --- Try importing real sensor support (MPU6050 via smbus) ---
try:
    if USE_REAL_SENSOR:
        import smbus  # Replace with actual MPU6050 driver in real setup
        REAL_SENSOR = True
        print("[INIT] Real IMU (MPU6050) sensor mode activated.")
    else:
        raise ImportError("smbus not found or virtual mode forced.")

except ImportError as e:
    REAL_SENSOR = False
    print(f"[INIT] Virtual IMU mode activated. Reason: {e}")

# --- Initialize shared utility class ---
utils = SensorUtils(
    sensor_name="imu",
    topic_publish="petguardian/imu"
)

# --- Generate real or fake IMU reading ---
def get_imu_reading():
    if REAL_SENSOR:
        # Replace with actual MPU6050 reading logic
        return {
            "accel_x": round(random.uniform(-2, 2), 6),
            "accel_y": round(random.uniform(-2, 2), 6),
            "accel_z": round(random.uniform(-2, 2), 6),
        }
    elif INTERACTIVE_MODE:
        try:
            ax = float(input("accel_x: "))
            ay = float(input("accel_y: "))
            az = float(input("accel_z: "))
            return {"accel_x": ax, "accel_y": ay, "accel_z": az}
        except ValueError:
            print("[INPUT ERROR] Invalid input. Using zeros.")
            return {"accel_x": 0.0, "accel_y": 0.0, "accel_z": 0.0}
    else:
        return {
            "accel_x": round(random.uniform(0, 9), 6),
            "accel_y": round(random.uniform(0, 1), 6),
            "accel_z": round(random.uniform(0, 9), 6),
        }

# --- Process and publish an IMU reading ---
def handle_imu_event():
    timestamp = utils.get_timestamp()
    data = {
        "sensor": "imu",
        "timestamp": timestamp,
        **get_imu_reading()
    }
    utils.log_locally("imu_log.json", data)
    utils.send_to_mqtt(data)
    utils.send_to_azure(data)
    utils.send_to_cosmos(data)

# --- Real IMU always-on mode ---
def run_real_mode():
    print("[MODE] Real IMU is publishing readings...")
    try:
        while True:
            handle_imu_event()
            time.sleep(2)
    except KeyboardInterrupt:
        print("[EXIT] Real IMU mode interrupted.")

# --- Manual input for IMU values ---
def run_interactive_mode():
    print("[INTERACTIVE] Type 'I' to simulate IMU reading, or 'X' to exit.")
    try:
        while True:
            cmd = input(">>> ").strip().lower()
            if cmd == "i":
                print("[INPUT] Manual IMU reading triggered.")
                handle_imu_event()
            elif cmd == "x":
                print("[EXIT] Interactive mode ended.")
                break
            else:
                print("[INFO] Use 'I' or 'X'.")
    except KeyboardInterrupt:
        print("[EXIT] Interactive mode interrupted.")

# --- Virtual simulated IMU events ---
def run_virtual_mode():
    print("[SIMULATION] Auto-generating IMU events...\n")
    time.sleep(3)
    try:
        while True:
            for _ in range(3):
                time.sleep(random.uniform(1, 3))
                print("[SIM] IMU reading simulated.")
                handle_imu_event()
            print("[SIM] Cooling down for 120 seconds.")
            time.sleep(120)
    except KeyboardInterrupt:
        print("[EXIT] Virtual simulation interrupted.")

# --- Optional real/virtual prompt ---
def prompt_sensor_mode():
    while True:
        choice = input("[SELECT MODE] Use real IMU? (Y/n): ").strip().lower()
        if choice in ("y", "yes"):
            return True
        elif choice in ("n", "no"):
            return False
        print("[INFO] Please enter 'Y' or 'N'.")


def start_imu_listener():
    def _imu_run_thread():
        if USE_REAL_SENSOR and REAL_SENSOR:
            run_real_mode()
        else:
            run_virtual_mode()

    thread = threading.Thread(target=_imu_run_thread, name="IMU_SensorThread", daemon=True)
    thread.start()


# --- Local development / testing ---
if __name__ == "__main__":
    utils.mqtt_client.connect(utils.broker, utils.port, 60)
    utils.mqtt_client.loop_start()
    print("[MQTT] IMU sensor connected and publishing.")

    if REAL_SENSOR:
        if prompt_sensor_mode():
            run_real_mode()
        else:
            run_interactive_mode()
    else:
        print("[MODE] Real IMU unavailable. Entering virtual test mode.")
        run_interactive_mode()
