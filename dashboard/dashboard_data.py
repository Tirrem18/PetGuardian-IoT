import base64
import json
from azure.cosmos import CosmosClient

# Cosmos DB configuration
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"
CONFIG_CONTAINER = "config"  # new container for settings

# Dashboard default settings
DEFAULTS = {
    "home_lat": 54.5742,
    "home_lon": -1.2345,
    "safe_radius": 30,
    "threat_enabled": True,
    "night_enabled": True,
    "cooldown": 30,
    "sound_window": 10,
    "min_sounds": 3,
    "min_interval": 1,
    "lux_threshold": 30,
    "imu_threshold": 1,
}


# Connect to Cosmos containers
def get_cosmos_container(name=CONTAINER_NAME):
    client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
    db = client.get_database_client(DATABASE_NAME)
    return db.get_container_client(name)

# Shared config loader from Cosmos
def load_config():
    try:
        container = get_cosmos_container(name=CONFIG_CONTAINER)
        print("[CONFIG LOAD] Trying to fetch dashboard_settings from Cosmos...")
        config_doc = container.read_item(item="dashboard_settings", partition_key="dashboard")
        print("[CONFIG LOAD] Loaded config from Cosmos:")
        print(json.dumps(config_doc["settings"], indent=2))
        return config_doc.get("settings", DEFAULTS.copy())
    except Exception as e:
        print(f"[CONFIG LOAD] Failed to load config from Cosmos — using defaults. Reason: {e}")
        return DEFAULTS.copy()

# Load for dashboard use
def load_dashboard_settings():
    return load_config()

# Load for AI/Threat use
def load_threat_config_from_cosmos():
    settings = load_config()
    return {
        "home_lat": settings["home_lat"],
        "home_lon": settings["home_lon"],
        "safe_radius": settings["safe_radius"],
        "cooldown": settings["cooldown"],
        "sound_window": settings["sound_window"],
        "min_sounds": settings["min_sounds"],
        "min_interval": settings["min_interval"]
    }

# Fetch logs
def fetch_all_logs():
    container = get_cosmos_container(name=CONTAINER_NAME)
    logs = {
        "threat": [],
        "acoustic": [],
        "gps": [],
        "camera": [],
        "light": [],
        "imu": [],
        "unknown": []
    }

    for item in container.query_items("SELECT * FROM c", enable_cross_partition_query=True):
        try:
            encoded = item.get("Body", "")
            if not encoded.strip():
                continue

            decoded = json.loads(base64.b64decode(encoded).decode("utf-8"))
            sensor = decoded.get("sensor", "unknown")
            decoded["timestamp"] = decoded.get("timestamp", item.get("timestamp", "N/A"))
            logs.get(sensor, logs["unknown"]).append(decoded)
        except Exception:
            continue

    return logs


def save_dashboard_settings(settings_dict):
    try:
        container = get_cosmos_container(name=CONFIG_CONTAINER)
        doc = {
            "id": "dashboard_settings",
            "partitionKey": "dashboard",
            "settings": settings_dict
        }
        container.upsert_item(doc)
        print("[CONFIG SAVE] Settings updated in Cosmos.")
        return True
    except Exception as e:
        print(f"[CONFIG SAVE] Failed to save settings to Cosmos. Reason: {e}")
        return False

