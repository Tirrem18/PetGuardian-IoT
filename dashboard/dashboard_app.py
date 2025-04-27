# --- dashboard/dashboard_app.py ---

import streamlit as st
import folium
from streamlit_folium import st_folium
import base64
from datetime import datetime
import os
import sys

# --- Import DashboardData ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from util.dashboard_data import DashboardData

# --- Initialize backend ---
data_handler = DashboardData()

# --- Clean duplicates ONCE on first load ---
if "duplicates_cleaned" not in st.session_state:
    data_handler.clean_duplicate_logs()
    st.session_state.duplicates_cleaned = True

# --- Load settings and logs ---
initial_settings = data_handler.load_dashboard_settings()
logs = data_handler.fetch_all_logs()

threat_logs = data_handler.sort_events_by_time(logs["threats"])
illumination_logs = data_handler.sort_events_by_time(logs["illuminations"])
camera_logs = data_handler.fetch_all_camera_logs()

# --- Streamlit page config ---
st.set_page_config(page_title="PetGuardian IoT Dashboard", layout="wide")
st.title("🐾 PetGuardian IoT Dashboard")

# --- Initialize session state from settings ---
for key, val in initial_settings.items():
    if key not in st.session_state:
        st.session_state[key] = val


# --- Select a threat event ---
selected_data = None
if threat_logs:
    selected_threat = st.selectbox(
        "Select a Threat Event:",
        options=[f"{t['timestamp']} – {t.get('reason', 'No Reason')}" for t in threat_logs],
        index=0,
        key="threat_selectbox"
    )
    selected_data = threat_logs[
        [f"{t['timestamp']} – {t.get('reason', 'No Reason')}" for t in threat_logs].index(selected_threat)
    ]

# --- Layout split into two columns ---
left_col, right_col = st.columns([2.5, 1.5])

# ========== LEFT COLUMN ==========
with left_col:
    # --- Threat Overview Map ---
    st.markdown("### 🛡️ Threat Overview")
    with st.container():
        m = folium.Map(location=(st.session_state.home_lat, st.session_state.home_lon), zoom_start=17)

        # Home marker
        folium.Marker(
            location=(st.session_state.home_lat, st.session_state.home_lon),
            popup="Home",
            icon=folium.Icon(color="green", icon="home")
        ).add_to(m)

        # Safe zone circle
        folium.Circle(
            radius=st.session_state.safe_radius,
            location=(st.session_state.home_lat, st.session_state.home_lon),
            popup="Safe Zone",
            color="green",
            fill=True,
            fill_opacity=0.3
        ).add_to(m)

        # Threat markers
        for threat in threat_logs:
            lat, lon = threat.get("gps_latitude"), threat.get("gps_longitude")
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                is_selected = selected_data and (threat.get("timestamp") == selected_data["timestamp"])
                if is_selected:
                    folium.CircleMarker(
                        location=(lat, lon),
                        radius=10,
                        color="black",
                        weight=3,
                        fill=True,
                        fill_color="red",
                        fill_opacity=1.0,
                        tooltip=f"SELECTED: {threat.get('timestamp', 'Unknown')}"
                    ).add_to(m)
                else:
                    folium.CircleMarker(
                        location=(lat, lon),
                        radius=8,
                        color="red",
                        fill=True,
                        fill_color="red",
                        fill_opacity=0.8,
                        tooltip=f"{threat.get('timestamp', 'Unknown')}: {threat.get('reason', 'No Reason')}"
                    ).add_to(m)

        st_folium(m, width=1400, height=700)

    # --- Home Location Settings ---
    st.markdown("### 🏡 Home Settings")
    with st.expander("Adjust Home Location Settings"):
        st.session_state.home_lat = st.number_input("Latitude", value=st.session_state.home_lat, format="%.6f")
        st.session_state.home_lon = st.number_input("Longitude", value=st.session_state.home_lon, format="%.6f")
        st.session_state.safe_radius = st.slider("Safe Radius (meters)", 10, 200, int(st.session_state.safe_radius))

    # --- Save and Reset Buttons ---
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Save Settings to Cosmos"):
            updated_settings = {key: st.session_state[key] for key in initial_settings.keys()}
            success = data_handler.save_dashboard_settings(updated_settings)
            if success:
                st.success("✅ Settings saved to Cosmos!")
            else:
                st.error("❌ Failed to save settings. Check console for errors.")

    with col2:
        if st.button("🔄 Reset Settings to Default"):
            for key, val in data_handler.DEFAULTS.items():
                st.session_state[key] = val
            st.success("✅ Settings reset to defaults. Click Save to apply to Cosmos!")
            st.rerun()

# ========== RIGHT COLUMN ==========
with right_col:
    # --- Threat Image Viewer ---
    st.markdown("### 📸 Threat Image Viewer")

    if selected_data:
        st.markdown(f"**Threat Time:** {selected_data['timestamp']}<br>**Reason:** {selected_data.get('reason', 'Unknown')}", unsafe_allow_html=True)

        matched_camera = data_handler.find_matching_camera_for_threat(selected_data["timestamp"], camera_logs)

        if matched_camera and matched_camera.get("image_base64"):
            try:
                image_bytes = base64.b64decode(matched_camera["image_base64"])
                st.image(image_bytes, caption=f"Matched Image: {matched_camera.get('filename', 'unknown')}", width=400)
            except Exception as e:
                st.error(f"⚠️ Failed to decode image: {e}")
        else:
            st.warning("⚠️ No matching camera image found for this threat event.")
    else:
        st.warning("⚠️ No threat events recorded yet.")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- System Modes ---
    st.markdown("### ⚙️ System Modes")
    st.session_state.threats_mode = st.toggle("Threat Detection Enabled", value=st.session_state.threats_mode)
    st.session_state.illumination_mode = st.toggle("Nighttime Safety Mode Enabled", value=st.session_state.illumination_mode)

    # --- Threat Detection Settings ---
    st.markdown("### 🎯 Threat Detection Settings")
    with st.expander("Adjust Threat AI Settings"):
        st.session_state.sound_cap = st.slider("Sound Cap", 1, 20, int(st.session_state.sound_cap))
        st.session_state.point_per_sound = st.slider("Points per Sound", 1, 10, int(st.session_state.point_per_sound))
        st.session_state.sound_decay_interval = st.slider("Sound Decay Interval (s)", 5.0, 30.0, float(st.session_state.sound_decay_interval), step=0.1)
        st.session_state.threat_threshold = st.slider("Threat Score Threshold", 1, 20, int(st.session_state.threat_threshold))
        st.session_state.threat_cooldown = st.slider("Threat Cooldown (s)", 5, 60, int(st.session_state.threat_cooldown))
        st.session_state.gps_check_cooldown = st.slider("GPS Check Cooldown (s)", 5, 60, int(st.session_state.gps_check_cooldown))
        st.session_state.distance_per_point = st.slider("Distance per Point (m)", 1, 50, int(st.session_state.distance_per_point))

    # --- Nighttime Illumination Settings ---
    st.markdown("### 🌙 Nighttime Illumination Settings")
    with st.expander("Adjust Night Mode Settings"):
        st.session_state.velocity_threshold = st.slider("Velocity Threshold (m/s)", 0.1, 5.0, float(st.session_state.velocity_threshold), step=0.1)
        st.session_state.velocity_risk_cap = st.slider("Velocity Risk Cap", 1, 10, int(st.session_state.velocity_risk_cap))
        st.session_state.lux_threshold = st.slider("Lux Threshold (Darkness)", 1, 500, int(st.session_state.lux_threshold))
        st.session_state.lux_risk_cap = st.slider("Lux Risk Cap", 1, 10, int(st.session_state.lux_risk_cap))
        st.session_state.gps_risk_cap = st.slider("GPS Risk Cap", 1, 10, int(st.session_state.gps_risk_cap))
        st.session_state.gps_weight_multiplier = st.slider("GPS Weight Multiplier", 1, 10, int(st.session_state.gps_weight_multiplier))
        st.session_state.mini_risk_threshold = st.slider("Mini Risk Threshold", 1.0, 10.0, float(st.session_state.mini_risk_threshold), step=0.1)
        st.session_state.full_risk_threshold = st.slider("Full Risk Threshold", 1.0, 10.0, float(st.session_state.full_risk_threshold), step=0.1)
        st.session_state.gps_wait_duration = st.slider("GPS Wait Duration (s)", 5, 30, int(st.session_state.gps_wait_duration))
        st.session_state.bulb_cooldown = st.slider("Bulb Cooldown (s)", 1, 60, int(st.session_state.bulb_cooldown))
