from sensors.acoustic_sensor import detect_sound
from cloud.mqtt_publisher import send_data_to_cloud
from utils.logger import log_data
import time


def main():
    print("Starting Pet Guardian IoT System...")

    while True:
        sound = detect_sound()  # Runs real or simulated sensor

        print(f" Processed Sound Event: {sound}")
        
        print("\n🔄 Waiting for next cycle...\n")
        time.sleep(5)

if __name__ == "__main__":
    main()