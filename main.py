import threading
from sensors import gps_sensor, camera_sensor
from ai import ai_controller
import time

def safe_start(name, func):
    try:
        print(f"🧵 Starting {name} listener thread...")
        func()
    except Exception as e:
        print(f"❌ {name} thread crashed: {e}")

def main():
    gps_thread = threading.Thread(target=lambda: safe_start("GPS", gps_sensor.start_gps_listener))
    cam_thread = threading.Thread(target=lambda: safe_start("Camera", camera_sensor.start_camera_listener))
    ai_thread  = threading.Thread(target=lambda: safe_start("AI", ai_controller.start_ai_listener))

    gps_thread.start()
    time.sleep(1)
    cam_thread.start()
    time.sleep(1)
    ai_thread.start()

    gps_thread.join()
    cam_thread.join()
    ai_thread.join()

if __name__ == "__main__":
    main()
