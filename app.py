"""Flask backend for the AI Student Mobile Phone Detection System."""
import datetime
import json
import os
import threading
import time
import uuid

import cv2
from flask import Flask, Response, jsonify, render_template, request

from detector import Detector

app = Flask(__name__)
detector = Detector()

camera_lock = threading.Lock()
frame_lock = threading.Lock()
stats_lock = threading.Lock()
incidents_lock = threading.Lock()

running = False
stop_event = threading.Event()
camera_thread = None
camera_index = None
latest_frame = None
last_alert_time = 0.0
ALERT_COOLDOWN = 3.0
MAX_CAMERAS = 10

INCIDENTS_FILE = "incidents.json"
INCIDENTS_DIR = os.path.join("static", "incidents")
os.makedirs(INCIDENTS_DIR, exist_ok=True)

latest_stats = {
    "people": 0,
    "phones": 0,
    "warnings": 0,
    "alert": False,
    "alert_message": "No camera running.",
    "error": None,
}

incidents = []


def load_incidents():
    global incidents
    if os.path.exists(INCIDENTS_FILE):
        try:
            with open(INCIDENTS_FILE) as f:
                incidents = json.load(f)
        except Exception:
            incidents = []


def save_incidents():
    with open(INCIDENTS_FILE, "w") as f:
        json.dump(incidents, f, indent=2)


load_incidents()


def list_cameras():
    available = []
    for i in range(MAX_CAMERAS):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                available.append({"index": i, "name": f"Camera {i}"})
        cap.release()
    return available


def camera_worker(index):
    global running, latest_frame, last_alert_time
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        with stats_lock:
            latest_stats["error"] = f"Cannot open camera {index}."
            latest_stats["alert_message"] = "Camera error."
        running = False
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.05)
            continue
        persons, phones, pairs = detector.detect(frame)
        annotated = detector.annotate(frame, persons, phones, pairs)

        now = time.time()
        with stats_lock:
            latest_stats["people"] = len(persons)
            latest_stats["phones"] = len(phones)
            latest_stats["warnings"] = len(pairs)
            latest_stats["error"] = None
            if pairs:
                latest_stats["alert"] = True
                if now - last_alert_time >= ALERT_COOLDOWN:
                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"incident_{ts}_{uuid.uuid4().hex[:6]}.jpg"
                    filepath = os.path.join(INCIDENTS_DIR, filename)
                    cv2.imwrite(filepath, annotated)
                    record = {
                        "id": uuid.uuid4().hex,
                        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
                        "camera_index": index,
                        "people": len(persons),
                        "phones": len(phones),
                        "warnings": len(pairs),
                        "image": f"incidents/{filename}",
                    }
                    with incidents_lock:
                        incidents.insert(0, record)
                        if len(incidents) > 100:
                            incidents[:] = incidents[:100]
                        save_incidents()
                    latest_stats["alert_message"] = (
                        f"Warning: {len(pairs)} potential phone-use detection(s)."
                    )
                    last_alert_time = now
            else:
                latest_stats["alert"] = False
                latest_stats["alert_message"] = "No phone detected near a person."

        ok, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if ok:
            with frame_lock:
                latest_frame = buf.tobytes()

    cap.release()
    with frame_lock:
        latest_frame = None
    running = False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/incidents")
def incidents_page():
    return render_template("incidents.html")


@app.route("/cameras")
def cameras():
    return jsonify({"cameras": list_cameras()})


@app.route("/camera/select", methods=["POST"])
def select_camera():
    global camera_index
    data = request.get_json(silent=True) or {}
    idx = data.get("index")
    try:
        idx = int(idx)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid camera index."}), 400
    if idx < 0 or idx >= MAX_CAMERAS:
        return jsonify({"ok": False, "error": "Camera index out of range."}), 400
    with camera_lock:
        if running:
            return jsonify({"ok": False, "error": "Stop the camera before switching."}), 409
        camera_index = idx
    return jsonify({"ok": True, "index": idx, "name": f"Camera {idx}"})


@app.route("/camera/start", methods=["POST"])
def start_camera():
    global running, camera_thread, stop_event
    with camera_lock:
        if running:
            return jsonify({"ok": False, "error": "Camera already running."}), 409
        if camera_index is None:
            return jsonify({"ok": False, "error": "Select a camera first."}), 400
        running = True
        stop_event.clear()
        camera_thread = threading.Thread(
            target=camera_worker, args=(camera_index,), daemon=True
        )
        camera_thread.start()
    return jsonify({"ok": True})


@app.route("/camera/stop", methods=["POST"])
def stop_camera():
    global running
    with camera_lock:
        if not running:
            return jsonify({"ok": True, "message": "Camera not running."})
        running = False
    stop_event.set()
    if camera_thread is not None:
        camera_thread.join(timeout=5)
    with stats_lock:
        latest_stats["people"] = 0
        latest_stats["phones"] = 0
        latest_stats["warnings"] = 0
        latest_stats["alert"] = False
        latest_stats["alert_message"] = "Camera stopped."
    return jsonify({"ok": True})


@app.route("/video_feed")
def video_feed():
    def gen():
        while True:
            with frame_lock:
                frame = latest_frame
            if frame is None:
                time.sleep(0.1)
                continue
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )
            time.sleep(0.03)

    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/stats")
def stats():
    with stats_lock:
        data = dict(latest_stats)
    data["running"] = running
    data["camera_index"] = camera_index
    data["incident_count"] = len(incidents)
    return jsonify(data)


@app.route("/api/incidents")
def api_incidents():
    with incidents_lock:
        return jsonify({"incidents": list(incidents)})


@app.route("/incidents/clear", methods=["POST"])
def clear_incidents():
    with incidents_lock:
        for inc in incidents:
            try:
                os.remove(os.path.join("static", inc["image"]))
            except OSError:
                pass
        incidents.clear()
        save_incidents()
    return jsonify({"ok": True})


if __name__ == "__main__":
    try:
        app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
    finally:
        stop_event.set()
        if camera_thread is not None:
            camera_thread.join(timeout=5)