import os
import sys
import time
import random
import threading

# Ensure project root path is included
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import SensorUtils
try:
    from sensors.utils.sensor_utils import SensorUtils
except ModuleNotFoundError:
    from utils.sensor_utils import SensorUtils

# --- Sensor Mode Detection ---
USE_REAL_SENSOR = os.getenv("IMU", "false").strip().lower() == "true"  # Real/virtual IMU mode from .env
INTERACTIVE_MODE = __name__ == "__main__"  # True if running manually

# --- Real IMU Hardware Setup ---
try:
    if USE_REAL_SENSOR:
        import smbus  # SMBus library used to talk to MPU6050 via I2C
        # Define MPU6050 Registers
        MPU6050_ADDR = 0x68  # Default I2C address for MPU6050
        PWR_MGMT_1 = 0x6B
        ACCEL_XOUT_H = 0x3B

        # Initialize SMBus
        bus = smbus.SMBus(1)  # Bus 1 is standard on Raspberry Pi

        # Wake up MPU6050 (clears sleep mode)
        bus.write_byte_data(MPU6050_ADDR, PWR_MGMT_1, 0)

        REAL_SENSOR = True
        print("[INIT] Real IMU (MPU6050) sensor mode activated.")
    else:
        raise ImportError("Virtual mode forced or smbus not found.")
except ImportError as e:
    REAL_SENSOR = False
    print(f"[INIT] Virtual IMU mode activated. Reason: {e}")

# --- Initialize shared SensorUtils instance ---
utils = SensorUtils(
    sensor_name="imu",
    topic_publish="petguardian/imu"
)

# --- Generate real or fake IMU reading ---
# Reads data from MPU6050 or provides simulated data
def get_imu_reading():
    if REAL_SENSOR:
        # --- Read accelerometer data from MPU6050 ---
        def read_word(register):
            high = bus.read_byte_data(MPU6050_ADDR, register)
            low = bus.read_byte_data(MPU6050_ADDR, register + 1)
            value = (high << 8) + low
            if value >= 0x8000:
                value = -((65535 - value) + 1)
            return value

        # Read and scale accelerometer values to 'g' units
        accel_x = read_word(ACCEL_XOUT_H) / 16384.0
        accel_y = read_word(ACCEL_XOUT_H + 2) / 16384.0
        accel_z = read_word(ACCEL_XOUT_H + 4) / 16384.0

        return {
            "accel_x": round(accel_x, 6),
            "accel_y": round(accel_y, 6),
            "accel_z": round(accel_z, 6)
        }

    elif INTERACTIVE_MODE:
        # --- Developer manually inputs IMU values ---
        try:
            ax = float(input("accel_x: "))
            ay = float(input("accel_y: "))
            az = float(input("accel_z: "))
            return {"accel_x": ax, "accel_y": ay, "accel_z": az}
        except ValueError:
            print("[INPUT ERROR] Invalid input. Using zeros.")
            return {"accel_x": 0.0, "accel_y": 0.0, "accel_z": 0.0}

    else:
        # --- Virtual mode generates random readings ---
        return {
            "accel_x": round(random.uniform(0, 9), 6),
            "accel_y": round(random.uniform(0, 1), 6),
            "accel_z": round(random.uniform(0, 9), 6),
        }

# --- Process and publish an IMU reading ---
# Builds event payload and sends to cloud services
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
# Continuously reads and sends IMU data every few seconds
def run_real_mode():
    print("[MODE] Real IMU is publishing readings...")
    try:
        while True:
            handle_imu_event()
            time.sleep(2)
    except KeyboardInterrupt:
        print("[EXIT] Real IMU mode interrupted.")

# --- Manual input for IMU values ---
# Developer manually triggers IMU events
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
# Auto-generates simulated readings for testing
def run_virtual_mode():
    time.sleep(2)
    print("\n[SIMULATION] Auto-generating IMU events...\n")
    try:
        while True:
            time.sleep(2)
            print("\n[SIM] IMU reading simulated.")
            handle_imu_event()
            time.sleep(12)
            handle_imu_event()
            for _ in range(3):
                print("\n[SIM] IMU reading simulated.")
                handle_imu_event()
                time.sleep(11)
            print("[SIM] Cooling down for 120 seconds.")
            time.sleep(120)
    except KeyboardInterrupt:
        print("[EXIT] Virtual simulation interrupted.")

# --- Optional real/virtual prompt for developer ---
def prompt_sensor_mode():
    while True:
        choice = input("[SELECT MODE] Use real IMU? (Y/n): ").strip().lower()
        if choice in ("y", "yes"):
            return True
        elif choice in ("n", "no"):
            return False
        print("[INFO] Please enter 'Y' or 'N'.")

# --- Start IMU background listener ---
# Connects to MQTT and starts sensor publishing in thread
def start_imu_listener():
    def _imu_run_thread():
        utils.mqtt_client.connect(utils.broker, utils.port, 60)
        utils.mqtt_client.loop_start()
        print("[MQTT] IMU sensor connected and publishing.")

        if USE_REAL_SENSOR and REAL_SENSOR:
            run_real_mode()
        else:
            run_virtual_mode()

    thread = threading.Thread(target=_imu_run_thread, name="IMU_SensorThread", daemon=True)
    thread.start()

# --- Local development and testing ---
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
