import streamlit as st
import folium
from streamlit_folium import st_folium
import sys, os
import base64
import json
from datetime import datetime
from azure.cosmos import CosmosClient

# Allow importing dashboard_data
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from dashboard_data import load_dashboard_settings, DEFAULTS, save_dashboard_settings


# --- Fetch Most Recent Threat from Cosmos ---
# Cosmos DB Config
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

def get_all_valid_threats():
    try:
        client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
        db = client.get_database_client(DATABASE_NAME)
        container = db.get_container_client(CONTAINER_NAME)

        valid_threats = []

        for item in container.query_items("SELECT * FROM c", enable_cross_partition_query=True):
            body_encoded = item.get("Body", "")
            if not body_encoded.strip():
                continue

            try:
                decoded = json.loads(base64.b64decode(body_encoded).decode("utf-8"))
            except Exception as decode_err:
                print(f"[❌] Decode error: {decode_err}")
                continue

            if decoded.get("sensor") != "threat":
                continue

            lat = decoded.get("gps_latitude")
            lon = decoded.get("gps_longitude")
            timestamp = decoded.get("timestamp", "Unknown")

            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and lat != 0 and lon != 0:
                valid_threats.append({
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "timestamp": timestamp,
                    "reason": decoded.get("reason", "Unknown")
                })

        return valid_threats

    except Exception as e:
        print(f"[🚨 COSMOS ERROR] {e}")
        return []


# --- Page setup ---
st.set_page_config(page_title="PetGuardian Dashboard", layout="wide")
st.title("🐾 PetGuardian IoT Dashboard")

# --- Load settings ---
initial_settings = load_dashboard_settings()
for key, val in initial_settings.items():
    if key not in st.session_state:
        st.session_state[key] = val
    else:
        if key in ["home_lat", "home_lon"]:
            st.session_state[key] = float(st.session_state[key])
        elif key in ["safe_radius", "cooldown", "sound_window", "min_sounds", "min_interval", "lux_threshold", "imu_threshold"]:
            st.session_state[key] = int(float(st.session_state[key]))
        elif key in ["threat_enabled", "night_enabled"]:
            st.session_state[key] = bool(st.session_state[key])

# --- Layout: split columns ---
left_col, right_col = st.columns([2.5, 1.5])

# === LEFT COLUMN: Map and Home Settings ===
with left_col:
    st.markdown("### 🏠 Home Location and Safe Zone")

    map_container = st.container()

    st.markdown("### ⚙️ Home Settings")
    with st.expander("Location Settings"):
        st.session_state.home_lat = st.number_input("Latitude", value=st.session_state.home_lat, format="%.6f", step=0.0001)
        st.session_state.home_lon = st.number_input("Longitude", value=st.session_state.home_lon, format="%.6f", step=0.0001)

    st.session_state.safe_radius = st.slider("Safe Radius (meters)", 10, 180, st.session_state.safe_radius)

    # Get latest threat from Cosmos
    all_threats = get_all_valid_threats()



    # --- Render Map ---
    with map_container:
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
        # Add ALL valid threats
        for threat in all_threats:
            folium.CircleMarker(
                location=(threat["latitude"], threat["longitude"]),
                radius=10,
                color='red',
                fill=True,
                fill_color='red',
                fill_opacity=1.0,
                tooltip=f"⚠️ {threat['timestamp']} – {threat['reason']}"
            ).add_to(m)


        st_folium(m, width=1500, height=450)


# === RIGHT COLUMN: AI Settings ===
with right_col:
    st.markdown("### 🧠 Enable Threat Detector")
    st.session_state.threat_enabled = st.toggle("Threat Detection", value=st.session_state.threat_enabled, key="threat_toggle")

    with st.expander("Threat Settings"):
        st.session_state.cooldown = st.slider("Cooldown Between Triggers (s)", 0, 60, st.session_state.cooldown)
        st.session_state.sound_window = st.slider("Sound Window (s)", 5, 60, st.session_state.sound_window)
        st.session_state.min_sounds = st.slider("Min Sounds to Trigger", 1, 10, st.session_state.min_sounds)
        st.session_state.min_interval = st.slider("Min Interval Between Sounds (s)", 1, 10, st.session_state.min_interval)

    st.markdown(" ")
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
