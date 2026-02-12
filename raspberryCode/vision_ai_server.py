import cv2
import numpy as np
from picamera2 import Picamera2
from ultralytics import YOLO
from flask import Flask, jsonify, request
import threading
import time
import os
import datetime
import requests
import hmac


def _load_dotenv_if_present():
    candidates = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
    ]
    loaded_paths = set()
    for env_path in candidates:
        if env_path in loaded_paths or not os.path.isfile(env_path):
            continue
        loaded_paths.add(env_path)
        with open(env_path, mode="r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)


_load_dotenv_if_present()

app = Flask(__name__)
model = YOLO('yolov8n.pt') 

PC_IP = os.getenv("PC_IP", "127.0.0.1")
PC_PORT = os.getenv("PC_PORT", "8000")
DEVICE_KEY = os.getenv("DEVICE_KEY")
CAPTURE_ENDPOINT_KEY = os.getenv("CAPTURE_ENDPOINT_KEY")
PI_PORT = int(os.getenv("PI_PORT", "5000"))

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

trigger_capture = False
screen_text = ""


def _validate_runtime_config():
    missing = []
    if not DEVICE_KEY:
        missing.append("DEVICE_KEY")
    if not CAPTURE_ENDPOINT_KEY:
        missing.append("CAPTURE_ENDPOINT_KEY")
    if missing:
        raise RuntimeError(
            "Missing required environment variables: "
            + ", ".join(missing)
            + "."
        )


def send_to_pc(obj_name, confidence):
    """Sends detection data to the PC server."""
    url = f"http://{PC_IP}:{PC_PORT}/new_detection"
    payload = {
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'object': obj_name,
        'confidence': round(confidence, 2),
        'hour': datetime.datetime.now().hour
    }
    try:
        headers = {"X-Device-Key": DEVICE_KEY}
        requests.post(url, json=payload, headers=headers, timeout=3)
        print(f"[PC] Data synchronized: {obj_name}")
    except requests.RequestException:
        print("[PC] Error: PC Server not detected or rejected request")

def send_telegram_alert(message, image_path):
    """Sends a photo alert with caption via Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[TELEGRAM] Skipped: TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not configured")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        with open(image_path, 'rb') as photo:
            payload = {
                'chat_id': TELEGRAM_CHAT_ID, 
                'caption': message, 
                'parse_mode': 'Markdown' 
            }
            files = {'photo': photo}
            requests.post(url, data=payload, files=files, timeout=10)
            print("[TELEGRAM] Photo alert sent")
    except Exception as e:
        print(f"[TELEGRAM] Error: Failed to send message. {e}")


@app.route('/detect', methods=['GET'])
def trigger():
    global trigger_capture
    incoming_key = request.headers.get("X-Device-Key", "")
    if not hmac.compare_digest(incoming_key, CAPTURE_ENDPOINT_KEY):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    if not trigger_capture:
        print("\n[M2M] Package detection signal received from Arduino.")
        trigger_capture = True
        return "Starting capture", 200
    return "Busy", 400


def main():
    global trigger_capture, screen_text
    
    picam2 = None
    camera_active = False

    cv2.namedWindow("Smart Vision Monitor", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Smart Vision Monitor", 600, 720) 

    threading.Thread(
        target=lambda: app.run(
            host='0.0.0.0',
            port=PI_PORT,
            debug=False,
            use_reloader=False
        ),
        daemon=True
    ).start()

    print(f"--- SYSTEM ONLINE: WAITING FOR ARDUINO ON PORT {PI_PORT} ---")
    print("--- CAMERA OFF: Energy saving mode active ---")

    try:
        while True:
            if trigger_capture and not camera_active:
                print("[CAMERA] Turning ON - Arduino signal received")
                try:
                    if picam2 is not None:
                        picam2.close()
                        picam2 = None
                        time.sleep(0.5)  
                    
                    picam2 = Picamera2()
                    config = picam2.create_preview_configuration(
                        main={"format": "RGB888", "size": (1280, 960)},
                        sensor={"output_size": picam2.sensor_resolution}
                    )
                    picam2.configure(config)
                    picam2.start()
                    camera_active = True
                except RuntimeError as e:
                    print(f"[CAMERA] ERROR: Failed to initialize camera: {e}")
                    print("[CAMERA] Retrying in 1 second...")
                    time.sleep(1)
                    trigger_capture = False
                    continue
            
            if camera_active and trigger_capture:
                for i in range(3, 0, -1):
                    start_sec = time.time()
                    while time.time() - start_sec < 1.0:
                        f_count = picam2.capture_array()
                        height_c, width_c = f_count.shape[:2]
                        crop_width_c = 800
                        x_start_c = (width_c - crop_width_c) // 2
                        f_count = f_count[:, x_start_c:x_start_c + crop_width_c]
                        cv2.putText(f_count, str(i), (250, 300), cv2.FONT_HERSHEY_SIMPLEX, 8, (0, 255, 0), 15)
                        cv2.imshow("Smart Vision Monitor", f_count)
                        cv2.waitKey(1)
                
                print("[AI] Processing image...")
                frame_ia = picam2.capture_array()
                height_ia, width_ia = frame_ia.shape[:2]
                crop_width_ia = 800
                x_start_ia = (width_ia - crop_width_ia) // 2
                frame_ia = frame_ia[:, x_start_ia:x_start_ia + crop_width_ia]
                results = model.predict(source=frame_ia, conf=0.5, verbose=False)
                
                if results[0].boxes:
                    box = results[0].boxes[0]
                    name = model.names[int(box.cls[0])]
                    conf = float(box.conf[0]) * 100
                    
                    image_path = "temp_capture.jpg"
                    cv2.imwrite(image_path, results[0].plot())

                    current_time = datetime.datetime.now().strftime("%H:%M:%S")
                    alert_msg = (
                        f"NEW DELIVERY DETECTED\n\n"
                        f"Object: {name}\n"
                        f"Accuracy: {conf:.1f}%\n"
                        f"Time: {current_time}"
                    )

                    threading.Thread(target=send_to_pc, args=(name, conf)).start()
                    threading.Thread(target=send_telegram_alert, args=(alert_msg, image_path)).start()
                    
                    screen_text = f"DETECTED: {name.upper()}"
                else:
                    screen_text = "NO OBJECTS DETECTED"
                
                trigger_capture = False
                
                print("[CAMERA] Turning OFF - Energy saving mode activated")
                if picam2 is not None:
                    picam2.stop()
                    picam2.close()
                    picam2 = None
                camera_active = False
                time.sleep(0.5) 
            elif not trigger_capture and not camera_active:
                idle_frame = np.zeros((960, 800, 3), dtype=np.uint8)
                cv2.putText(idle_frame, "WAITING FOR SIGNAL", (100, 400), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (100, 100, 100), 2)
                cv2.putText(idle_frame, "Camera: OFF (Energy Saving)", (50, 500), cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 100, 100), 2)
                cv2.imshow("Smart Vision Monitor", idle_frame)
                cv2.waitKey(100)
            
            if cv2.waitKey(1) & 0xFF == ord('q'): 
                break
    finally:
        if camera_active and picam2 is not None:
            picam2.stop()
            picam2.close()
        cv2.destroyAllWindows()
        if os.path.exists("temp_capture.jpg"): os.remove("temp_capture.jpg")

if __name__ == "__main__":
    _validate_runtime_config()
    main()
