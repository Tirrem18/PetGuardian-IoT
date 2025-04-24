# fetch_threat_matches.py
import base64
import json
from datetime import datetime, timedelta
from azure.cosmos import CosmosClient

# Cosmos config
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

def get_threat_matches():
    client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
    db = client.get_database_client(DATABASE_NAME)
    container = db.get_container_client(CONTAINER_NAME)

    threat_logs = []
    camera_logs = []

    for item in container.query_items("SELECT * FROM c", enable_cross_partition_query=True):
        try:
            encoded = item.get("Body", "")
            if not encoded.strip():
                continue
            decoded = json.loads(base64.b64decode(encoded).decode("utf-8"))
            sensor = decoded.get("sensor")
            timestamp = decoded.get("timestamp")

            if sensor == "threat":
                threat_logs.append({
                    "timestamp": timestamp,
                    "latitude": decoded.get("gps_latitude", "N/A"),
                    "longitude": decoded.get("gps_longitude", "N/A"),
                    "reason": decoded.get("reason", "Unknown reason"),
                })

            elif sensor == "camera":
                camera_logs.append({
                    "timestamp": timestamp,
                    "image_base64": decoded.get("image_base64", None)
                })
        except Exception as e:
            print(f"[ERROR] Skipped: {e}")

    return match_threats_to_images(threat_logs, camera_logs)

def match_threats_to_images(threats, cameras):
    def parse_time(ts):
        return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

    results = []
    for threat in threats:
        threat_time = parse_time(threat["timestamp"])
        best_match = None
        min_delta = timedelta(seconds=3)

        for cam in cameras:
            try:
                cam_time = parse_time(cam["timestamp"])
                if abs(threat_time - cam_time) <= min_delta:
                    best_match = cam
                    min_delta = abs(threat_time - cam_time)
            except:
                continue

        results.append({
            **threat,
            "image_base64": best_match["image_base64"] if best_match else None
        })

    return results


def get_most_recent_threat():
    # Return a hardcoded fake threat for testing
    return {
        "latitude": 54.5749,      # Slightly offset from your home lat
        "longitude": -1.2349,     # Slightly offset from your home lon
        "timestamp": "2025-04-24 12:34:56"
    }

