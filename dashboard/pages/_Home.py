# pages/1_Home.py

import streamlit as st
import folium
from streamlit_folium import st_folium
from dashboard_data import load_dashboard_settings

# --- Page setup ---
st.set_page_config(page_title="PetGuardian Dashboard", layout="wide")
st.title("🐾 PetGuardian IoT Dashboard")

# --- Load settings from database/backend ---
initial_settings = load_dashboard_settings()
for key, val in initial_settings.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- Layout: split columns ---
left_col, right_col = st.columns([2.5, 1.5])

# === LEFT COLUMN: Map + Home Settings ===
with left_col:
    st.markdown("### 🏠 Home Location and Safe Zone")

    m = folium.Map(location=(st.session_state.home_lat, st.session_state.home_lon), zoom_start=17)
    folium.Marker(
        location=(st.session_state.home_lat, st.session_state.home_lon),
        popup="Home",
        icon=folium.Icon(color="green", icon="home")
    ).add_to(m)
    folium.Circle(
        radius=st.session_state.safe_radius,
        location=(st.session_state.home_lat, st.session_state.home_lon),
        popup="Safe Zone",
        color="green",
        fill=True,
        fill_opacity=0.3
    ).add_to(m)
    st_folium(m, width=1500, height=450)

    st.markdown("### ⚙️ Home Settings")
    with st.expander("Location Settings"):
        st.session_state.home_lat = st.number_input("Latitude", value=st.session_state.home_lat, format="%.6f", step=0.0001)
        st.session_state.home_lon = st.number_input("Longitude", value=st.session_state.home_lon, format="%.6f", step=0.0001)
    st.session_state.safe_radius = st.slider("Radius (meters)", 10, 180, st.session_state.safe_radius)

# === RIGHT COLUMN: Feature Toggles ===
with right_col:
    st.markdown("### 🧠 Enable Threat Detector")
    st.session_state.threat_enabled = st.toggle("Threat Detection", value=st.session_state.threat_enabled, key="threat_toggle")

    with st.expander("Threat Settings"):
        st.session_state.cooldown = st.slider("Cooldown Between Triggers (s)", 0, 60, st.session_state.cooldown)
        st.session_state.sound_window = st.slider("Sound Window (s)", 5, 30, st.session_state.sound_window)
        st.session_state.min_sounds = st.slider("Min Sounds to Trigger", 1, 5, st.session_state.min_sounds)
        st.session_state.min_interval = st.slider("Min Interval Between Sounds (s)", 0.5, 5.0, st.session_state.min_interval)

    st.markdown(" ")  # Spacer

    st.markdown("### 🌙 Enable Nighttime Safety Mode")
    st.session_state.night_enabled = st.toggle("Night Mode", value=st.session_state.night_enabled, key="night_toggle")

    with st.expander("Nighttime Settings"):
        st.session_state.lux_threshold = st.slider("Lux Threshold (Darkness)", 1, 100, st.session_state.lux_threshold)
        st.session_state.imu_threshold = st.slider("IMU Movement Threshold", 0.1, 5.0, st.session_state.imu_threshold)

