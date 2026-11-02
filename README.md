# AI Student Mobile Phone Detection System

A beginner-friendly web app that uses a pretrained YOLO model to detect people and mobile phones from a webcam, draws bounding boxes, and warns when a phone is detected near a person.

## Project structure

```
classroom-phone-detector/
├── app.py
├── detector.py
├── requirements.txt
├── README.md
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── script.js
```

## File purposes

- `app.py` - Flask server, camera management, video streaming, stats API, incident logging.
- `detector.py` - YOLO detection, proximity check, annotation drawing.
- `templates/index.html` - Dashboard UI.
- `static/style.css` - Styling.
- `static/script.js` - Frontend logic, polling, camera enumeration.
- `requirements.txt` - Python dependencies.

## Installation

### 1. Install Python
Install Python 3.9+ from https://www.python.org (check "Add to PATH").

### 2. Create virtual environment
```bash
cd classroom-phone-detector
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```
The first run downloads `yolov8n.pt` automatically.

### 4. Run the app
```bash
python app.py
```

### 5. Open website
Visit http://127.0.0.1:5000

### 6. Select a camera
Use the dropdown (backend camera indices). Click "Refresh" to rescan. Click "Request Browser Camera Permission" to enumerate browser devices (informational only).

### 7. Start / stop detection
Click "Start Camera", then "Stop Camera" to release the camera.

### 8. View incidents
Open the "Incidents" page from the top nav to see logged phone-near-person events with timestamps and snapshots.

## Browser vs backend camera access

- Browser camera access uses `navigator.mediaDevices` (JavaScript) and shows device labels after permission.
- Backend camera access uses OpenCV `cv2.VideoCapture(index)` on the server machine.
- Browser device IDs cannot be reliably matched to OpenCV indices, so this project uses a simple backend camera-index selector. Limitation: index 0 is usually the default webcam; external USB webcams often appear as 1, 2, etc. If a selected index fails, try the next.

## Detection notes

- Uses YOLO COCO classes: person (0), cell phone (67).
- Proximity: phone centre inside/near an expanded person box, or overlapping.
- A warning means a phone was detected near a person. This does NOT prove active phone usage.

## Common errors / troubleshooting

- "No cameras found": close other apps using the webcam; try index 1/2.
- Slow performance: YOLOv8n is lightweight; reduce resolution already set to 640x480. Close other programs.
- Model download fails: check internet; manually place `yolov8n.pt` in the project folder.
- Port in use: change port in app.py.
- Camera not releasing: ensure you click Stop; Ctrl+C stops the server and releases via finally block.
- OpenCV import error on Linux: `pip install opencv-python-headless` instead.

## Constraints

CPU inference only, no training, no database, no cloud. Suitable for a first-year engineering student.