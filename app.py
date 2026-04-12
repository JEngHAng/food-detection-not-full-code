import logging
import time
import os
from flask import Flask, jsonify, render_template, send_from_directory, Response, request
from flask_cors import CORS
from config import ServerConfig, DB_PATH, UPLOAD_DIR
from database import init_db
from detector import FoodDetector
from hardware.camera import PiCamera

app = Flask(__name__)
CORS(app)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
init_db(str(DB_PATH))

app.detector = FoodDetector()
app.camera = PiCamera()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/video_feed")
def video_feed():
    def generate():
        while True:
            frame = app.camera.get_frame()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.1)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/api/capture", methods=["POST"])
def capture_api():
    path = app.camera.capture()
    if path:
        filename = os.path.basename(path)
        # ✅ ใส่ Timestamp กลับไปใน JSON เลยเพื่อให้ JS ใช้งานง่าย
        return jsonify({
            "success": True, 
            "filename": filename,
            "image_url": f"/uploads/{filename}?t={int(time.time())}"
        })
    return jsonify({"success": False, "error": "Camera Busy"}), 500

@app.route("/api/detect-captured", methods=["POST"])
def detect_api():
    data = request.get_json()
    filename = data.get("filename")
    if not filename:
        return jsonify({"success": False, "error": "No file"}), 400
    
    image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    result = app.detector.detect(image_path)
    
    return jsonify({
        "success": True,
        "total_price": result.get("total_price", 0),
        "annotated_image": f"/uploads/annotated_{filename}?t={int(time.time())}",
        "dishes": result.get("detections", []),
        "pending_file": filename
    })

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
