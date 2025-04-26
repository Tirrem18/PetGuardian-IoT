# dashboard/util/dashboard_data.py

import base64
import json
import os
from dotenv import load_dotenv
from azure.cosmos import CosmosClient

# Step 1: Load environment variables from .env
load_dotenv()

class DashboardData:
    def __init__(self):
        # Step 2: Read settings from environment
        self.COSMOS_URI = os.getenv("COSMOS_URI")
        self.COSMOS_KEY = os.getenv("COSMOS_KEY")
        self.DATABASE_NAME = os.getenv("COSMOS_DB", "iotdata")
        self.CONTAINER_NAME = os.getenv("COSMOS_CONTAINER", "telemetry")
        self.CONFIG_CONTAINER = "config"

        # Local logs fallback
        self.local_log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "logs"))
        self.illumination_log_file = os.path.join(self.local_log_path, "illumination_log.json")
        self.threat_log_file = os.path.join(self.local_log_path, "threat_log.json")

        # Dashboard defaults
        # inside your DashboardData class

        self.DEFAULTS = {
            # General
            "home_lat": 54.5742,
            "home_lon": -1.2345,
            "safe_radius": 30,

            # Modes
            "threats_mode": True,
            "illumination_mode": True,

            # IlluminatorAI settings
            "velocity_threshold": 0.5,
            "velocity_risk_cap": 4,
            "lux_threshold": 200,
            "lux_risk_cap": 4,
            "gps_safe_radius": 30,  # duplicated but fine
            "gps_risk_cap": 3,
            "gps_weight_multiplier": 2,
            "mini_risk_threshold": 4.1,
            "full_risk_threshold": 6.5,
            "gps_wait_duration": 10,
            "bulb_cooldown": 5,

            # ThreatAI settings
            "threat_threshold": 8.0,
            "sound_cap": 5,
            "point_per_sound": 2,
            "sound_decay_interval": 10.0,
            "threat_cooldown": 30,
            "gps_check_cooldown": 10,
            "distance_per_point": 10,
        }


    # COSMOS CONNECTION
    def get_cosmos_container(self, name=None):
        name = name or self.CONTAINER_NAME
        client = CosmosClient(self.COSMOS_URI, credential=self.COSMOS_KEY)
        db = client.get_database_client(self.DATABASE_NAME)
        return db.get_container_client(name)

    # CONFIG LOADING
    def load_dashboard_settings(self):
        try:
            container = self.get_cosmos_container(name=self.CONFIG_CONTAINER)
            config_doc = container.read_item(item="dashboard_settings", partition_key="dashboard")
            return config_doc.get("settings", self.DEFAULTS.copy())
        except Exception as e:
            print(f"[CONFIG LOAD] Failed, using defaults. Reason: {e}")
            return self.DEFAULTS.copy()

    # CONFIG SAVING
    def save_dashboard_settings(self, settings_dict):
        try:
            container = self.get_cosmos_container(name=self.CONFIG_CONTAINER)
            doc = {
                "id": "dashboard_settings",
                "partitionKey": "dashboard",
                "settings": settings_dict
            }
            container.upsert_item(doc)
            print("[CONFIG SAVE] Settings updated in Cosmos.")
            return True
        except Exception as e:
            print(f"[CONFIG SAVE] Failed to save settings. Reason: {e}")
            return False

    # LOG FETCHING from Cosmos
    def fetch_all_logs_from_cosmos(self):
        """Fetch threat and illumination events from Cosmos."""
        try:
            container = self.get_cosmos_container(name=self.CONTAINER_NAME)
            threat_logs = []
            illumination_logs = []

            for item in container.query_items("SELECT * FROM c", enable_cross_partition_query=True):
                try:
                    encoded = item.get("Body", "")
                    if not encoded.strip():
                        continue
                    decoded = json.loads(base64.b64decode(encoded).decode("utf-8"))
                    event_type = decoded.get("event", "unknown")

                    if event_type == "threat":
                        threat_logs.append(decoded)
                    elif event_type == "illumination":
                        illumination_logs.append(decoded)

                except Exception as e:
                    print(f"[COSMOS LOG FETCH] Error decoding item: {e}")
                    continue

            return {
                "threats": threat_logs,
                "illuminations": illumination_logs
            }

        except Exception as e:
            print(f"[LOG FETCH] Failed to fetch logs from Cosmos: {e}")
            return {"threats": [], "illuminations": []}

    # LOCAL LOG FETCHING
    def load_threat_log_local(self):
        """Load threat events from local file."""
        return self._load_local_log_file(self.threat_log_file)

    def load_illumination_log_local(self):
        """Load illumination events from local file."""
        return self._load_local_log_file(self.illumination_log_file)

    def _load_local_log_file(self, filepath):
        """Internal: load any local JSON log file."""
        if not os.path.exists(filepath):
            return []
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[LOCAL LOG ERROR] Failed to load {filepath}: {e}")
            return []

