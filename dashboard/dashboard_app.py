# dashboard_app.py

import streamlit as st

# Page settings
st.set_page_config(
    page_title="Pet Guardian AI - Home",
    page_icon="🐾",
    layout="centered"
)

# Main Title
st.title("🐾 Pet Guardian AI System")

# Subtitle
st.subheader("Welcome to the Pet Guardian Dashboard")

# Description
st.markdown("""
This is a **Streamlit-based dashboard** built for the **Pet Guardian IoT System**.

🔹 Monitor real-time sensor events (e.g., motion, light, GPS).  
🔹 View and analyse AI-generated threat and illumination logs.  
🔹 Visualize the status of the pet’s environment and safety decisions.

---
""")

# Key Features Section
st.header("🚀 Key Features")
st.markdown("""
- **Real-Time Monitoring**: Detect and respond to movement, sound, and GPS events.
- **Threat Detection**: Analyze multiple events (sound spikes, GPS) to trigger camera alerts.
- **Safe Movement Detection**: Illuminate the pet at night when movement and darkness are detected.
- **Cloud Integration**: Logs are saved to Azure CosmosDB and visualized here.
- **Customizable**: Easy to expand with more AI models or additional sensors.
""")

# Final note
st.info("Use the sidebar ➡️ to navigate between **Dashboard** and **Logs** pages.")

