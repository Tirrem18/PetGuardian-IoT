# --- dashboard/logs_page.py ---

import streamlit as st
from datetime import datetime
import base64
import os
import sys

# --- Setup system path to find util folder ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from util.dashboard_data import DashboardData

# --- Streamlit Page Config ---
st.set_page_config(page_title="PetGuardian - All Logs", layout="wide")
st.title("🐾 PetGuardian - All Sensor Logs")

# --- Initialize Backend ---
data_handler = DashboardData()

# --- Load All Logs ---
logs = data_handler.fetch_all_logs()
camera_logs = data_handler.fetch_all_camera_logs()
logs["camera"] = camera_logs  # Merge camera logs into main dictionary

# --- Sensor Types to Display ---
sensor_types = ["threats", "illuminations", "camera", "bulb", "imu", "lux", "gps", "acoustic"]

# --- UI: Date Filter ---
st.markdown("#### Filter logs by date")
selected_date = st.date_input(" ", label_visibility="collapsed")

st.markdown("---")
st.markdown("### 📚 Logs grouped by Sensor Type")

# --- Main Display Loop ---
for sensor in sensor_types:
    all_entries = logs.get(sensor, [])
    filtered = []

    # Filter by selected date
    for entry in all_entries:
        timestamp = entry.get("timestamp", "")
        try:
            if selected_date:
                log_date = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").date()
                if log_date != selected_date:
                    continue
        except:
            continue
        filtered.append(entry)

    # Display entries
    with st.expander(f"**{sensor.capitalize()} Logs ({len(filtered)})**", expanded=False):
        if not filtered:
            st.info(f"No logs found for {sensor} on selected date.")
        else:
            for i, log in enumerate(filtered, start=1):
                st.markdown(f"---\n#### Entry {i} — `{log.get('timestamp', 'Unknown')}`")
                for key, val in log.items():
                    if key == "image_base64" and val != "no_image":
                        try:
                            image_bytes = base64.b64decode(val)
                            st.image(image_bytes, caption="Camera Snapshot", use_container_width=True)
                        except Exception:
                            st.warning("⚠️ Could not render image.")
                    elif key != "image_base64":
                        st.markdown(f"- **{key.replace('_', ' ').capitalize()}:** `{val}`")
