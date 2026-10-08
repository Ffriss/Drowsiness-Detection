"""evaluate_folder.py - วัดผลโมเดลทั้ง 3 ตัวบนภาพตาจาก webcam จริง (data/webcam_test/{open,closed})

    python ml/evaluate_folder.py --dir data/webcam_test

ใช้ threshold เดียวกับที่เลือกจาก validation ตอนเทรน ผลบันทึกที่ models/<name>_webcam.json
(หน้า Model Comparison ใน dashboard จะแสดงผลชุดนี้เทียบกับ test set ปกติ)
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf

from arch import LABELS
from evalutil import compute_metrics
from preprocess import preprocess_uint8, to_model_input

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"

ap = argparse.ArgumentParser()
ap.add_argument("--dir", default="data/webcam_test")
args = ap.parse_args()

xs, ys = [], []
for label, folder in ((0, "open"), (1, "closed")):  # 1 = closed (positive)
    for p in sorted((Path(args.dir) / folder).glob("*.png")):
        img = cv2.imread(str(p))
        if img is not None:
            xs.append(to_model_input(preprocess_uint8(img)))
            ys.append(label)
if not xs:
    raise SystemExit(f"ไม่พบภาพใน {args.dir}/open และ {args.dir}/closed (เก็บด้วย ml/collect_webcam.py)")
x, y = np.stack(xs), np.array(ys)
print(f"ภาพทดสอบ: {len(y)} (closed={int(y.sum())}, open={int((1 - y).sum())})")

for name, label in LABELS.items():
    model_path = MODELS_DIR / f"{name}.keras"
    if not model_path.exists():
        print(f"ข้าม {label}: ยังไม่ได้เทรน")
        continue
    meta_path = MODELS_DIR / f"{name}_metrics.json"
    thr = json.loads(meta_path.read_text())["threshold"] if meta_path.exists() else 0.5
    model = tf.keras.models.load_model(model_path, compile=False)
    p = model.predict(x, verbose=0).ravel()
    m = compute_metrics(y, p, thr)
    (MODELS_DIR / f"{name}_webcam.json").write_text(json.dumps(m, indent=2))
    print(f"{label}: acc={m['accuracy']:.4f} precision={m['precision']:.4f} recall={m['recall']:.4f} f1={m['f1']:.4f}")
