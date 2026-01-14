from flask import Flask, request, jsonify
from flask_cors import CORS
import csv
import os

app = Flask(__name__)
CORS(app)

CSV_FILE = "log_detections.csv"

@app.route('/new_detection', methods=['POST'])
def recibir_datos():
    """Receives the JSON from the Pi and adds it to the CSV."""
    try:
        data = request.json
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
        print(f"❌ Error in reception: {e}")
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
            print(f"❌ Error reading CSV: {e}")
            
    return jsonify(registros[::-1])

if __name__ == "__main__":
    print("========================================")
    print("🚀 DATA MANAGEMENT BACKEND STARTED")
    print(f"📍 Local address: http://192.168.1.36:8000")
    print("========================================")
    app.run(host='0.0.0.0', port=8000, debug=False)