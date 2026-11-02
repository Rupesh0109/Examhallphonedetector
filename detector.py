"""YOLO-based person and mobile phone detector."""
import cv2
from ultralytics import YOLO

PERSON_CLASS = 0
PHONE_CLASS = 67
MARGIN = 0.25  # proximity margin as fraction of person box size


class Detector:
    def __init__(self, model_path="yolov8n.pt"):
        # Lightweight pretrained YOLOv8 nano model (CPU friendly)
        self.model = YOLO(model_path)

    def detect(self, frame):
        results = self.model(frame, verbose=False, conf=0.4)
        persons = []
        phones = []
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
                item = {"bbox": (x1, y1, x2, y2), "conf": conf}
                if cls == PERSON_CLASS:
                    persons.append(item)
                elif cls == PHONE_CLASS:
                    phones.append(item)

        pairs = []
        for pi, p in enumerate(persons):
            for qi, ph in enumerate(phones):
                if self._near(p["bbox"], ph["bbox"]):
                    pairs.append((pi, qi))
        return persons, phones, pairs

    @staticmethod
    def _near(person_bbox, phone_bbox):
        px1, py1, px2, py2 = person_bbox
        hx1, hy1, hx2, hy2 = phone_bbox
        cx = (hx1 + hx2) // 2
        cy = (hy1 + hy2) // 2
        w = px2 - px1
        h = py2 - py1
        mx = int(w * MARGIN)
        my = int(h * MARGIN)
        if px1 - mx <= cx <= px2 + mx and py1 - my <= cy <= py2 + my:
            return True
        ix1 = max(px1, hx1); iy1 = max(py1, hy1)
        ix2 = min(px2, hx2); iy2 = min(py2, hy2)
        if ix2 > ix1 and iy2 > iy1:
            return True
        return False

    def annotate(self, frame, persons, phones, pairs):
        warned_persons = {p for p, _ in pairs}
        warned_phones = {q for _, q in pairs}

        for i, p in enumerate(persons):
            x1, y1, x2, y2 = p["bbox"]
            color = (0, 0, 255) if i in warned_persons else (0, 200, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"Person {p['conf']:.2f}", (x1, max(y1 - 8, 15)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        for j, ph in enumerate(phones):
            x1, y1, x2, y2 = ph["bbox"]
            color = (0, 0, 255) if j in warned_phones else (255, 165, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"Phone {ph['conf']:.2f}", (x1, max(y1 - 8, 15)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        if pairs:
            cv2.putText(frame, "Potential phone use detected", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        return frame