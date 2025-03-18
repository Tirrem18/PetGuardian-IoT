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
    print("Light sensor module not found! Running in virtual mode...")
    REAL_SENSOR = False

# BH1750 I2C Address (For Physical Sensor)
BH1750_ADDR = 0x23  

BROKER = "test.mosquitto.org"
TOPIC = "petguardian/light"

if REAL_SENSOR:
    bus = SMBus(1)  # I2C Bus on Raspberry Pi

def send_data_to_cloud(light_data):
    """Send light sensor data to MQTT broker."""
    client = mqtt.Client()
    client.connect(BROKER)
    payload = json.dumps({
        "sensor": "light",
        "lux": light_data["lux"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    client.publish(TOPIC, payload)
    client.disconnect()
    print(f"Sent Light Data to MQTT Broker: {payload}")

def log_light_data(light_data):
    """Logs light sensor data into a JSON file."""
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "lux": light_data["lux"]
    }

    if os.path.exists("light_log.json"):
        try:
            with open("light_log.json", "r") as log_file:
                logs = json.load(log_file)
            if not isinstance(logs, list):
                logs = []  
        except (json.JSONDecodeError, FileNotFoundError):
            logs = []  
    else:
        logs = []  

    logs.append(log_entry)

    with open("light_log.json", "w") as log_file:
        json.dump(logs, log_file, indent=4)

    print(f"Logged Light Data: {log_entry}")

def get_light_level():
    """Gets light sensor data from real sensor or generates mock data."""
    if REAL_SENSOR:
        data = bus.read_i2c_block_data(BH1750_ADDR, 0x10, 2)
        lux = (data[0] << 8) | data[1]  # Convert raw data to Lux
        return {"lux": lux}
    else:
        return {"lux": random.uniform(0, 1000)}  # Simulating Lux values

def light_tracking():
    """Tracks and logs light sensor data continuously."""
    print("Light Sensor Active...")

    while True:
        light_data = get_light_level()
        log_light_data(light_data)
        send_data_to_cloud(light_data)
        time.sleep(5)  # Adjust tracking interval

if __name__ == "__main__":
    try:
        light_tracking()
    except KeyboardInterrupt:
        print("\n Stopping light sensor tracking...")
