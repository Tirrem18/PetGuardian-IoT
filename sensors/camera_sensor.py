import os
import sys
import time
import uuid
import json
import base64
import threading

# Ensure clean imports by appending project root path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try both import styles for SensorUtils
try:
    from sensors.utils.sensor_utils import SensorUtils
except ModuleNotFoundError:
    from utils.sensor_utils import SensorUtils

# --- Mode Detection ---
INTERACTIVE_MODE = __name__ == "__main__"  # True if running manually
USE_REAL_CAMERA = os.getenv("CAMERA", "false").strip().lower() == "true"  # Read from .env whether real camera is used

# --- File Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Project root
LOG_DIR = os.path.join(BASE_DIR, "data", "logs")  # Directory for general logs
SAVE_DIR = os.path.join(LOG_DIR, "images")  # Directory to save captured images
TEST_DIR = os.path.join(BASE_DIR, "tests", "test_images")  # Directory containing test images

# Ensure all necessary directories exist
os.makedirs(SAVE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# --- Sensor Utilities ---
# Initialize SensorUtils instance for camera sensor
utils = SensorUtils(
    sensor_name="camera",
    topic_publish="petguardian/camera",
    topic_trigger="petguardian/trigger/camera"
)

# --- Check for Real Camera ---
# Try importing and initializing a real webcam camera
try:
    if USE_REAL_CAMERA:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            cap.release()
            REAL_CAMERA = True
            print("[INIT] Real webcam camera enabled.")
        else:
            raise Exception("No webcam found.")
    else:
        raise ImportError("Virtual camera mode forced")
except Exception as e:
    REAL_CAMERA = False
    print(f"[INIT] Virtual camera mode. Reason: {e}")

# --- Handle Camera Event ---
# Captures an image and processes it based on environment mode
def handle_camera_event(timestamp=None, filename=None):
    timestamp = timestamp or utils.get_timestamp()  # Generate current timestamp if missing
    filename = filename or f"{timestamp.replace(':', '-').replace(' ', '_')}.jpg"  # Default filename format
    image_path = os.path.join(SAVE_DIR, filename)

    # --- Handling different camera modes ---
    if INTERACTIVE_MODE and REAL_CAMERA:
        input("[INTERACTIVE] Press Enter to take webcam photo...")
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        if ret:
            cv2.imwrite(image_path, frame)
            print(f"[CAPTURED] Saved real webcam image: {image_path}")
        else:
            print("[ERROR] Failed to capture webcam image.")
            image_path = None

    elif INTERACTIVE_MODE and not REAL_CAMERA:
        print("[INTERACTIVE] Select test image: 1-Dog  2-Bike  3-Human")
        choice = input("Choice (1–3): ").strip()
        test_files = {"1": "dog.png", "2": "bike.png", "3": "human.png"}
        src = test_files.get(choice)
        if src:
            try:
                src_path = os.path.join(TEST_DIR, src)
                with open(src_path, "rb") as fsrc, open(image_path, "wb") as fdst:
                    fdst.write(fsrc.read())
                print(f"[SIM] Test image copied to: {image_path}")
            except Exception as e:
                print(f"[ERROR] Failed to copy test image: {e}")
                image_path = None
        else:
            print("[ERROR] Invalid choice.")
            image_path = None

    elif not INTERACTIVE_MODE and REAL_CAMERA:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        if ret:
            cv2.imwrite(image_path, frame)
            print(f"[CAPTURED] Auto webcam image: {image_path}")
        else:
            print("[ERROR] Auto webcam capture failed.")
            image_path = None

    else:
        print("\n[SIMULATION] No real camera detected. Using fallback image.")
        fallback_path = os.path.join(TEST_DIR, "no_camera.png")
        if os.path.exists(fallback_path):
            try:
                with open(fallback_path, "rb") as fsrc, open(image_path, "wb") as fdst:
                    fdst.write(fsrc.read())
                print(f"[SIM] Fallback image copied: {image_path}")
            except Exception as e:
                print(f"[ERROR] Failed to copy fallback image: {e}")
                image_path = None
        else:
            print("[ERROR] no_camera.png not found.")
            image_path = None

    # --- Log and Cloud Upload Process ---

    filename_only = os.path.basename(image_path) if image_path else "no_image"  # Extract filename

    # Encode image to base64 string if available
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode()
    else:
        image_base64 = "no_image"

    # Build payload with sensor and image metadata
    data = {
        "sensor": "camera",
        "timestamp": timestamp,
        "image_file": filename_only,
        "image_base64": image_base64
    }

    # Save lightweight local log with filename only
    utils.log_locally("camera_log.json", {
        "sensor": "camera",
        "timestamp": timestamp,
        "image_file": filename_only
    })

    # Send full payload to MQTT broker, Azure IoT Hub, and Cosmos DB
    utils.send_to_mqtt(data)
    utils.send_to_azure(data)
    utils.send_to_cosmos(data)

# --- MQTT Trigger Listener ---
# Listens to MQTT trigger topic and handles incoming commands
def start_camera_listener():
    def on_camera_trigger(client, userdata, msg):
        print(f"[MQTT] Trigger received on {msg.topic}")
        try:
            payload = json.loads(msg.payload.decode())
            if payload.get("command") == "get_camera":
                timestamp = payload.get("timestamp") or utils.get_timestamp()
                filename = payload.get("filename")  # Supports specifying a filename if needed
                handle_camera_event(timestamp, filename)
        except Exception as e:
            print(f"[ERROR] Failed to handle trigger: {e}")

    utils.start_mqtt_listener(on_camera_trigger)

# --- Threaded entry for Guardian ---
# Starts the camera listener in a background thread
def start_camera_thread():
    thread = threading.Thread(target=start_camera_listener, name="CameraSensorThread", daemon=True)
    thread.start()

# --- Developer Test Mode ---
# Allows manual testing of camera capture when running this script directly
if __name__ == "__main__":
    utils.mqtt_client.connect(utils.broker, utils.port, 60)  # Connect to MQTT broker
    utils.mqtt_client.loop_start()  # Start MQTT loop
    print("[MQTT] Camera sensor connected and waiting.")

    print("[INTERACTIVE] Type 'C' to capture an image, or 'X' to exit.")
    try:
        while True:
            cmd = input(">>> ").strip().lower()
            if cmd == "c":
                handle_camera_event()
            elif cmd == "x":
                print("[EXIT] Exiting camera test mode.")
                break
            else:
                print("[INFO] Type 'C' to capture an image, or 'X' to exit interactive mode.")
    except KeyboardInterrupt:
        print("\n[EXIT] Camera interactive loop interrupted.")
