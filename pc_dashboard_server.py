from flask import Flask, request, jsonify
from flask_cors import CORS
import csv
import os
import hmac


def _load_dotenv_if_present():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(env_path):
        return
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

CSV_FILE = os.getenv("CSV_FILE", "log_detections.csv")
API_DEVICE_KEY = os.getenv("API_DEVICE_KEY")
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))

raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost,http://127.0.0.1")
ALLOWED_ORIGINS = [o.strip() for o in raw_origins.split(",") if o.strip()]
CORS(app, resources={r"/*": {"origins": ALLOWED_ORIGINS}})


def _validate_runtime_config():
    if not API_DEVICE_KEY:
        raise RuntimeError("Missing required environment variable: API_DEVICE_KEY.")

@app.route('/new_detection', methods=['POST'])
def recibir_datos():
    """Receives the JSON from the Pi and adds it to the CSV."""
    incoming_key = request.headers.get("X-Device-Key", "")
    if not hmac.compare_digest(incoming_key, API_DEVICE_KEY):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "Invalid JSON body"}), 400
        required_fields = ('timestamp', 'object', 'confidence', 'hour')
        missing = [field for field in required_fields if field not in data]
        if missing:
            return jsonify({
                "status": "error",
                "message": f"Missing fields: {', '.join(missing)}"
            }), 400
        print(f"Reception M2M: {data['object']} | Confidence: {data['confidence']}%")
        
        file_exists = os.path.isfile(CSV_FILE)
        
        with open(CSV_FILE, mode='a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Timestamp', 'Object', 'Confidence', 'Hour'])
            
            writer.writerow([
                data['timestamp'], 
                data['object'], 
                data['confidence'], 
                data['hour']
            ])
            
        return jsonify({"status": "success", "message": "Data stored on PC"}), 200
    
    except Exception as e:
        print(f"Error in reception: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/get_data', methods=['GET'])
def enviar_datos():
    """Reads the CSV and returns it as JSON for the Dashboard."""
    registros = []
    if os.path.isfile(CSV_FILE):
        try:
            with open(CSV_FILE, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                registros = list(reader)
        except Exception as e:
            print(f"Error reading CSV: {e}")
            
    return jsonify(registros[::-1])

if __name__ == "__main__":
    _validate_runtime_config()
    print("========================================")
    print("DATA MANAGEMENT BACKEND STARTED")
    print(f"Allowed dashboard origins: {', '.join(ALLOWED_ORIGINS)}")
    print(f"Listening on: http://{BACKEND_HOST}:{BACKEND_PORT}")
    print("========================================")
    app.run(host=BACKEND_HOST, port=BACKEND_PORT, debug=False)
