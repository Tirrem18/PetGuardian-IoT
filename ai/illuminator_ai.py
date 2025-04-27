import json
import time
import math
import joblib
import pandas as pd
from ai.utils.ai_utils import AIUtils
from dashboard.util.dashboard_data import DashboardData

# --- Illuminator AI (Lux + Motion + GPS Risk Detection) ---
class IlluminatorAI:
    def __init__(self, client_id="illuminator_core"):
        self.ai = AIUtils(client_id=client_id)
        print(f"[ILLUMINATOR AI] Using client_id: {client_id}")

        # --- Load Configuration from Cosmos (via DashboardData) ---
        self.config = DashboardData().load_dashboard_settings()

        # Settings
        self.velocity_threshold = self.config["velocity_threshold"]
        self.velocity_risk_cap = self.config["velocity_risk_cap"]
        self.lux_threshold = self.config["lux_threshold"]
        self.lux_risk_cap = self.config["lux_risk_cap"]
        self.gps_safe_radius = self.config["gps_safe_radius"]
        self.gps_risk_cap = self.config["gps_risk_cap"]
        self.mini_risk_threshold = self.config["mini_risk_threshold"]
        self.full_risk_threshold = self.config["full_risk_threshold"]
        self.gps_wait_duration = self.config["gps_wait_duration"]
        self.bulb_cooldown = self.config["bulb_cooldown"]
        self.home_lat = self.config["home_lat"]
        self.home_lon = self.config["home_lon"]
        self.home_radius = self.config["safe_radius"]
        self.gps_weight_multiplier = self.config["gps_weight_multiplier"]

        # Cached Sensor Readings
        self.pending_illumination = None
        self.last_velocity = None
        self.last_lux = None
        self.last_gps = None
        self.gps_wait_start = 0
        self.last_gps_check_time = 0
        self.last_bulb_trigger_time = 0

        self.is_waiting_for_gps = False  # NEW: Prevent multiple IMU triggers during a waiting cycle

        # Load AI Model
        try:
            self.illumination_model = joblib.load("ai/models/illumination_model.pkl")
            print("[ILLUMINATOR AI] AI model for illumination loaded.")
        except Exception as e:
            print(f"[ILLUMINATOR AI] Failed to load illumination AI model: {e}")
            self.illumination_model = None

        print("[ILLUMINATOR AI] IlluminatorAI initialized.")

    # --- Handle IMU Event (Movement Detection) ---
    def handle_imu_event(self, payload):
        try:
            if self.is_waiting_for_gps:
                print("[ILLUMINATOR AI] Waiting for GPS. Ignoring new IMU event.")
                return

            if "velocity" in payload:
                velocity = float(payload.get("velocity", 0))
            elif all(axis in payload for axis in ["accel_x", "accel_y", "accel_z"]):
                ax = float(payload.get("accel_x", 0))
                ay = float(payload.get("accel_y", 0))
                az = float(payload.get("accel_z", 0))
                velocity = math.sqrt(ax**2 + ay**2 + az**2) * 0.1
                print(f"[ILLUMINATOR AI] Estimated velocity from accel: {velocity:.2f} m/s")
            else:
                velocity = 0

            self.last_velocity = velocity

            if velocity < self.velocity_threshold:
                print("[ILLUMINATOR AI] Movement too slow. No Lux or GPS needed.")
                self.pending_illumination = None
                return

            print(f"[ILLUMINATOR AI] Detected fast movement: {velocity:.2f} m/s — waiting for Lux reading...")
            self.send_lux_trigger()

        except Exception as e:
            print(f"[ILLUMINATOR AI] Failed to process IMU payload: {e}")

    # --- Handle Lux Event (Ambient Light Detection) ---
    def handle_lux_event(self, payload):
        try:
            lux = float(payload.get("lux", 1000))
            self.last_lux = lux

            if self.last_velocity is None:
                print("[ILLUMINATOR AI] No velocity cached. Ignoring Lux event.")
                return

            velocity_risk = min((self.last_velocity / self.velocity_threshold) * 2, self.velocity_risk_cap)
            lux_threshold = self.lux_threshold

            if lux >= lux_threshold:
                lux_risk = 0
            else:
                darkness_ratio = (lux_threshold - lux) / lux_threshold
                lux_risk = min(darkness_ratio * self.lux_risk_cap, self.lux_risk_cap)

            combined_risk = velocity_risk + lux_risk

            print(f"[ILLUMINATOR AI] Velocity Risk: {velocity_risk:.2f}, Lux Risk: {lux_risk:.2f} — Combined: {combined_risk:.2f}")

            if combined_risk < self.mini_risk_threshold:
                print("[ILLUMINATOR AI] Combined risk too low. No GPS needed.\n")
                self.pending_illumination = None
                return

            self.pending_illumination = {
                "velocity_risk": velocity_risk,
                "lux_risk": lux_risk,
                "timestamp": time.time()
            }
            self.gps_wait_start = time.time()
            self.is_waiting_for_gps = True
            self.send_gps_trigger()

        except Exception as e:
            print(f"[ILLUMINATOR AI] Failed to process Lux payload: {e}")

    # --- Handle GPS Event (Location Verification) ---
    def handle_gps_event(self, payload):
        try:
            self.last_gps = {
                "latitude": float(payload.get("latitude")),
                "longitude": float(payload.get("longitude")),
                "timestamp": time.time()
            }
            print("[ILLUMINATOR AI] GPS location updated.")

            if not self.pending_illumination:
                print("[ILLUMINATOR AI] No pending illumination event, ignoring GPS.")
                self.is_waiting_for_gps = False
                return

            self.evaluate_threat()
            self.is_waiting_for_gps = False

        except Exception as e:
            print(f"[ILLUMINATOR AI] Failed to process GPS payload: {e}")
            self.is_waiting_for_gps = False

    # --- Evaluate Total Threat Score ---
    def evaluate_threat(self):
        try:
            now = time.time()
            pending = self.pending_illumination
            velocity_risk = pending.get("velocity_risk", 0)
            lux_risk = pending.get("lux_risk", 0)

            if self.last_gps is None:
                elapsed = now - self.gps_wait_start
                if elapsed > self.gps_wait_duration:
                    gps_risk = self.gps_risk_cap
                else:
                    print(f"[ILLUMINATOR AI] Waiting for GPS... {elapsed:.1f} seconds elapsed.")
                    return
            else:
                gps_risk = self.calculate_gps_risk(self.last_gps)

            total_score = round(velocity_risk + lux_risk + gps_risk, 2)

        except Exception as e:
            print(f"[ILLUMINATOR AI] Threat evaluation setup failed: {e}")
            return

        # --- Use AI Model to Predict Illumination Need ---
        if self.illumination_model:
            try:
                input_data = pd.DataFrame([{
                    "velocity_risk": velocity_risk,
                    "lux_risk": lux_risk,
                    "gps_risk": gps_risk
                }])

                prediction = self.illumination_model.predict(input_data)[0]

                if prediction == 1:
                    print("\n[ILLUMINATOR AI] ML Model predicted illumination needed.\n")
                    self.trigger_illuminator(total_score)
                else:
                    print("\n[ILLUMINATOR AI] ML Model predicted no illumination needed.\n")

            except Exception as e:
                print(f"[ILLUMINATOR AI] AI prediction failed: {e}")

        else:
            if total_score >= self.full_risk_threshold:
                self.trigger_illuminator(total_score)
            else:
                print("[ILLUMINATOR AI] Threat score too low. No bulb activation.")

        self.pending_illumination = None

    # --- Calculate GPS Risk Based on Distance ---
    def calculate_gps_risk(self, gps):
        try:
            lat1 = math.radians(gps["latitude"])
            lon1 = math.radians(gps["longitude"])
            lat2 = math.radians(self.home_lat)
            lon2 = math.radians(self.home_lon)

            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            distance = 6371000 * c

            print(f"[ILLUMINATOR AI] Distance from home: {distance:.2f} meters\n")

            if distance <= self.gps_safe_radius:
                return 0

            gps_risk = ((distance - self.gps_safe_radius) / self.gps_safe_radius) * self.gps_weight_multiplier
            return min(gps_risk, self.gps_risk_cap)

        except Exception as e:
            print(f"[ILLUMINATOR AI] GPS risk calculation failed: {e}")
            return self.gps_risk_cap

    # --- Send GPS Trigger Request ---
    def send_gps_trigger(self):
        print("[ILLUMINATOR AI] Sending GPS trigger...")
        for attempt in range(3):
            success = self.ai.publish("petguardian/trigger/gps", {
                "command": "get_gps",
                "timestamp": self.ai.get_timestamp()
            })
            if success:
                print("[ILLUMINATOR AI] GPS trigger published.")
                return
        print("[ILLUMINATOR AI] Failed to publish GPS trigger.")

    # --- Send Lux Trigger Request ---
    def send_lux_trigger(self):
        print("[ILLUMINATOR AI] Sending Lux trigger...")
        for attempt in range(3):
            success = self.ai.publish("petguardian/trigger/lux", {
                "command": "get_lux",
                "timestamp": self.ai.get_timestamp()
            })
            if success:
                print("[ILLUMINATOR AI] Lux trigger published.\n")
                return
            
        print("[ILLUMINATOR AI] Failed to publish Lux trigger.")

    # --- Trigger Bulb Activation ---
    def trigger_illuminator(self, threat_score):
        now = time.time()
        if now - self.last_bulb_trigger_time < self.bulb_cooldown:
            print("[ILLUMINATOR AI] Bulb cooldown active. Skipping activation.")
            return

        self.last_bulb_trigger_time = now
        timestamp = self.ai.get_timestamp()

        event = {
            "timestamp": timestamp,
            "event": "illumination",
            "score": threat_score,
            "reason": "AI Model: Movement + Darkness + GPS risk exceeded threshold."
        }

        self.ai.log_locally("illumination_log.json", event)
        self.ai.send_to_azure(event)
        self.ai.send_to_cosmos(event, tag="ai")

        self.ai.publish("petguardian/trigger/bulb", {
            "command": "turn_on",
            "timestamp": timestamp,
            "duration": 10
        })

        print(f"[ILLUMINATOR AI] Bulb triggered with threat score {threat_score:.2f}")
