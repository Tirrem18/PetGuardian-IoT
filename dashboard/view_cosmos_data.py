import base64
import json
import os
from azure.cosmos import CosmosClient
from datetime import datetime

# Cosmos DB connection
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

# Create image output folder if it doesn't exist
os.makedirs("images", exist_ok=True)

# Connect to Cosmos DB
client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

print(f"✅ Connected to Cosmos DB - DB: {DATABASE_NAME}, Container: {CONTAINER_NAME}")
print("🔎 Retrieving and decoding telemetry data...\n")

items_found = False

# Query and process all telemetry items
for item in container.query_items(query="SELECT * FROM c", enable_cross_partition_query=True):
    items_found = True

    try:
        # Decode base64 Body field
        body_encoded = item.get("Body", "")
        body_decoded = json.loads(base64.b64decode(body_encoded).decode('utf-8'))

        sensor_type = body_decoded.get("sensor", "unknown")
        timestamp = body_decoded.get("timestamp", item.get("timestamp", "N/A"))

        if sensor_type == "acoustic":
            event = body_decoded.get("event", "unknown_event")
            print(f"📅 {timestamp} | 🔊 Acoustic Event: {event}")

        elif sensor_type == "gps":
            lat = body_decoded.get("latitude", "N/A")
            lon = body_decoded.get("longitude", "N/A")
            print(f"📅 {timestamp} | 🛰️ GPS Location: ({lat}, {lon})")

        elif sensor_type in ["light", "led_light_sensor", "simulated_led_light"]:
            lux = body_decoded.get("lux", "N/A")
            print(f"📅 {timestamp} | 💡 Light Level: {lux} lux | Sensor: {sensor_type}")

        elif sensor_type == "camera":
            image_data = body_decoded.get("image_base64")
            if image_data:
                image_bytes = base64.b64decode(image_data)
                filename = f"images/camera_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                with open(filename, "wb") as img_file:
                    img_file.write(image_bytes)
                print(f"📅 {timestamp} | 📸 Camera Image Saved: {filename}")
            else:
                print(f"📅 {timestamp} | 📸 Camera sensor data found but no 'image_base64' field.")

        else:
            print(f"📅 {timestamp} | ❓ Unknown sensor type: {sensor_type}")

    except Exception as e:
        print(f"⚠️ Error processing item: {e}")

if not items_found:
    print("🚫 No telemetry items found in the container.")
