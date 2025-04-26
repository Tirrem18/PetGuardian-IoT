import json
import time
import math
from ai.utils.ai_utils import AIUtils

class ThreatAI:
    def __init__(self, client_id="threats_core"):
        self.ai = AIUtils(client_id=client_id)
        print(f"[THREAT AI] Using client_id: {client_id}")

        self.config = self.fetch_config_from_cosmos()
        self.acoustic_events = []
        self.last_gps = None
        self.last_trigger_time = 0
        self.last_gps_check_time = 0
        self.pending_threat = None
        self.gps_wait_start = 0
        self.gps_wait_duration = 10  # seconds

        self.cooldown = self.config["threat_cooldown"]
        self.gps_check_cooldown = self.config["gps_check_cooldown"]

        print("[THREAT AI] ✅ ThreatAI class initialized.")

    def fetch_config_from_cosmos(self):
        print("[CONFIG] Loaded threat AI parameters (static fallback).")
        return {
            "threat_threshold": 8.0,
            "sound_cap": 5,
            "point_per_sound": 2,
            "sound_decay_interval": 10.0,
            "threat_cooldown": 30,
            "gps_check_cooldown": 10,
            "home_lat": 54.5742,
            "home_lon": -1.2345,
            "home_radius": 30,
            "gps_cap": 10,
            "distance_per_point": 10
        }

    def handle_acoustic_event(self, payload):
        print("[THREAT AI] ⚡ Acoustic event received via MQTT")
        now = time.time()
        self.acoustic_events.append(now)

        max_event_age = self.config["sound_cap"] * self.config["sound_decay_interval"]
        self.acoustic_events = [t for t in self.acoustic_events if now - t <= max_event_age]

        if now - self.last_trigger_time < self.cooldown:
            print(f"[THREAT AI] Cooldown active ({self.cooldown}s). Skipping evaluation.")
            return

        self.evaluate_threat()

    def get_acoustic_score(self, now):
        score = 0
        for t in self.acoustic_events:
            decay = (now - t) / self.config["sound_decay_interval"]
            value = max(0, self.config["point_per_sound"] - decay)
            score += value
        capped_score = min(score, self.config["sound_cap"])
        print(f"[THREAT AI] Calculated acoustic score: {capped_score:.2f}")
        return capped_score

    def evaluate_threat(self):
        now = time.time()

        if self.pending_threat:
            try:
                acoustic_score = float(self.pending_threat["acoustic_score"])
            except (TypeError, ValueError):
                acoustic_score = self.get_acoustic_score(now)
        else:
            acoustic_score = self.get_acoustic_score(now)

        if float(acoustic_score) < float(self.config["sound_cap"]):
            print(f"[THREAT AI] Acoustic score {acoustic_score} < threshold.")
            return

        if self.last_gps is None:
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
                    print("[THREAT AI] ⏱ GPS timeout reached. Assuming max GPS risk.")
                    self.trigger_threat(acoustic_score + self.config["gps_cap"], acoustic_score)
                    self.pending_threat = None
                else:
                    print(f"[THREAT AI] ⏳ Waiting for GPS... {elapsed:.1f}s")
            return

        if now - self.last_gps_check_time < self.gps_check_cooldown:
            print("[THREAT AI] ⏸ GPS check cooldown active.")
            return

        self.last_gps_check_time = now
        gps_score = self.get_gps_risk_score(self.last_gps)
        total_score = round(float(acoustic_score) + gps_score, 2)

        if total_score >= self.config["threat_threshold"]:
            self.trigger_threat(total_score, acoustic_score)
            self.pending_threat = None
        else:
            print("[THREAT AI] 🔶 No threat triggered. Score below threshold.")

    def send_gps_trigger(self):
        print("[THREAT AI] 🛰️ Sending GPS trigger...")
        for attempt in range(5):
            success = self.ai.publish("petguardian/trigger/gps", {
                "command": "get_gps",
                "timestamp": self.ai.get_timestamp()
            })
            if success:
                print("[THREAT AI] ✅ GPS trigger published.")
                return
            time.sleep(0.5)
        print("[THREAT AI] ❌ All GPS trigger attempts failed.")

    def get_gps_risk_score(self, gps):
        try:
            lat1 = math.radians(gps["latitude"])
            lon1 = math.radians(gps["longitude"])
            lat2 = math.radians(self.config["home_lat"])
            lon2 = math.radians(self.config["home_lon"])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            distance = 6371000 * c
            print(f"[THREAT AI] GPS distance from home: {distance:.2f}m")
            if distance <= self.config["home_radius"]:
                return 0
            score = distance / self.config["distance_per_point"]
            return min(score, self.config["gps_cap"])
        except Exception as e:
            print(f"[THREAT AI] ❌ GPS scoring failed: {e}")
            return self.config["gps_cap"]

    def handle_gps_event(self, payload):
        try:
            self.last_gps = {
                "latitude": float(payload["latitude"]),
                "longitude": float(payload["longitude"]),
                "timestamp": time.time()
            }
            print("[THREAT AI] 🛰️ GPS location updated.")

            if self.pending_threat:
                gps_score = self.get_gps_risk_score(self.last_gps)
                acoustic_score = float(self.pending_threat["acoustic_score"])
                total_score = round(acoustic_score + gps_score, 2)

                if total_score >= self.config["threat_threshold"]:
                    self.trigger_threat(total_score, acoustic_score)
                else:
                    print(f"[THREAT AI] 🔶 No threat triggered after GPS. Final score: {total_score}")

                self.pending_threat = None
            else:
                print("[THREAT AI] No pending threat active, skipping GPS handling.")
        except Exception as e:
            print(f"[THREAT AI] ⚠️ Invalid GPS payload: {e}")

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

        if gps_score != "unknown" and gps_score > 0:
            reason = f"Threat score exceeded {self.config['threat_threshold']} due to sound and unsafe GPS location"
        else:
            reason = f"Threat score exceeded {self.config['threat_threshold']} due to sound alone"

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

        self.ai.log_locally("threat_log.json", event)
        self.ai.send_to_azure(event)
        self.ai.send_to_cosmos(event, tag="ai")

        self.ai.publish("petguardian/ai/event", event)
        self.ai.publish("petguardian/trigger/camera", {
            "command": "get_camera",
            "timestamp": timestamp,
            "filename": photo_filename  # ✅ pass filename!
        })


        time.sleep(2)

        print(f"\n[THREAT AI] 🚨 Threat Details:")
        print(f"   - Acoustic score (sound only): {acoustic_score}")
        print(f"   - GPS risk score (location risk): {gps_score}")
        print(f"   - ➔ Total combined threat score: {score}")
        print(f"   - ➔ {reason}")

        time.sleep(1)

        print(f"\n[THREAT AI] 🚨 Threat Logged with following: {event}\n\n")
