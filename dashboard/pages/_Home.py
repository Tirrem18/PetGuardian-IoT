import streamlit as st
import folium
from streamlit_folium import st_folium
from dashboard_data import load_dashboard_settings, DEFAULTS, save_dashboard_settings
from dashboard.tools.threat_dummy import get_most_recent_threat


# --- Page setup ---
st.set_page_config(page_title="PetGuardian Dashboard", layout="wide")
st.title("🐾 PetGuardian IoT Dashboard")

# --- Load settings from database/backend ---
initial_settings = load_dashboard_settings()
for key, val in initial_settings.items():
    if key not in st.session_state:
        st.session_state[key] = val
    else:
        # Force correct types
        if key in ["home_lat", "home_lon"]:
            st.session_state[key] = float(st.session_state[key])
        elif key in ["safe_radius", "cooldown", "sound_window", "min_sounds", "min_interval", "lux_threshold", "imu_threshold"]:
            st.session_state[key] = int(float(st.session_state[key]))
        elif key in ["threat_enabled", "night_enabled"]:
            st.session_state[key] = bool(st.session_state[key])

# --- Layout: split columns ---
left_col, right_col = st.columns([2.5, 1.5])

# === LEFT COLUMN: Home Settings and Map ===
with left_col:
    st.markdown("### 🏠 Home Location and Safe Zone")

    # Render placeholder for map first (visually top)
    map_container = st.container()

    st.markdown("### ⚙️ Home Settings")
    with st.expander("Location Settings"):
        st.session_state.home_lat = st.number_input("Latitude", value=st.session_state.home_lat, format="%.6f", step=0.0001)
        st.session_state.home_lon = st.number_input("Longitude", value=st.session_state.home_lon, format="%.6f", step=0.0001)

    st.session_state.safe_radius = st.slider("Safe Radius (meters)", 10, 180, st.session_state.safe_radius)

    map_center = st.session_state.get("_map_center", (st.session_state.home_lat, st.session_state.home_lon))


    # Now render the map *after* slider so it gets correct radius
    with map_container:
        # Create base map
        m = folium.Map(location=(st.session_state.home_lat, st.session_state.home_lon), zoom_start=17)

        # Add home marker
        folium.Marker(
            location=(st.session_state.home_lat, st.session_state.home_lon),
            popup="Home",
            icon=folium.Icon(color="green", icon="home")
        ).add_to(m)

        # Add safe zone
        folium.Circle(
            radius=st.session_state.safe_radius,
            location=(st.session_state.home_lat, st.session_state.home_lon),
            popup="Safe Zone",
            color="green",
            fill=True,
            fill_opacity=0.3
        ).add_to(m)

        # ✅ Add a static red dot (no function call at all)
        folium.CircleMarker(
            location=(54.5749, -1.2349),  # Hardcoded test
            radius=7,
            color='red',
            fill=True,
            fill_color='red',
            fill_opacity=1.0,
            tooltip="⚠️ Test Dot"
        ).add_to(m)

        # Always show the map
        st_folium(m, width=1500, height=450)



# === RIGHT COLUMN: Features ===
with right_col:
    st.markdown("### 🧠 Enable Threat Detector")
    st.session_state.threat_enabled = st.toggle("Threat Detection", value=st.session_state.threat_enabled, key="threat_toggle")

    with st.expander("Threat Settings"):
        st.session_state.cooldown = st.slider("Cooldown Between Triggers (s)", 0, 60, st.session_state.cooldown)
        st.session_state.sound_window = st.slider("Sound Window (s)", 5, 60, st.session_state.sound_window)
        st.session_state.min_sounds = st.slider("Min Sounds to Trigger", 1, 10, st.session_state.min_sounds)
        st.session_state.min_interval = st.slider("Min Interval Between Sounds (s)", 1, 10, st.session_state.min_interval)

    st.markdown(" ")  # Spacer

    st.markdown("### 🌙 Enable Nighttime Safety Mode")
    st.session_state.night_enabled = st.toggle("Night Mode", value=st.session_state.night_enabled, key="night_toggle")

    with st.expander("Nighttime Settings"):
        st.session_state.lux_threshold = st.slider("Lux Threshold (Darkness)", 1, 100, st.session_state.lux_threshold)
        st.session_state.imu_threshold = st.slider("IMU Movement Threshold", 1, 10, st.session_state.imu_threshold)

# === Save and Reset Buttons ===
with st.container():
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Save Settings to Cosmos"):
            updated_settings = {
                "home_lat": float(st.session_state.home_lat),
                "home_lon": float(st.session_state.home_lon),
                "safe_radius": int(st.session_state.safe_radius),
                "cooldown": int(st.session_state.cooldown),
                "sound_window": int(st.session_state.sound_window),
                "min_sounds": int(st.session_state.min_sounds),
                "min_interval": int(st.session_state.min_interval),
                "lux_threshold": int(st.session_state.lux_threshold),
                "imu_threshold": int(st.session_state.imu_threshold),
                "threat_enabled": bool(st.session_state.threat_enabled),
                "night_enabled": bool(st.session_state.night_enabled)
            }
            success = save_dashboard_settings(updated_settings)
            if success:
                st.success("Settings saved to Cosmos!")
            else:
                st.error("Failed to save settings. Check console for errors.")

    with col2:
        if st.button("🧼 Reset to Defaults"):
            for key, val in DEFAULTS.items():
                st.session_state[key] = val
            st.rerun()
