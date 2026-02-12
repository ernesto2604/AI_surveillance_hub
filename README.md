# AI Surveillance Hub

AI Surveillance Hub is an IoT-based smart monitoring system that combines an Arduino trigger, a Raspberry Pi vision pipeline (YOLOv8), and a Flask backend with a live web dashboard.

When an object is detected near the sensor, the system captures an image, runs object detection, sends a Telegram alert with photo evidence, and stores the detection in a CSV log that is visualized in real time.

## Features

- Ultrasonic-triggered detection flow from Arduino to Raspberry Pi
- Real-time object detection using YOLOv8 on Raspberry Pi
- Telegram photo alerts with detected object and confidence
- Flask API for detection ingestion and dashboard data retrieval
- Live dashboard with stats, detection history, and object distribution chart
- CSV-based persistent logging

## Repository Structure

- `arduinoCode/code`: Arduino sketch that detects proximity and triggers the Pi via HTTP
- `raspberryCode/vision_ai_server.py`: Raspberry Pi service for camera capture, YOLO inference, and alerting
- `pc_dashboard_server.py`: Flask backend that stores detections in `log_detections.csv` and serves dashboard data
- `index.html`: Frontend dashboard UI
- `styles.css`: Dashboard styles
- `log_detections.csv`: Detection log file

## System Architecture

1. Arduino reads distance from an ultrasonic sensor.
2. When distance is below threshold, Arduino calls `GET /detect` on the Raspberry Pi.
3. Raspberry Pi captures a frame, runs YOLOv8 inference, and identifies the top detection.
4. Raspberry Pi sends:
   - Detection metadata to the PC backend (`POST /new_detection`)
   - Telegram photo alert using Bot API
5. PC backend appends detection data to CSV and exposes `GET /get_data`.
6. Web dashboard polls backend every 5 seconds and updates tables/charts.

## Requirements

### Arduino

- Arduino board with Wi-Fi support (e.g., UNO R4 WiFi)
- Ultrasonic sensor (HC-SR04 or compatible)
- Arduino IDE with `WiFiS3` support

### Raspberry Pi

- Raspberry Pi OS with camera support enabled
- Python 3.9+
- Camera module compatible with `picamera2`

Python packages:

- `opencv-python`
- `numpy`
- `picamera2`
- `ultralytics`
- `flask`
- `requests`

### PC / Dashboard Host

- Python 3.9+
- Flask backend dependencies:
  - `flask`
  - `flask-cors`
- Any modern browser for `index.html`

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/ernesto2604/AI_surveillance_hub.git
cd AI_surveillance_hub
```

### 2. Configure Arduino (`arduinoCode/code`)

Update:

- `ssid`
- `pass`
- `server` (Raspberry Pi IP)

Flash the sketch to your board.

### 3. Configure Raspberry Pi (`raspberryCode/vision_ai_server.py`)

Update:

- `PC_IP` and `PC_PORT`
- `TELEGRAM_TOKEN`
- `TELEGRAM_CHAT_ID`

Install dependencies and run:

```bash
python raspberryCode/vision_ai_server.py
```

### 4. Configure and run backend on PC (`pc_dashboard_server.py`)

Optionally adjust host/network values in the script, then run:

```bash
python pc_dashboard_server.py
```

Default API endpoints:

- `POST /new_detection`
- `GET /get_data`

### 5. Open the dashboard

Serve or open `index.html` and ensure it can reach the backend URL configured in the frontend (`http://localhost:8000/get_data` by default).

## API Contract

### `POST /new_detection`

Expected JSON body:

```json
{
  "timestamp": "2026-01-18 17:29:40",
  "object": "bottle",
  "confidence": 76.42,
  "hour": 17
}
```

### `GET /get_data`

Returns an array of detection rows from newest to oldest.

## Security Notes

Current source files contain hardcoded Wi-Fi and Telegram credentials. For production or public sharing:

- Move secrets to environment variables or local config files excluded by `.gitignore`
- Rotate exposed tokens/passwords before deploying
- Restrict network access to trusted LAN hosts

## License

This project is distributed under the MIT License. See `LICENSE` for details.
