import time
import json
import os
import random
import paho.mqtt.client as mqtt

# Try to import Raspberry Pi GPS library; if unavailable, use virtual mode
try:
    import gpsd
    REAL_SENSOR = True
except ImportError:
    print("GPS module not found! Running in virtual mode...")
    REAL_SENSOR = False

BROKER = "test.mosquitto.org"
TOPIC = "petguardian/gps"

def send_data_to_cloud(location):
    """Send GPS data to MQTT broker."""
    client = mqtt.Client()
    client.connect(BROKER)
    payload = json.dumps({
        "sensor": "gps",
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    client.publish(TOPIC, payload)
    client.disconnect()
    print(f"Sent GPS Data to MQTT Broker: {payload}")

def log_gps_data(location):
    """Logs GPS data into a JSON file."""
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "latitude": location["latitude"],
        "longitude": location["longitude"]
    }

    if os.path.exists("gps_log.json"):
        try:
            with open("gps_log.json", "r") as log_file:
                logs = json.load(log_file)
            if not isinstance(logs, list):
                logs = []  
        except (json.JSONDecodeError, FileNotFoundError):
            logs = []  
    else:
        logs = []  

    logs.append(log_entry)

    with open("gps_log.json", "w") as log_file:
        json.dump(logs, log_file, indent=4)

    print(f"Logged GPS Data: {log_entry}")

def get_gps_location():
    """Gets GPS data from real sensor or generates mock data."""
    if REAL_SENSOR:
        gpsd.connect()
        packet = gpsd.get_current()
        return {"latitude": packet.lat, "longitude": packet.lon}
    else:
        return {"latitude": 51.5074 + random.uniform(-0.01, 0.01), "longitude": -0.1278 + random.uniform(-0.01, 0.01)}

def gps_tracking():
    """Tracks and logs GPS data continuously."""
    print("GPS Tracking Active...")

    while True:
        location = get_gps_location()
        log_gps_data(location)
        send_data_to_cloud(location)
        time.sleep(5)  # Adjust tracking interval

if __name__ == "__main__":
    try:
        gps_tracking()
    except KeyboardInterrupt:
        print("\n Stopping GPS tracking...")
