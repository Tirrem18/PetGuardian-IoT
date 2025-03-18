import time
import json
import os
import random
import paho.mqtt.client as mqtt

# Try to import Raspberry Pi I2C library; if unavailable, use virtual mode
try:
    from smbus2 import SMBus
    REAL_SENSOR = True
except ImportError:
    print("IMU module not found! Running in virtual mode...")
    REAL_SENSOR = False

# MPU-6050 I2C Address (For Physical Sensor)
MPU6050_ADDR = 0x68  

BROKER = "test.mosquitto.org"
TOPIC = "petguardian/imu"

if REAL_SENSOR:
    bus = SMBus(1)  # I2C Bus on Raspberry Pi

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
    print(f"Sent IMU Data to MQTT Broker: {payload}")

def log_imu_data(motion_data):
    """Logs IMU data into a JSON file."""
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "accel_x": motion_data["accel_x"],
        "accel_y": motion_data["accel_y"],
        "accel_z": motion_data["accel_z"]
    }

    if os.path.exists("imu_log.json"):
        try:
            with open("imu_log.json", "r") as log_file:
                logs = json.load(log_file)
            if not isinstance(logs, list):
                logs = []  
        except (json.JSONDecodeError, FileNotFoundError):
            logs = []  
    else:
        logs = []  

    logs.append(log_entry)

    with open("imu_log.json", "w") as log_file:
        json.dump(logs, log_file, indent=4)

    print(f"Logged IMU Data: {log_entry}")

def get_motion_data():
    """Gets IMU data from real sensor or generates mock data."""
    if REAL_SENSOR:
        accel_x = bus.read_byte_data(MPU6050_ADDR, 0x3B)
        accel_y = bus.read_byte_data(MPU6050_ADDR, 0x3D)
        accel_z = bus.read_byte_data(MPU6050_ADDR, 0x3F)
        return {"accel_x": accel_x, "accel_y": accel_y, "accel_z": accel_z}
    else:
        return {"accel_x": random.uniform(-2, 2), "accel_y": random.uniform(-2, 2), "accel_z": random.uniform(-2, 2)}

def imu_tracking():
    """Tracks and logs IMU data continuously."""
    print("IMU Tracking Active...")

    while True:
        motion_data = get_motion_data()
        log_imu_data(motion_data)
        send_data_to_cloud(motion_data)
        time.sleep(5)  # Adjust tracking interval

if __name__ == "__main__":
    try:
        imu_tracking()
    except KeyboardInterrupt:
        print("\n Stopping IMU tracking...")
