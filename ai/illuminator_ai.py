import json
import time
import math
from ai.utils.ai_utils import AIUtils

class IlluminatorAI:
    def __init__(self, client_id="illuminator_core"):
        self.ai = AIUtils(client_id=client_id)
        print(f"[ILLUMINATOR AI] Using client_id: {client_id}")

        # --- Load Config ---
        self.config = self.fetch_config_from_cosmos()

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
        self.home_radius = self.config["home_radius"]
        self.gps_weight_multiplier = self.config["gps_weight_multiplier"]

        # --- Cached Sensor Data ---
        self.pending_illumination = None
        self.last_velocity = None
        self.last_lux = None
        self.last_gps = None
        self.gps_wait_start = 0
        self.last_gps_check_time = 0
        self.last_bulb_trigger_time = 0

        print("[ILLUMINATOR AI] ✅ IlluminatorAI initialized.")

    def fetch_config_from_cosmos(self):
        print("[CONFIG] Loaded illuminator AI parameters (static fallback).")
        return {
            "velocity_threshold": 0.5,
            "velocity_risk_cap": 4,
            "lux_threshold": 200,
            "lux_risk_cap": 4,
            "gps_safe_radius": 30,
            "gps_risk_cap": 3,
            "mini_risk_threshold": 4.1,
            "full_risk_threshold": 6.5,
            "gps_wait_duration": 10,
            "bulb_cooldown": 5,
            "home_lat": 54.5742,
            "home_lon": -1.2345,
            "home_radius": 30,
            "gps_weight_multiplier": 2
        }


    def handle_imu_event(self, payload):
        try:
            if "velocity" in payload:
                velocity = float(payload.get("velocity", 0))
            elif "accel_x" in payload and "accel_y" in payload and "accel_z" in payload:
                ax = float(payload.get("accel_x", 0))
                ay = float(payload.get("accel_y", 0))
                az = float(payload.get("accel_z", 0))
                velocity = math.sqrt(ax**2 + ay**2 + az**2) * 0.1  # Scaling factor
                print(f"[ILLUMINATOR AI] 🧮 Estimated velocity from accel: {velocity:.2f} m/s")
            else:
                velocity = 0
            
            self.last_velocity = velocity
            now = time.time()

            if velocity < self.velocity_threshold:
                print("[ILLUMINATOR AI] 🐢 Movement too slow. No Lux or GPS needed.")
                self.pending_illumination = None
                return

            print(f"[ILLUMINATOR AI] ⚡ Detected fast movement: {velocity:.2f} m/s ➔ Waiting for Lux reading...\n")
            self.send_lux_trigger()


        except Exception as e:
            print(f"[ILLUMINATOR AI] ⚠️ Failed to process IMU payload: {e}")

    def handle_lux_event(self, payload):
        try:
            lux = float(payload.get("lux", 1000))
            self.last_lux = lux
            now = time.time()

            if self.last_velocity is None:
                print("[ILLUMINATOR AI] 🚫 No velocity cached. Ignoring Lux event.\n")
                return

            velocity_risk = min((self.last_velocity / self.velocity_threshold) * 2, self.velocity_risk_cap)

            if lux >= 75:
                lux_risk = 0
            else:
                darkness_ratio = (75 - lux) / 74
                lux_risk = min(darkness_ratio * self.lux_risk_cap, self.lux_risk_cap)

            combined_risk = velocity_risk + lux_risk

            print(f"[ILLUMINATOR AI] 📊 Velocity Risk: {velocity_risk:.2f}, Lux Risk: {lux_risk:.2f} ➔ Combined: {combined_risk:.2f}")

            if combined_risk < self.mini_risk_threshold:
                print("[ILLUMINATOR AI] 🔵 Combined risk too low. No GPS ping needed.")
                self.pending_illumination = None
                return

            # Only if risk is high enough:
            self.pending_illumination = {
                "velocity_risk": velocity_risk,
                "lux_risk": lux_risk,
                "timestamp": now
            }
            self.gps_wait_start = now
            self.send_gps_trigger()

        except Exception as e:
            print(f"[ILLUMINATOR AI] ⚠️ Failed to process Lux payload: {e}")


    def handle_gps_event(self, payload):
        try:
            lat = float(payload.get("latitude"))
            lon = float(payload.get("longitude"))
            now = time.time()

            self.last_gps = {
                "latitude": lat,
                "longitude": lon,
                "timestamp": now
            }
            print("[ILLUMINATOR AI] 🛰️ GPS location updated.")

            if not self.pending_illumination:
                print("[ILLUMINATOR AI] 🚫 No pending illumination event, ignoring GPS.")
                return

            self.evaluate_threat()

        except Exception as e:
            print(f"[ILLUMINATOR AI] ⚠️ Failed to process GPS payload: {e}")

    def evaluate_threat(self):
        try:
            now = time.time()
            pending = self.pending_illumination
            velocity_risk = pending.get("velocity_risk", 0)
            lux_risk = pending.get("lux_risk", 0)

            if self.last_gps is None:
                elapsed = now - self.gps_wait_start
                if elapsed > self.gps_wait_duration:
                    print("[ILLUMINATOR AI] ⏱ GPS timeout reached. Assuming max GPS risk.")
                    gps_risk = self.gps_risk_cap
                else:
                    print(f"[ILLUMINATOR AI] ⏳ Waiting for GPS... {elapsed:.1f}s\n")
                    return
            else:
                gps_risk = self.calculate_gps_risk(self.last_gps)

            total_score = round(velocity_risk + lux_risk + gps_risk, 2)

            print(f"[ILLUMINATOR AI] 📈 Total Threat Score: {total_score:.2f}")

            if total_score >= self.full_risk_threshold:
                self.trigger_illuminator(total_score)
            else:
                print("[ILLUMINATOR AI] 🔵 Threat score too low. No bulb activation.\n")

            self.pending_illumination = None

        except Exception as e:
            print(f"[ILLUMINATOR AI] ⚠️ Threat evaluation failed: {e}")

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
            distance = 6371000 * c  # meters

            print(f"[ILLUMINATOR AI] 📏 Distance from home: {distance:.2f}m")

            if distance <= self.gps_safe_radius:
                return 0

            gps_risk = ((distance - self.gps_safe_radius) / self.gps_safe_radius) * self.gps_weight_multiplier
            gps_risk = min(gps_risk, self.gps_risk_cap)
            return gps_risk

        except Exception as e:
            print(f"[ILLUMINATOR AI] ⚠️ GPS risk calculation failed: {e}")
            return self.gps_risk_cap

    def send_gps_trigger(self):
        print("[ILLUMINATOR AI] 🛰️ Sending GPS trigger...")
        for attempt in range(3):
            success = self.ai.publish("petguardian/trigger/gps", {
                "command": "get_gps",
                "timestamp": self.ai.get_timestamp()
            })
            if success:
                print("[ILLUMINATOR AI] ✅ GPS trigger published.")
                return
            time.sleep(0.5)
        print("[ILLUMINATOR AI] ❌ Failed to publish GPS trigger.")
        
        
    def send_lux_trigger(self):
        print("[ILLUMINATOR AI] 🔦 Sending Lux trigger...")
        for attempt in range(3):
            success = self.ai.publish("petguardian/trigger/lux", {
                "command": "get_lux",
                "timestamp": self.ai.get_timestamp()
            })
            if success:
                print("[ILLUMINATOR AI] ✅ Lux trigger published.\n")
                return
            time.sleep(0.5)
        print("[ILLUMINATOR AI] ❌ Failed to publish Lux trigger.")

    def trigger_illuminator(self, threat_score):
        now = time.time()
        if now - self.last_bulb_trigger_time < self.bulb_cooldown:
            print("[ILLUMINATOR AI] ⏸ Bulb cooldown active. Skipping activation.")
            return

        self.last_bulb_trigger_time = now
        timestamp = self.ai.get_timestamp()

        event = {
            "timestamp": timestamp,
            "event": "illumination",
            "score": threat_score,
            "reason": "Movement + Darkness + GPS risk exceeded threshold."
        }

        self.ai.log_locally("illumination_log.json", event)
        self.ai.send_to_azure(event)
        self.ai.send_to_cosmos(event, tag="ai")

        self.ai.publish("petguardian/trigger/bulb", {
            "command": "turn_on",
            "timestamp": timestamp,
            "duration": 10
        })

        print(f"\n[ILLUMINATOR AI] 💡 Bulb triggered with threat score {threat_score:.2f}\n")
