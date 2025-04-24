import base64
import json
from azure.cosmos import CosmosClient

# Cosmos DB config
COSMOS_URI = "https://petguardiandb.documents.azure.com:443/"
COSMOS_KEY = "gb0rv4z3It79ncyssNJmhHj8mDY8eUBcZPYBfACM9GPWXbf1m2IoIxDgwUQ7dcWfyUJOxUUnSncKACDb44Qynw=="
DATABASE_NAME = "iotdata"
CONTAINER_NAME = "telemetry"

# Sensors to delete
SENSOR_TYPES_TO_DELETE = {"acoustic", "gps", "lux", "imu", "camera", "threat"}

def cleanup_cosmos():
    print("[🔗] Connecting to Cosmos DB...")
    client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
    db = client.get_database_client(DATABASE_NAME)
    container = db.get_container_client(CONTAINER_NAME)
    print("[✅] Connected.")

    deleted_count = 0

    for item in container.query_items("SELECT * FROM c", enable_cross_partition_query=True):
        body_encoded = item.get("Body", "")
        if not body_encoded.strip():
            continue

        try:
            decoded = json.loads(base64.b64decode(body_encoded).decode("utf-8"))
            sensor_type = decoded.get("sensor")

            if sensor_type in SENSOR_TYPES_TO_DELETE:
                container.delete_item(item=item['id'], partition_key=item['deviceId'])
                print(f"[🗑️] Deleted item: {item['id']} ({sensor_type})")
                deleted_count += 1
        except Exception as e:
            print(f"[⚠️] Skipped item due to error: {e}")
            continue

    print(f"\n✅ Cleanup complete. Deleted {deleted_count} items.")

if __name__ == "__main__":
    cleanup_cosmos()