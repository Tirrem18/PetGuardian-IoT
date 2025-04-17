import os
import time
import json
import random
import paho.mqtt.client as mqtt

# Attempt to import real IMU I2C library; fallback to virtual mode
try:
    from smbus2 import SMBus
    REAL_SENSOR = True
except ImportError:
    print("IMU module not found. Running in virtual mode.")
    REAL_SENSOR = False

# I2C address for MPU-6050
MPU6050_ADDR = 0x68

# MQTT configuration
BROKER = "test.mosquitto.org"
TOPIC = "petguardian/imu"

# Setup I2C bus for physical device
if REAL_SENSOR:
    bus = SMBus(1)  # Default I2C bus on Raspberry Pi

# Absolute path to /data/logs/imu_log.json
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "data", "logs")
LOG_PATH = os.path.join(LOG_DIR, "imu_log.json")
os.makedirs(LOG_DIR, exist_ok=True)

def send_data_to_cloud(motion_data):
    """Send IMU data to MQTT broker."""
    client = mqtt.Client()
    client.connect(BROKER)
    payload = json.dumps({
        "sensor": "imu",
        "accel_x": motion_data["accel_x"],
        "accel_y": motion_data["accel_y"],
        "accel_z": motion_data["accel_z"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    client.publish(TOPIC, payload)
    client.disconnect()
    print("Sent IMU data to MQTT broker.")

def log_imu_data(motion_data):
    """Log IMU data to /data/logs/imu_log.json."""
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "accel_x": motion_data["accel_x"],
        "accel_y": motion_data["accel_y"],
        "accel_z": motion_data["accel_z"]
    }

    logs = []
    if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 0:
        try:
            with open(LOG_PATH, "r") as log_file:
                logs = json.load(log_file)
            if not isinstance(logs, list):
                logs = []
        except Exception:
            logs = []

    logs.append(log_entry)

    with open(LOG_PATH, "w") as log_file:
        json.dump(logs, log_file, indent=4)

    print("Logged IMU data locally.")

def get_motion_data():
    """Retrieve IMU data from sensor or simulate values."""
    if REAL_SENSOR:
        accel_x = bus.read_byte_data(MPU6050_ADDR, 0x3B)
        accel_y = bus.read_byte_data(MPU6050_ADDR, 0x3D)
        accel_z = bus.read_byte_data(MPU6050_ADDR, 0x3F)
        return {
            "accel_x": accel_x,
            "accel_y": accel_y,
            "accel_z": accel_z
        }
    else:
        return {
            "accel_x": random.uniform(-2, 2),
            "accel_y": random.uniform(-2, 2),
            "accel_z": random.uniform(-2, 2)
        }

def imu_tracking():
    """Continuously track, log, and send IMU data."""
    print("IMU tracking active...")
    while True:
        motion_data = get_motion_data()
        log_imu_data(motion_data)
        send_data_to_cloud(motion_data)
        time.sleep(5)

if __name__ == "__main__":
    try:
        imu_tracking()
    except KeyboardInterrupt:
        print("\nIMU tracking stopped.")
