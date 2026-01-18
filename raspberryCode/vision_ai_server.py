import cv2
import numpy as np
from picamera2 import Picamera2
from ultralytics import YOLO
from flask import Flask, jsonify
import threading
import time
import os
import datetime
import requests

app = Flask(__name__)
model = YOLO('yolov8n.pt') 

PC_IP = "192.168.1.37" 
PC_PORT = "8000"

TELEGRAM_TOKEN = "8574425087:AAH21JZ8Bv4DkgKE3jU7FiVipuRwKeJIiH4"
TELEGRAM_CHAT_ID = "1144391963"

trigger_capture = False
screen_text = ""


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
        requests.post(url, json=payload, timeout=3)
        print(f"[PC] Data synchronized: {obj_name}")
    except:
        print("[PC] Error: PC Server not detected")

def send_telegram_alert(message, image_path):
    """Sends a photo alert with caption via Telegram."""
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

    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False), daemon=True).start()

    print("--- SYSTEM ONLINE: WAITING FOR ARDUINO ON PORT 5000 ---")
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
    main()