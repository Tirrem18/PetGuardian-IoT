# --- dashboard/util/dashboard_data.py ---

import base64
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from azure.cosmos import CosmosClient

# --- Load environment variables ---
load_dotenv()

class DashboardData:
    def __init__(self):
        # --- Read settings from environment ---
        self.COSMOS_URI = os.getenv("COSMOS_URI")
        self.COSMOS_KEY = os.getenv("COSMOS_KEY")
        self.DATABASE_NAME = os.getenv("COSMOS_DB", "iotdata")
        self.CONTAINER_NAME = os.getenv("COSMOS_CONTAINER", "telemetry")
        self.CONFIG_CONTAINER = "config"

        # --- Local fallback paths ---
        self.local_log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "logs"))
        self.illumination_log_file = os.path.join(self.local_log_path, "illumination_log.json")
        self.threat_log_file = os.path.join(self.local_log_path, "threat_log.json")

        # --- Dashboard Defaults ---
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
            "lux_threshold": 500,
            "lux_risk_cap": 4,
            "gps_safe_radius": 30,
            "gps_risk_cap": 3,
            "gps_weight_multiplier": 2,
            "mini_risk_threshold": 4.1,
            "full_risk_threshold": 6.5,
            "gps_wait_duration": 10,
            "bulb_cooldown": 5,

            # ThreatAI settings
            "threat_threshold": 8.0,
            "sound_cap": 4.1,
            "point_per_sound": 2,
            "sound_decay_interval": 10.0,
            "threat_cooldown": 30,
            "gps_check_cooldown": 10,
            "distance_per_point": 10,
        }

    # --- COSMOS CONNECTION ---
    def get_cosmos_container(self, name=None):
        name = name or self.CONTAINER_NAME
        client = CosmosClient(self.COSMOS_URI, credential=self.COSMOS_KEY)
        db = client.get_database_client(self.DATABASE_NAME)
        return db.get_container_client(name)

    # --- CONFIG LOADING ---
    def load_dashboard_settings(self):
        """Load settings from Cosmos. Fallback to defaults if needed."""
        try:
            container = self.get_cosmos_container(name=self.CONFIG_CONTAINER)
            config_doc = container.read_item(item="dashboard_settings", partition_key="dashboard")
            loaded = config_doc.get("settings", {})
        except Exception as e:
            print(f"[CONFIG LOAD] Failed, using defaults. Reason: {e}")
            loaded = {}

        merged_config = self.DEFAULTS.copy()
        merged_config.update(loaded)
        return merged_config

    # --- CONFIG SAVING ---
    def save_dashboard_settings(self, settings_dict):
        """Save settings back to Cosmos."""
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

    # --- FETCH ALL LOGS FROM COSMOS ---
    def fetch_all_logs_from_cosmos(self):
        """Fetch threat, illumination, and sensor logs from Cosmos."""
        try:
            container = self.get_cosmos_container(name=self.CONTAINER_NAME)

            logs = {
                "threats": [],
                "illuminations": [],
                "camera": [],
                "bulb": [],
                "imu": [],
                "lux": [],
                "gps": [],
                "acoustic": []
            }

            for item in container.query_items("SELECT * FROM c", enable_cross_partition_query=True):
                try:
                    encoded = item.get("Body", "")
                    if not encoded.strip():
                        continue
                    decoded = json.loads(base64.b64decode(encoded).decode("utf-8"))

                    event = decoded.get("event", "").lower()
                    sensor = decoded.get("sensor", "").lower()

                    if event == "threat":
                        logs["threats"].append(decoded)
                    elif event == "illumination":
                        logs["illuminations"].append(decoded)
                    elif sensor in logs:
                        logs[sensor].append(decoded)
                    else:
                        print(f"[UNKNOWN LOG TYPE] {decoded}")

                except Exception as e:
                    print(f"[COSMOS LOG FETCH] Error decoding item: {e}")
                    continue

            return logs

        except Exception as e:
            print(f"[LOG FETCH] Failed to fetch logs from Cosmos: {e}")
            return {
                "threats": [],
                "illuminations": [],
                "camera": [],
                "bulb": [],
                "imu": [],
                "lux": [],
                "gps": [],
                "acoustic": []
            }

    # --- LOCAL LOG FETCHING ---
    def load_threat_log_local(self):
        return self._load_local_log_file(self.threat_log_file)

    def load_illumination_log_local(self):
        return self._load_local_log_file(self.illumination_log_file)

    def _load_local_log_file(self, filepath):
        if not os.path.exists(filepath):
            return []
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[LOCAL LOG ERROR] Failed to load {filepath}: {e}")
            return []

    # --- FETCH ALL LOGS ---
    def fetch_all_logs(self):
        """Try fetching logs from Cosmos first. Fallback to local."""
        try:
            cosmos_logs = self.fetch_all_logs_from_cosmos()
            if cosmos_logs["threats"] or cosmos_logs["illuminations"]:
                return cosmos_logs
        except Exception as e:
            print(f"[FALLBACK] Error fetching Cosmos logs: {e}")

        print("[FALLBACK] Loading local logs instead.")
        return {
            "threats": self.load_threat_log_local(),
            "illuminations": self.load_illumination_log_local()
        }

    # --- CLEAN DUPLICATE LOGS ---
    def clean_duplicate_logs(self):
        """Delete duplicate events based on timestamp and event type."""
        try:
            container = self.get_cosmos_container(name=self.CONTAINER_NAME)
            all_items = list(container.query_items("SELECT * FROM c", enable_cross_partition_query=True))

            seen = set()
            to_delete = []

            for item in all_items:
                try:
                    encoded = item.get("Body", "")
                    if not encoded.strip():
                        continue
                    decoded = json.loads(base64.b64decode(encoded).decode("utf-8"))
                    key = (decoded.get("timestamp", ""), decoded.get("event", ""))

                    if key in seen:
                        to_delete.append(item["id"])
                    else:
                        seen.add(key)

                except:
                    continue

            for doc_id in to_delete:
                try:
                    container.delete_item(item=doc_id, partition_key="collar01")
                except:
                    continue

        except Exception:
            pass

    # --- SORT EVENTS BY TIME ---
    def sort_events_by_time(self, events):
        """Sort events by timestamp (latest first)."""
        try:
            return sorted(events, key=lambda x: x.get("timestamp", ""), reverse=True)
        except Exception as e:
            print(f"[SORT ERROR] Failed to sort events: {e}")
            return events

    # --- FILTER EVENTS AFTER TIMESTAMP ---
    def filter_events_since(self, events, since_timestamp):
        """Filter events after a given timestamp."""
        try:
            return [e for e in events if e.get("timestamp", "") > since_timestamp]
        except Exception as e:
            print(f"[FILTER ERROR] Failed to filter events: {e}")
            return events

    # --- FIND CAMERA IMAGE CLOSEST TO THREAT TIME ---
    def find_matching_camera_for_threat(self, threat_timestamp, camera_logs):
        """Find closest camera image to the threat timestamp."""
        try:
            threat_time = datetime.strptime(threat_timestamp, "%Y-%m-%d %H:%M:%S")
            closest_img = None
            smallest_delta = float('inf')

            for cam in camera_logs:
                cam_ts_str = cam.get("timestamp", None)
                if not cam_ts_str:
                    continue

                try:
                    cam_time = datetime.strptime(cam_ts_str, "%Y-%m-%d %H:%M:%S")
                    delta = abs((threat_time - cam_time).total_seconds())

                    if delta <= 15 and delta < smallest_delta:
                        smallest_delta = delta
                        closest_img = cam

                except Exception as e:
                    print(f"[CAMERA MATCH ERROR] {e}")
                    continue

            if closest_img:
                print(f"[MATCH FOUND] Closest camera at {closest_img.get('timestamp', 'unknown')} (Δ {smallest_delta}s)")
            else:
                print("[MATCH NOT FOUND] No camera image within 15s of threat event.")

            return closest_img

        except Exception as e:
            print(f"[MATCHING ERROR] {e}")
            return None

    # --- FETCH ALL CAMERA LOGS ---
    def fetch_all_camera_logs(self):
        """Fetch all camera sensor events."""
        try:
            container = self.get_cosmos_container(name=self.CONTAINER_NAME)
            camera_logs = []

            for item in container.query_items("SELECT * FROM c", enable_cross_partition_query=True):
                try:
                    encoded = item.get("Body", "")
                    if not encoded.strip():
                        continue

                    decoded = json.loads(base64.b64decode(encoded).decode("utf-8"))
                    if decoded.get("sensor") == "camera":
                        camera_logs.append(decoded)

                except Exception as e:
                    print(f"[CAMERA FETCH ERROR] {e}")
                    continue

            print(f"[CAMERA FETCH] Fetched {len(camera_logs)} camera events.")
            return camera_logs

        except Exception as e:
            print(f"[CAMERA LOG FETCH ERROR] {e}")
            return []
