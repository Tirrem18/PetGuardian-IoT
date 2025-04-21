# PetGuardian-IoT

By default, the system assumes all sensors (SOUND, CAMERA, GPS) are active — as they would be on a real-life smart collar.

You can **disable individual sensors** and simulate their behavior by running `main.py` with environment flags:

▶ Example – run all sensors in virtual/simulated mode:
SOUND=false CAMERA=false GPS=false python main.py

▶ Example – test only the real camera sensor:
SOUND=false CAMERA=true GPS=false python main.py

These flags let you mix real and virtual sensors for flexible development and testing.
