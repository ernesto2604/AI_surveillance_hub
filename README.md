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
- `arduinoCode/secrets.h.example`: Template for local Arduino secrets (Wi-Fi, Pi IP, device key)
- `raspberryCode/vision_ai_server.py`: Raspberry Pi service for camera capture, YOLO inference, and alerting
- `pc_dashboard_server.py`: Flask backend that stores detections in `log_detections.csv` and serves dashboard data
- `index.html`: Frontend dashboard UI
- `styles.css`: Dashboard styles
- `log_detections.csv`: Detection log file
- `.env.example`: Template for runtime configuration and shared API keys

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

### 2. Configure runtime secrets

Create a local environment file from the template:

```bash
cp .env.example .env
```

Set at least these required values:

- `API_DEVICE_KEY`: secret used by backend to accept requests
- `DEVICE_KEY`: same value as `API_DEVICE_KEY` (used by Raspberry Pi when posting detections)
- `CAPTURE_ENDPOINT_KEY`: secret required by Raspberry Pi `/detect` endpoint
- `PC_IP` and `PC_PORT`: backend address reachable from Raspberry Pi
- `PI_PORT`: Raspberry Pi detection endpoint port (must match Arduino `PI_SERVER_PORT`)

Optional:

- `TELEGRAM_TOKEN`
- `TELEGRAM_CHAT_ID`
- `ALLOWED_ORIGINS` for dashboard CORS

### 3. Configure Arduino secrets (`arduinoCode/secrets.h`)

Create a local secrets file from the template:

```bash
cp arduinoCode/secrets.h.example arduinoCode/secrets.h
```

Set:

- `WIFI_SSID`
- `WIFI_PASS`
- `PI_SERVER_IP`
- `PI_SERVER_PORT` (must match `PI_PORT` in `.env`)
- `DEVICE_KEY` (must match `CAPTURE_ENDPOINT_KEY` in `.env`)

Then flash `arduinoCode/code` to your board.

### 4. Install Python dependencies

Recommended (both PC and Raspberry Pi):

```bash
pip install flask flask-cors requests numpy opencv-python ultralytics
```

Raspberry Pi also needs `picamera2` installed according to your OS image/package manager.

### 5. Run backend on PC

The backend auto-loads `.env` from the repository root, then start:

```bash
python pc_dashboard_server.py
```

### 6. Run vision service on Raspberry Pi

The vision service also auto-loads `.env` from the repository root (or current folder), then run:

```bash
python raspberryCode/vision_ai_server.py
```

Default API endpoints:

- `POST /new_detection`
- `GET /get_data`
- `GET /detect` (requires `X-Device-Key` header)

### 7. Open the dashboard

Serve or open `index.html` and ensure it can reach the backend URL configured in the frontend (`http://localhost:8000/get_data` by default).

## API Contract

### `POST /new_detection`

Security:

- Requires header `X-Device-Key: <API_DEVICE_KEY>`

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

### `GET /detect`

Security:

- Requires header `X-Device-Key: <CAPTURE_ENDPOINT_KEY>`

## Project Report

For a complete explanation of the project design, implementation decisions, and results, see:

- `docs/AI_surveillance_hub_report.pdf`

## Security Notes

Security hardening applied in this repository:

- Secrets removed from source code and moved to `.env` and `arduinoCode/secrets.h` (both ignored by git)
- Device-to-device endpoints now require shared key authentication (`X-Device-Key`)
- CORS is configurable with `ALLOWED_ORIGINS`

Recommended operational actions:

- Rotate any token/password that was previously committed
- Use long random values for `API_DEVICE_KEY` and `CAPTURE_ENDPOINT_KEY`
- Restrict services to trusted LAN hosts and firewall unnecessary ports

## Troubleshooting

- `Missing required environment variable: API_DEVICE_KEY`:
  ensure `.env` is loaded and contains the key.
- Raspberry Pi `/detect` returns `401 Unauthorized`:
  `DEVICE_KEY` in `arduinoCode/secrets.h` must match `CAPTURE_ENDPOINT_KEY` on Pi.
- Backend `/new_detection` returns `401 Unauthorized`:
  `DEVICE_KEY` on Pi must match `API_DEVICE_KEY` on backend.
- Dashboard shows no data:
  verify backend is running on port `8000` and `index.html` points to the correct host.

## License

This project is distributed under the MIT License. See `LICENSE` for details.
