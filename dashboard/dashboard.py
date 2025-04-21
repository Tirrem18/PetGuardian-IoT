import streamlit as st
import folium
from streamlit_folium import st_folium

# --- Set Streamlit config ---
st.set_page_config(page_title="PetGuardian Dashboard", layout="wide")
st.title("🐾 PetGuardian IoT Dashboard")

# --- Default values ---
DEFAULT_LAT, DEFAULT_LON, DEFAULT_RADIUS = 54.5742, -1.2345, 30

# --- Session state defaults ---
state_defaults = {
    "home_lat": DEFAULT_LAT,
    "home_lon": DEFAULT_LON,
    "safe_radius": DEFAULT_RADIUS,
    "threat_enabled": False,
    "night_enabled": False,
    "cooldown": 30,
    "sound_window": 10,
    "min_sounds": 3,
    "min_interval": 1.0,
    "lux_threshold": 30,
    "imu_threshold": 0.5
}
for key, val in state_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- Layout: 2 columns ---
left_col, right_col = st.columns([2.5, 1.5])

# === LEFT COLUMN ===
with left_col:
    with st.container():
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

# === RIGHT COLUMN ===
with right_col:
    with st.container():
        st.markdown("### 🧠 Enable Threat Detector")
        st.session_state.threat_enabled = st.toggle("Threat Detection", value=st.session_state.threat_enabled, key="threat_toggle")

        with st.expander("Threat Settings"):
            st.session_state.cooldown = st.slider("Cooldown Between Triggers (s)", 0, 60, st.session_state.cooldown)
            st.session_state.sound_window = st.slider("Sound Window (s)", 5, 30, st.session_state.sound_window)
            st.session_state.min_sounds = st.slider("Min Sounds to Trigger", 1, 5, st.session_state.min_sounds)
            st.session_state.min_interval = st.slider("Min Interval Between Sounds (s)", 0.5, 5.0, st.session_state.min_interval)

    st.markdown(" ")  # spacer between sections

    with st.container():
        st.markdown("### 🌙 Enable Nighttime Safety Mode")
        st.session_state.night_enabled = st.toggle("Night Mode", value=st.session_state.night_enabled, key="night_toggle")

        with st.expander("Nighttime Settings"):
            st.session_state.lux_threshold = st.slider("Lux Threshold (Darkness)", 1, 100, st.session_state.lux_threshold)
            st.session_state.imu_threshold = st.slider("IMU Movement Threshold", 0.1, 5.0, st.session_state.imu_threshold)
