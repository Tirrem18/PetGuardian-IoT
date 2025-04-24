import base64
import json
import os
from datetime import datetime
from azure.cosmos import CosmosClient

# --- Cosmos Config ---
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

# --- Connect ---
client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

print("🔗 Connected to Cosmos. Fetching all threat logs...\n")

# --- Fetch + Decode ---
threat_count = 0

for item in container.query_items("SELECT * FROM c", enable_cross_partition_query=True):
    try:
        body_encoded = item.get("Body", "")
        if not body_encoded.strip():
            continue

        # Decode and parse base64 JSON
        decoded = json.loads(base64.b64decode(body_encoded).decode("utf-8"))

        if decoded.get("sensor") == "threat":
            threat_count += 1
            timestamp = decoded.get("timestamp", "N/A")
            reason = decoded.get("reason", "No reason provided")
            lat = decoded.get("gps_latitude", "N/A")
            lon = decoded.get("gps_longitude", "N/A")

            print(f"\n🧠 Threat #{threat_count}")
            print(f"🕒 {timestamp}")
            print(f"📍 Location: ({lat}, {lon})")
            print(f"📢 Reason: {reason}")

    except Exception as e:
        print(f"[Error] Skipping one item: {e}")

# --- Summary ---
if threat_count == 0:
    print("⚠️ No threat events found in the database.")
else:
    print(f"\n✅ Done. Total threats found: {threat_count}")
