"""main.py - FastAPI backend

รันจากโฟลเดอร์รากของโปรเจกต์:
    python -m uvicorn backend.main:app --reload --port 8000
"""
import json
import time

import cv2
import numpy as np
from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend import db
from backend import settings as cfg
from backend.detector import MODELS_DIR, MODEL_NAMES, Detector, ModelNotTrained
from backend.state import DrowsyStateMachine
from arch import LABELS  # noqa: E402  (backend.detector เพิ่ม ml/ เข้า sys.path แล้ว)

app = FastAPI(title="Drowsiness Detection API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

detector = Detector()
SESSIONS = {}  # session_id -> {"sm": DrowsyStateMachine, "key": (status, reason), "seen": float}
SESSION_TTL = 600


def _read_json(path):
    return json.loads(path.read_text()) if path.exists() else None


def _model_info(name):
    return {
        "name": name,
        "label": LABELS[name],
        "ready": (MODELS_DIR / f"{name}.keras").exists(),
        "metrics": _read_json(MODELS_DIR / f"{name}_metrics.json"),
        "webcam": _read_json(MODELS_DIR / f"{name}_webcam.json"),
    }


def _session(session_id):
    now = time.monotonic()
    for sid in [s for s, v in SESSIONS.items() if now - v["seen"] > SESSION_TTL]:
        del SESSIONS[sid]
    s = SESSIONS.setdefault(session_id, {"sm": DrowsyStateMachine(), "key": ("Normal", None), "seen": now})
    s["seen"] = now
    return s


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/models")
def models():
    return [_model_info(n) for n in MODEL_NAMES]


@app.get("/api/models/{name}")
def model_detail(name: str):
    if name not in LABELS:
        raise HTTPException(404, "ไม่พบโมเดลนี้")
    return _model_info(name)


@app.post("/api/predict")
def predict(file: UploadFile = File(...), model: str = Form(...), session_id: str = Form(...)):
    if model not in LABELS:
        raise HTTPException(400, f"model ต้องเป็นหนึ่งใน {MODEL_NAMES}")
    frame = cv2.imdecode(np.frombuffer(file.file.read(), np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(400, "อ่านภาพไม่ได้")
    try:
        r = detector.analyze(frame, model)
    except ModelNotTrained:
        raise HTTPException(409, f"ยังไม่ได้เทรนโมเดล {LABELS[model]} (รัน python ml/train.py ก่อน)")

    conf = cfg.get()
    r["threshold_default"] = r["threshold"]  # ค่าจาก models/<name>_metrics.json
    if model in conf["thresholds"]:
        r["threshold"] = conf["thresholds"][model]  # ค่าที่ตั้งจากหน้าเว็บ

    s = _session(session_id)
    st = s["sm"].update(time.monotonic(), r["p_closed"], r["threshold"], r["yaw"], conf)
    key = (st["status"], st["reason"])
    if st["status"] in ("Warning", "Danger") and key != s["key"]:
        seconds = st["distract_seconds"] if st["reason"] == "distracted" else st["closed_seconds"]
        db.log_event(session_id, model, st["status"], seconds, r["p_closed"], st["reason"], st["yaw"])
    s["key"] = key
    return {**r, **st}


@app.get("/api/settings")
def get_settings():
    return {**cfg.get(), "defaults": cfg.DEFAULTS, "limits": cfg.LIMITS, "model_thresholds": _file_thresholds()}


@app.put("/api/settings")
def put_settings(patch: dict = Body(...)):
    cfg.update(patch)
    return get_settings()


@app.post("/api/settings/reset")
def reset_settings():
    cfg.reset()
    return get_settings()


def _file_thresholds():
    """threshold จากไฟล์ metrics ของแต่ละโมเดล (ค่าเริ่มต้นก่อนปรับบนเว็บ)"""
    out = {}
    for n in MODEL_NAMES:
        m = _read_json(MODELS_DIR / f"{n}_metrics.json")
        out[n] = m.get("threshold") if m else None
    return out


@app.get("/api/history")
def history(limit: int = 200):
    return db.list_events(min(limit, 1000))


@app.get("/api/stats")
def stats():
    return db.stats()


@app.delete("/api/history")
def clear_history():
    db.clear_events()
    return {"ok": True}
