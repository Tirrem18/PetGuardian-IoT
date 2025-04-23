# 🚀 How to Run the Dashboard
To launch the PetGuardian Streamlit dashboard, run the following command from the root of the project:

streamlit run dashboard/dashboard.py

# PetGuardian-IoT — Sensor Configuration Guide

The system assumes all sensors (SOUND, CAMERA, GPS) are active by default, simulating a real smart collar setup.

Use environment variables to switch each sensor between **real**, **virtual**, and **interactive** modes.

---

## 🔧 Sensor Mode Basics

| Mode Type       | Value     | Description                                        |
|----------------|-----------|----------------------------------------------------|
| Real Mode       | `true`    | Uses actual hardware (e.g., GPIO, PiCamera, GPS)   |
| Virtual Mode    | `false`   | Simulates input with fake or test data             |
| Interactive Mode| `interactive` | Allows manual testing (keyboard or terminal input) |

---

## ⚙️ Full Command Examples with Descriptions

### 🛰️ GPS Sensor
- `$env:GPS="true"; $env:GPS_MODE="interactive"; python 
  - Manually trigger real GPS hardware (if present)

- `$env:GPS="false"; $env:GPS_MODE="interactive"; python
  - Simulate GPS ping with manual coordinate entry

- `$env:GPS="true"; python
  - Auto-detect location from GPS hardware on MQTT trigger

- `$env:GPS="false"; python
  - Simulate GPS data with random coordinates (virtual auto-mode)

### 📷 Camera Sensor
- `$env:CAMERA="true"; $env:CAMERA_MODE="interactive"; python
  - Press `C` to capture from real camera manually

- `$env:CAMERA="false"; $env:CAMERA_MODE="interactive"; python
  - Pick a test image manually from list (virtual test)

- `$env:CAMERA="true"; python
  - Automatically capture real image on MQTT trigger

- `$env:CAMERA="false"; python
  - Auto-simulate a webcam snapshot when triggered

### 🔊 Acoustic Sensor
- `$env:SOUND="true"; $env:SOUND_MODE="interactive"; python
  - Press `ENTER` to simulate sound on real hardware

- `$env:SOUND="false"; $env:SOUND_MODE="interactive"; python 
  - Use `S` to simulate sound, `X` to exit (virtual/manual)

- `$env:SOUND="true"; python
  - Automatically detect real acoustic events from GPIO

- `$env:SOUND="false"; python 
  - Auto-simulate random sound spikes in background

---

## 🔁 Main Program with Mixed Configurations

### Run All Sensors in Virtual Mode:
```bash
SOUND=false CAMERA=false GPS=false python main.py
```

### Run Only Camera as Real Sensor:
```bash
SOUND=false CAMERA=true GPS=false python main.py
```

### Run All Sensors in Real Mode:
```bash
SOUND=true CAMERA=true GPS=true python main.py
```

---OR

SOUND=true SOUND_MODE=interactive python3 acoustic_sensor.py on PI
