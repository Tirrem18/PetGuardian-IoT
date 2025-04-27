import json
import time
import math
import joblib
import numpy as np
from ai.utils.ai_utils import AIUtils
from dashboard.util.dashboard_data import DashboardData

# --- Threat Detection AI ---
class ThreatAI:
    def __init__(self, client_id="threats_core"):
        self.ai = AIUtils(client_id=client_id)
        print(f"[THREAT AI] Using client_id: {client_id}")
        self.model = joblib.load("ai/models/threat_model.pkl")


        # --- Load Configuration from DashboardData (Cosmos DB) ---
        self.config = DashboardData().load_dashboard_settings()

        # Threshold settings
        self.threat_threshold = self.config["threat_threshold"]
        self.sound_cap = self.config["sound_cap"]
        self.point_per_sound = self.config["point_per_sound"]
        self.sound_decay_interval = self.config["sound_decay_interval"]
        self.cooldown = self.config["threat_cooldown"]
        self.gps_check_cooldown = self.config["gps_check_cooldown"]
        self.home_lat = self.config["home_lat"]
        self.home_lon = self.config["home_lon"]
        self.safe_radius = self.config["safe_radius"]
        self.gps_risk_cap = self.config["gps_risk_cap"]
        self.distance_per_point = self.config["distance_per_point"]

        # Internal State
        self.acoustic_events = []
        self.last_gps = None
        self.last_trigger_time = 0
        self.last_gps_check_time = 0
        self.pending_threat = None
        self.gps_wait_start = 0
        self.gps_wait_duration = 10  # Seconds to wait for GPS after acoustic

        print("[THREAT AI] ThreatAI class initialized.")

    # --- Handle Incoming Acoustic Event ---
    def handle_acoustic_event(self, payload):
        print("[THREAT AI] Acoustic event received via MQTT")
        now = time.time()
        self.acoustic_events.append(now)

        max_event_age = self.sound_cap * self.sound_decay_interval
        self.acoustic_events = [t for t in self.acoustic_events if now - t <= max_event_age]

        if now - self.last_trigger_time < self.cooldown:
            print(f"[THREAT AI] Cooldown active ({self.cooldown}s). Skipping evaluation.")
            return

        self.evaluate_threat()

    # --- Calculate Acoustic Score ---
    def get_acoustic_score(self, now):
        score = 0
        for t in self.acoustic_events:
            decay = (now - t) / self.sound_decay_interval
            value = max(0, self.point_per_sound - decay)
            score += value

        print(f"[THREAT AI] Calculated acoustic score: {score:.2f}")
        return score

    # --- Evaluate Total Threat (Acoustic + GPS) ---
    def evaluate_threat(self):
        now = time.time()

        if self.pending_threat:
            try:
                acoustic_score = float(self.pending_threat["acoustic_score"])
            except (TypeError, ValueError):
                acoustic_score = self.get_acoustic_score(now)
        else:
            acoustic_score = self.get_acoustic_score(now)

        if float(acoustic_score) < float(self.sound_cap):
            print(f"[THREAT AI] Acoustic score {acoustic_score} below sound cap.")
            return

        if self.last_gps is None:
            # No GPS yet, request one
            if self.pending_threat is None:
                self.pending_threat = {
                    "acoustic_score": acoustic_score,
                    "timestamp": now
                }
                self.gps_wait_start = now
                self.send_gps_trigger()
            else:
                elapsed = now - self.gps_wait_start
                if elapsed > self.gps_wait_duration:
                    print("[THREAT AI] GPS timeout reached. Assuming max GPS risk.")
                    self.trigger_threat(acoustic_score + self.gps_risk_cap, acoustic_score)
                    self.pending_threat = None
                else:
                    print(f"[THREAT AI] Waiting for GPS response... {elapsed:.1f}s elapsed.")
            return

        if now - self.last_gps_check_time < self.gps_check_cooldown:
            print("[THREAT AI] GPS check cooldown active.")
            return

        self.last_gps_check_time = now
        gps_score = self.get_gps_risk_score(self.last_gps)
        total_score = round(float(acoustic_score) + gps_score, 2)

        # --- ML Model Prediction ---
        input_features = np.array([[acoustic_score, gps_score]])
        prediction = self.model.predict(input_features)

        if prediction[0] == 1:
            print("[THREAT AI] ML Model predicted THREAT.")
            self.trigger_threat(total_score, acoustic_score)
        else:
            print("[THREAT AI] ML Model predicted NO THREAT.")

    # --- Request New GPS Reading via MQTT ---
    def send_gps_trigger(self):
        print("[THREAT AI] Sending GPS trigger...")
        for attempt in range(5):
            success = self.ai.publish("petguardian/trigger/gps", {
                "command": "get_gps",
                "timestamp": self.ai.get_timestamp()
            })
            if success:
                print("[THREAT AI] GPS trigger published successfully.")
                return
            time.sleep(0.5)
        print("[THREAT AI] All GPS trigger attempts failed.")

    # --- Calculate GPS Risk Score ---
    def get_gps_risk_score(self, gps):
        try:
            lat1 = math.radians(gps["latitude"])
            lon1 = math.radians(gps["longitude"])
            lat2 = math.radians(self.home_lat)
            lon2 = math.radians(self.home_lon)

            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            distance = 6371000 * c  # Earth's radius in meters

            print(f"[THREAT AI] Distance from home: {distance:.2f}m")

            if distance <= self.safe_radius:
                print("[THREAT AI] Inside safe zone. GPS risk = 0.")
                return 0

            gps_risk = distance / self.distance_per_point
            capped_risk = min(gps_risk, self.gps_risk_cap)
            print(f"[THREAT AI] GPS Risk Score: {capped_risk:.2f}")
            return capped_risk

        except Exception as e:
            print(f"[THREAT AI] GPS risk calculation failed: {e}")
            return self.gps_risk_cap

    # --- Handle Incoming GPS Data ---
    def handle_gps_event(self, payload):
        try:
            self.last_gps = {
                "latitude": float(payload["latitude"]),
                "longitude": float(payload["longitude"]),
                "timestamp": time.time()
            }
            print("[THREAT AI] GPS location updated.")

            if self.pending_threat:
                gps_score = self.get_gps_risk_score(self.last_gps)
                acoustic_score = float(self.pending_threat["acoustic_score"])
                total_score = round(acoustic_score + gps_score, 2)

                print(f"[THREAT AI] Combined Score (Acoustic + GPS): {total_score:.2f}")

                if total_score >= self.threat_threshold:
                    self.trigger_threat(total_score, acoustic_score)
                else:
                    print("[THREAT AI] ML Model predicted NO THREAT after GPS update. No further action taken.")

                self.pending_threat = None
            else:
                print("[THREAT AI] No pending threat active, skipping GPS handling.")

        except Exception as e:
            print(f"[THREAT AI] Invalid GPS payload: {e}")

    # --- Trigger Final Threat Event ---
    def trigger_threat(self, score, acoustic_score=None):
        timestamp = self.ai.get_timestamp()
        gps_data = self.last_gps or {"latitude": "unknown", "longitude": "unknown"}
        gps = (gps_data["latitude"], gps_data["longitude"])

        self.last_trigger_time = time.time()

        if acoustic_score is None:
            acoustic_score = "unknown"

        if acoustic_score != "unknown":
            gps_score = round(score - acoustic_score, 2)
        else:
            gps_score = "unknown"

        if gps_score != "unknown" and gps_score > 0.3:
            reason = f"AI model predicted a threat based on sound and GPS risk."
        else:
            reason = f"AI model predicted a threat based on sound alone."


        photo_filename = f"{timestamp.replace(' ', '_').replace(':', '-')}.jpg"

        event = {
            "timestamp": timestamp,
            "event": "threat",
            "score": score,
            "gps_latitude": gps[0],
            "gps_longitude": gps[1],
            "reason": reason,
            "image_filename": photo_filename
        }

        # Log and upload event
        self.ai.log_locally("threat_log.json", event)
        self.ai.send_to_azure(event)
        self.ai.send_to_cosmos(event, tag="ai")

        # Publish event and trigger camera
        self.ai.publish("petguardian/ai/event", event)
        self.ai.publish("petguardian/trigger/camera", {
            "command": "get_camera",
            "timestamp": timestamp,
            "filename": photo_filename
        })

        time.sleep(2)

        print(f"\n[THREAT AI] Threat Details:")
        print(f"   - Acoustic score (sound): {acoustic_score}")
        print(f"   - GPS risk score (location risk): {gps_score}")
        print(f"   - ➔ Total combined threat score: {score}")
        print(f"   - ➔ {reason}")

        time.sleep(1)

        print(f"\n[THREAT AI] Threat logged and published:\n{event}\n")
