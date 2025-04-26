import streamlit as st
from dashboard_data import fetch_all_logs
from datetime import datetime
import base64

# --- Page Setup ---
st.set_page_config(page_title="Sensor Logs", layout="wide")
st.title("PetGuardian - All Sensor Logs")

# Date Filter
st.markdown("####  Filter logs by date")
selected_date = st.date_input(" ", label_visibility="collapsed")

# Fetch logs
logs = fetch_all_logs()

# UI separator
st.markdown("---")
st.markdown("Below are all logs retrieved from Cosmos DB, grouped by sensor type:")

# --- Render logs grouped ---
for sensor, all_entries in logs.items():
    filtered = []
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

    with st.expander(f"{sensor.capitalize()} Logs ({len(filtered)})", expanded=False):
        if not filtered:
            st.info("No logs found for this sensor on selected date.")
        else:
            for i, log in enumerate(filtered, start=1):
                st.markdown(f"---\n#### Entry {i} — `{log.get('timestamp', 'Unknown')}`")
                for key, val in log.items():
                    if key == "image_base64" and val != "no_image":
                        try:
                            st.image(base64.b64decode(val), caption="Camera Snapshot", use_container_width=True)
                        except:
                            st.warning("Could not render image.")
                    elif key != "image_base64":
                        st.markdown(f"- **{key.replace('_', ' ').capitalize()}:** `{val}`")
