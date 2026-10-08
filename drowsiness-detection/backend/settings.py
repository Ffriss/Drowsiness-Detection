"""settings.py - ค่าที่ปรับได้จากหน้าเว็บ บันทึกไว้ที่ data/settings.json (ไม่หายเมื่อรีสตาร์ต backend)"""
import json
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "settings.json"
_lock = threading.Lock()

DEFAULTS = {
    "eye_warn": 1.0,         # วินาทีที่ตาปิดต่อเนื่องก่อนเตือน
    "eye_danger": 2.0,       # วินาทีที่ตาปิดต่อเนื่องก่อนอันตราย
    "yaw_limit": 30.0,       # องศาที่หันเกินแล้วนับว่าไม่มองถนน
    "yaw_return": 20.0,      # องศาที่ต้องหันกลับมาถึงจะนับว่ามองถนน
    "distract_warn": 2.0,    # วินาทีที่ไม่มองถนนก่อนเตือน
    "distract_danger": 4.0,  # วินาทีที่ไม่มองถนนก่อนอันตราย
    "thresholds": {},        # {"custom_cnn": 0.3, ...} ถ้าไม่มี ใช้ค่าจาก models/<name>_metrics.json
}

# ช่วงค่าที่อนุญาต (ต่ำสุด, สูงสุด)
LIMITS = {
    "eye_warn": (0.3, 10.0), "eye_danger": (0.5, 15.0),
    "yaw_limit": (5.0, 80.0), "yaw_return": (0.0, 75.0),
    "distract_warn": (0.5, 15.0), "distract_danger": (1.0, 30.0),
}

_current = None


def _load():
    global _current
    if _current is None:
        data = {}
        if PATH.exists():
            try:
                data = json.loads(PATH.read_text())
            except (ValueError, OSError):
                data = {}
        _current = {**DEFAULTS, **{k: v for k, v in data.items() if k in DEFAULTS}}
        _current["thresholds"] = dict(_current.get("thresholds") or {})
    return _current


def get():
    with _lock:
        s = _load()
        return {**s, "thresholds": dict(s["thresholds"])}


def _validate(s):
    for key, (lo, hi) in LIMITS.items():
        s[key] = round(min(max(float(s[key]), lo), hi), 2)
    # ค่าอันตรายต้องมากกว่าค่าเตือน และมุมกลับต้องน้อยกว่ามุมเข้า
    s["eye_danger"] = max(s["eye_danger"], s["eye_warn"] + 0.1)
    s["distract_danger"] = max(s["distract_danger"], s["distract_warn"] + 0.1)
    s["yaw_return"] = min(s["yaw_return"], s["yaw_limit"] - 1.0)
    s["thresholds"] = {k: round(min(max(float(v), 0.01), 0.99), 3)
                       for k, v in (s.get("thresholds") or {}).items() if v is not None}
    return s


def update(patch):
    global _current
    with _lock:
        s = {**_load()}
        for k, v in patch.items():
            if k == "thresholds" and isinstance(v, dict):
                th = dict(s["thresholds"])
                for name, val in v.items():
                    if val is None:
                        th.pop(name, None)  # None = กลับไปใช้ค่าจากไฟล์ metrics
                    else:
                        th[name] = val
                s["thresholds"] = th
            elif k in LIMITS:
                s[k] = v
        _current = _validate(s)
        PATH.parent.mkdir(exist_ok=True)
        PATH.write_text(json.dumps(_current, indent=2))
        return {**_current, "thresholds": dict(_current["thresholds"])}


def reset():
    global _current
    with _lock:
        _current = {**DEFAULTS, "thresholds": {}}
        if PATH.exists():
            PATH.unlink()
        return {**_current, "thresholds": {}}
