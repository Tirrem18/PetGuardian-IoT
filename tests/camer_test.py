# tests/view_camera_images.py

import streamlit as st
import base64
import json
import os
from azure.cosmos import CosmosClient
from datetime import datetime

# --- Cosmos Config ---
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

# --- Connect to Cosmos ---
client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

# --- Streamlit setup ---
st.set_page_config(page_title="Camera Image Viewer", layout="wide")
st.title("📷 PetGuardian - Camera Images from Cosmos")

# --- Fetch all camera images ---
@st.cache_data(show_spinner=True)
def fetch_camera_images():
    images = []
    try:
        for item in container.query_items(query="SELECT * FROM c", enable_cross_partition_query=True):
            try:
                body_encoded = item.get("Body", "")
                if not body_encoded.strip():
                    continue

                body_json = base64.b64decode(body_encoded).decode("utf-8")
                body_decoded = json.loads(body_json)

                if body_decoded.get("sensor") == "camera":
                    timestamp = body_decoded.get("timestamp", "unknown_time")
                    image_base64 = body_decoded.get("image_base64", None)

                    if image_base64:
                        images.append({
                            "timestamp": timestamp,
                            "image_base64": image_base64
                        })
            except Exception as e:
                print(f"[FETCH ERROR] {e}")
                continue
    except Exception as e:
        st.error(f"❌ Failed to connect or fetch from Cosmos: {e}")
    return images

# --- Load images ---
camera_images = fetch_camera_images()

if not camera_images:
    st.warning("⚠️ No camera images found in Cosmos.")
else:
    st.success(f"✅ Found {len(camera_images)} camera images.")

    for idx, img in enumerate(camera_images):
        st.markdown(f"### 🖼️ Image {idx + 1} – Captured at {img['timestamp']}")
        try:
            image_bytes = base64.b64decode(img["image_base64"])
            st.image(image_bytes, width=500)
        except Exception as e:
            st.error(f"⚠️ Failed to decode image {idx + 1}: {e}")

