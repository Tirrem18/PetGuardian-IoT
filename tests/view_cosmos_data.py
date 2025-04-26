import base64
import json
import os
from azure.cosmos import CosmosClient
from datetime import datetime

# Configuration for connecting to Azure Cosmos DB
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

# Folder path for saving camera images
IMAGE_DIR = os.path.join("..", "data", "images")
os.makedirs(IMAGE_DIR, exist_ok=True)

# Connect to Cosmos DB and access the telemetry container
client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

print(f"Connected to Cosmos DB - Database: {DATABASE_NAME}, Container: {CONTAINER_NAME}")
print("Retrieving and decoding telemetry data...\n")

items_found = False  # Flag to track if any items were retrieved
printed_events = set()  # To track and skip duplicates

# Query all telemetry entries in the container
for item in container.query_items(query="SELECT * FROM c", enable_cross_partition_query=True):
    items_found = True

    try:
        body_encoded = item.get("Body", "")
        if not body_encoded.strip():
            print("Skipping item with empty Body field.")
            continue

        try:
            body_json = base64.b64decode(body_encoded).decode("utf-8")
            body_decoded = json.loads(body_json)
        except Exception as decode_err:
            print(f"Invalid Body format: {decode_err}")
            continue

        sensor_type = body_decoded.get("sensor", "unknown")
        event_type = body_decoded.get("event", "none")
        timestamp = body_decoded.get("timestamp", item.get("timestamp", "N/A"))

        # Create a unique event ID to detect duplicates
        event_id = f"{timestamp}_{sensor_type}_{event_type}"

        if event_id in printed_events:
            continue  # Skip already printed event
        printed_events.add(event_id)

        # Handle acoustic sensor data
        if sensor_type == "acoustic":
            event = body_decoded.get("event", "unknown_event")
            print(f"{timestamp} | Acoustic Event: {event}")

        elif sensor_type == "bulb":
            event = body_decoded.get("event", "unknown_event")
            print(f"{timestamp} | Bulb Event: {event}")

        # Handle GPS sensor data
        elif sensor_type == "gps":
            lat = body_decoded.get("latitude", "N/A")
            lon = body_decoded.get("longitude", "N/A")
            print(f"{timestamp} | GPS Location: ({lat}, {lon})")

        # Handle light sensor data
        elif sensor_type in ["light", "led_light_sensor", "simulated_led_light"]:
            lux = body_decoded.get("lux", "N/A")
            print(f"{timestamp} | Light Level: {lux} lux | Sensor Type: {sensor_type}")

        # Handle camera image data
        elif sensor_type == "camera":
            image_data = body_decoded.get("image_base64")
            if image_data:
                image_bytes = base64.b64decode(image_data)
                filename = f"camera_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                file_path = os.path.join(IMAGE_DIR, filename)

                with open(file_path, "wb") as img_file:
                    img_file.write(image_bytes)

                print(f"{timestamp} | Image saved: {file_path}")
            else:
                print(f"{timestamp} | Camera data found but missing 'image_base64' field.")

        # Handle threat event data
        elif event_type == "threat":
            score = body_decoded.get("score", "N/A")
            gps_latitude = body_decoded.get("gps_latitude", "N/A")
            gps_longitude = body_decoded.get("gps_longitude", "N/A")
            reason = body_decoded.get("reason", "N/A")

            print(f"{timestamp} | 🚨 Threat Event Detected! Score: {score}, Location: ({gps_latitude}, {gps_longitude}), Reason: {reason}")

        # Handle unknown sensor types
        else:
            print(f"{timestamp} | Unknown sensor type: {sensor_type}. Full event data:")
            for key, value in body_decoded.items():
                print(f"    {key}: {value}")

    except Exception as e:
        print(f"Error processing item: {e}")

# If no telemetry items were found in the database
if not items_found:
    print("No telemetry items found in the container.")
