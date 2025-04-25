import sys
import time
import os
import json
from math import radians, cos, sin, sqrt, atan2
from ai.old.threat_uploader_test import send_threat_to_cosmos, send_threat_to_azure

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sensors.camera_sensor import trigger_camera

class ThreatDetector:
    def __init__(self, home_location=None, safe_radius=30, threat_cooldown_seconds=30,
                 sound_window=10, min_sounds=3, min_sound_interval=1,
                 threat_enabled=True):
        """
        Initializes the threat detection system.
        """
        self.home_location = home_location
        self.safe_radius = safe_radius
        self.threat_cooldown_seconds = threat_cooldown_seconds
        self.sound_window = sound_window
        self.min_sounds = min_sounds
        self.min_sound_interval = min_sound_interval
        self.threat_enabled = threat_enabled

        self.sound_timestamps = []       # List of timestamps for recent sounds
        self.latest_gps = None           # Most recent GPS reading (lat, lon)
        self.last_trigger_time = 0       # Time of last confirmed threat
        self.awaiting_gps = False        # Set to True after sound spike detected
        self.awaiting_gps_since = None   # Time GPS was first requested

    def handle(self, payload):
        """
        Main handler called by ai_controller.py.
        """
        if not self.threat_enabled:
            print("⚠️ Threat detection is OFF — ignoring incoming sensor data.")
            return False

        # Check for GPS timeout
        if self.awaiting_gps_since and time.time() - self.awaiting_gps_since > 15:
            print("⏱️ GPS timeout — no fix received within 15 seconds. Assuming pet is outside zone.")
            self.awaiting_gps = False
            self.awaiting_gps_since = None
            self.latest_gps = None  # Will log "unknown"
            self._trigger_threat_response()
            self.sound_timestamps.clear()
            self.last_trigger_time = time.time()
            return "threat_triggered"

        sensor_type = payload.get("sensor")

        if sensor_type == "acoustic":
            return self._handle_sound(payload.get("timestamp"))
        elif sensor_type == "gps":
            return self._handle_gps(payload.get("latitude"), payload.get("longitude"))

        return False

    def _handle_sound(self, timestamp):
        """
        Handle incoming sound. If threshold reached, request GPS.
        """
        now = time.time()

        if self.min_sounds > 1 and self.sound_timestamps:
            time_since_last = now - self.sound_timestamps[-1]
            if time_since_last < self.min_sound_interval:
                return False  # Skip sound if too close

        self.sound_timestamps.append(now)
        self.sound_timestamps = [t for t in self.sound_timestamps if now - t <= self.sound_window]

        if len(self.sound_timestamps) >= self.min_sounds:
            if now - self.last_trigger_time >= self.threat_cooldown_seconds:
                self.awaiting_gps = True
                self.awaiting_gps_since = now
                print("📡 Sound spike detected — awaiting GPS position.")
                return "awaiting_gps"

        return False

    def _handle_gps(self, lat, lon):
        """
        GPS received. If awaiting, confirm threat based on zone.
        """
        try:
            self.latest_gps = (float(lat), float(lon))
        except (TypeError, ValueError):
            self.latest_gps = None
            print("⚠️ Invalid GPS received — assuming outside zone.")
            return False

        if not self.awaiting_gps:
            return False

        self.awaiting_gps = False
        self.awaiting_gps_since = None
        now = time.time()

        outside_zone = True
        if self.home_location and self.latest_gps:
            outside_zone = self._is_outside_safe_zone()

        if self.home_location and not outside_zone:
            print("✅ Inside safe zone. No threat.")
            self.sound_timestamps.clear()
            return False

        self._trigger_threat_response()
        self.sound_timestamps.clear()
        self.last_trigger_time = now
        return "threat_triggered"

    def _is_outside_safe_zone(self):
        """
        Calculates GPS distance using haversine.
        """
        lat1, lon1 = self.latest_gps
        lat2, lon2 = self.home_location
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = 6371000 * c
        return distance > self.safe_radius

    def _trigger_threat_response(self):
        """
        Log threat + print summary.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        gps = self.latest_gps if self.latest_gps else ("unknown", "unknown")

        # 👉 Build reason before clearing timestamps
        sound_count = len(self.sound_timestamps)
        reason_text = f"{sound_count} sound event{'s' if sound_count != 1 else ''} within {self.sound_window} seconds"

        log_entry = {
            "timestamp": timestamp,
            "gps_latitude": gps[0],
            "gps_longitude": gps[1],
            "reason": reason_text
        }

        # Save locally
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(base_dir, "data", "logs")
        log_path = os.path.join(log_dir, "threat_log.json")

        os.makedirs(log_dir, exist_ok=True)

        try:
            if os.path.exists(log_path) and os.path.getsize(log_path) > 0:
                with open(log_path, "r") as file:
                    logs = json.load(file)
                if not isinstance(logs, list):
                    logs = []
            else:
                logs = []
        except Exception:
            logs = []

        logs.append(log_entry)
        with open(log_path, "w") as file:
            json.dump(logs, file, indent=4)

        # ✅ Send with actual values
        send_threat_to_cosmos(timestamp, gps, reason_text)
        send_threat_to_azure(timestamp, gps, reason_text)

        print("\n⚠️ THREAT DETECTED!")
        print(f"- Time: {timestamp}")
        print(f"- Location: {gps}")
        print(f"- Reason: {reason_text}")
