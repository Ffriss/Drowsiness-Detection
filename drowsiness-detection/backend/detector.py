"""detector.py - MediaPipe Face Mesh -> ตัดตา -> preprocess -> โมเดล -> P(closed)  และคำนวณมุมหันหน้า (yaw)"""
import base64
import json
import math
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))

from arch import LABELS  # noqa: E402
from eyecrop import extract_eyes  # noqa: E402
from preprocess import preprocess_uint8, to_model_input  # noqa: E402

MODELS_DIR = ROOT / "models"
MODEL_NAMES = list(LABELS)

# จุดขอบแก้มซ้าย/ขวา และหางตาซ้าย/ขวา (ตามตำแหน่งในภาพ) ของ MediaPipe Face Mesh
YAW_PAIRS = [(234, 454), (33, 263)]
YAW_SIGN = 1  # ถ้าทดสอบแล้วหันซ้ายแต่จอบอกขวา ให้เปลี่ยนเป็น -1


def to_data_url(g_uint8):
    """ภาพขาวดำ 64x64 -> data URL (PNG) ให้หน้าเว็บแสดงได้ทันที"""
    ok, buf = cv2.imencode(".png", g_uint8)
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode() if ok else None


def estimate_yaw(face_landmarks, width):
    """มุมหันซ้าย/ขวาโดยประมาณ (องศา) จากความลึก z ของจุดคู่ซ้าย-ขวาบนใบหน้า
    มองตรง ≈ 0, ค่าบวก = หันไปทางซ้ายของผู้ขับ, ค่าลบ = หันขวา"""
    lm = face_landmarks.landmark
    angles = []
    for a, b in YAW_PAIRS:
        dx = (lm[b].x - lm[a].x) * width
        dz = (lm[b].z - lm[a].z) * width
        if abs(dx) > 1e-6:
            angles.append(math.degrees(math.atan2(dz, dx)))
    return YAW_SIGN * float(np.mean(angles)) if angles else None


class ModelNotTrained(Exception):
    pass


class Detector:
    def __init__(self):
        self._lock = threading.Lock()
        self._mesh = None
        self._models = {}
        self._thresholds = {}

    def _get_mesh(self):
        if self._mesh is None:
            import mediapipe as mp
            self._mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False, max_num_faces=1, refine_landmarks=False,
                min_detection_confidence=0.5, min_tracking_confidence=0.5)
        return self._mesh

    def _get_model(self, name):
        if name not in self._models:
            path = MODELS_DIR / f"{name}.keras"
            if not path.exists():
                raise ModelNotTrained(name)
            import tensorflow as tf
            self._models[name] = tf.keras.models.load_model(path, compile=False)
            meta = MODELS_DIR / f"{name}_metrics.json"
            self._thresholds[name] = json.loads(meta.read_text()).get("threshold", 0.5) if meta.exists() else 0.5
        return self._models[name]

    def threshold(self, name):
        return self._thresholds.get(name, 0.5)

    def analyze(self, frame_bgr, name):
        """คืน dict: face_found, p_closed (หรือ None), yaw, eye_boxes, eye_images, eye_probs, latency_ms, threshold"""
        t0 = time.perf_counter()
        with self._lock:
            model = self._get_model(name)
            res = self._get_mesh().process(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
            face = res.multi_face_landmarks[0] if res.multi_face_landmarks else None
            eyes = extract_eyes(frame_bgr, face) if face else []
            if not eyes:
                return {"face_found": False, "p_closed": None, "yaw": None, "eye_boxes": [], "eye_images": [],
                        "latency_ms": round((time.perf_counter() - t0) * 1000, 1), "threshold": self.threshold(name)}
            yaw = estimate_yaw(face, frame_bgr.shape[1])
            grays = [preprocess_uint8(crop) for crop, _ in eyes]  # ภาพที่โมเดลเห็นจริง
            batch = np.stack([to_model_input(g) for g in grays])
            probs = model(batch, training=False).numpy().ravel()
            p = float(np.mean(probs))
        return {"face_found": True, "p_closed": round(p, 4), "yaw": None if yaw is None else round(yaw, 1),
                "eye_boxes": [list(b) for _, b in eyes],
                "eye_images": [to_data_url(g) for g in grays],
                "eye_probs": [round(float(v), 4) for v in probs],
                "latency_ms": round((time.perf_counter() - t0) * 1000, 1), "threshold": self.threshold(name)}
