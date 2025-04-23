# pages/2_Logs.py

import streamlit as st
from dashboard_data import fetch_all_logs

# Page config
st.set_page_config(page_title="📚 Sensor Logs", layout="wide")
st.title("📚 PetGuardian - All Sensor Logs")

# Fetch logs from Cosmos DB
logs = fetch_all_logs()

# Description
st.markdown("Below are all logs retrieved from Cosmos DB, grouped by sensor type:")

# Loop through each sensor category and display logs in dropdowns
for sensor, entries in logs.items():
    with st.expander(f"🔍 {sensor.capitalize()} Logs ({len(entries)})"):
        if entries:
            for log in entries:
                st.markdown(f"- {log}")
        else:
            st.write("No entries found.")
