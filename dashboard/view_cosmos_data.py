import base64
import json
from azure.cosmos import CosmosClient

# Cosmos DB connection
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

# Connect to Cosmos DB
client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

print(f"✅ Connected to Cosmos DB - DB: {DATABASE_NAME}, Container: {CONTAINER_NAME}")
print("🔎 Retrieving and decoding data from Cosmos DB...\n")

items_found = False

# Query and process all items
for item in container.query_items(query="SELECT * FROM c", enable_cross_partition_query=True):
    items_found = True
    base64_body = item.get("Body")

    if base64_body:
        try:
            decoded_json = json.loads(base64.b64decode(base64_body).decode("utf-8"))
            sensor_type = decoded_json.get("sensor")
            timestamp = decoded_json.get("timestamp", "N/A")

            if sensor_type == "acoustic":
                event = decoded_json.get("event", "unknown_event")
                print(f"📅 {timestamp} | 🔊 Event: {event} | 🎙️ Sensor: Acoustic")
            elif sensor_type == "gps":
                lat = decoded_json.get("latitude", "N/A")
                lon = decoded_json.get("longitude", "N/A")
                print(f"📅 {timestamp} | 🛰️ GPS Location: ({lat}, {lon})")
            else:
                print(f"📅 {timestamp} | ❓ Unknown sensor type: {sensor_type}")
        except Exception as e:
            print(f"⚠️ Error decoding message: {e}")
    else:
        print("⚠️ No 'Body' field found in this item.")

if not items_found:
    print("🚫 No items found in the container.")
