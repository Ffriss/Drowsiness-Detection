"""set_threshold.py - ดูผลของ threshold แต่ละค่า แล้วตั้งค่าใหม่พร้อมคำนวณ metrics บน test set ใหม่ให้ตรงกัน

1) ดูตาราง (ใช้ validation set เลือกค่า ไม่ใช้ test เพื่อไม่ให้ผลในรายงานดูดีเกินจริง)
    python ml/set_threshold.py --model custom_cnn --sweep

2) ตั้งค่าใหม่ (คำนวณ accuracy/precision/recall/F1 บน test ใหม่ แล้วบันทึกลง models/<model>_metrics.json)
    python ml/set_threshold.py --model custom_cnn --threshold 0.35

ค่าเดิมที่ได้จากตอนเทรนจะถูกเก็บไว้ที่ "threshold_val" ใช้คืนค่าได้ด้วย --threshold <ค่านั้น>
หลังตั้งค่าใหม่ ต้องปิดแล้วเปิด backend ใหม่ ค่าจึงจะมีผล
"""
import argparse
import json
from pathlib import Path

import numpy as np
import tensorflow as tf

from arch import LABELS
from evalutil import compute_metrics

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"


def load_split(data_dir, name):
    z = np.load(Path(data_dir) / f"{name}.npz")
    x = z["x"].astype("float32")[..., None] / 255.0
    y = (1 - z["y"]).astype(int)  # 1 = ตาปิด
    return x, y, z["glasses"].astype(bool)


def predict(model, x):
    return model.predict(x, batch_size=256, verbose=0).ravel()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=list(LABELS))
    ap.add_argument("--data", default="data/mrl")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sweep", action="store_true", help="แสดงผลบน validation ที่ threshold ต่าง ๆ")
    g.add_argument("--threshold", type=float, help="ตั้ง threshold ใหม่ (0-1)")
    args = ap.parse_args()

    meta_path = MODELS_DIR / f"{args.model}_metrics.json"
    meta = json.loads(meta_path.read_text())
    original = meta.get("threshold_val", meta["threshold"])
    print(f"threshold ตอนนี้ = {meta['threshold']} | ค่าเดิมจากตอนเทรน = {original}")
    model = tf.keras.models.load_model(MODELS_DIR / f"{args.model}.keras", compile=False)

    if args.sweep:
        x, y, _ = load_split(args.data, "val")
        p = predict(model, x)
        print("\nผลบน validation set:")
        print(f"{'thr':>5} {'acc':>7} {'prec':>7} {'recall':>7} {'f1':>7}  ตาเปิดถูกนับว่าปิด  ตาปิดที่พลาด")
        for t in [0.02, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
            m = compute_metrics(y, p, t)
            (tn, fp), (fn, tp) = m["confusion_matrix"]
            print(f"{t:>5.2f} {m['accuracy']:>7.2%} {m['precision']:>7.2%} {m['recall']:>7.2%} {m['f1']:>7.2%}"
                  f"  {fp:>8} ({fp / max(tn + fp, 1):.1%})  {fn:>8} ({fn / max(fn + tp, 1):.1%})")
        print("\nเลือกค่าจากตารางนี้ แล้วรันอีกครั้งด้วย --threshold <ค่า>")
        return

    t = args.threshold
    if not 0.0 < t < 1.0:
        raise SystemExit("threshold ต้องอยู่ระหว่าง 0 ถึง 1")
    x, y, glasses = load_split(args.data, "test")
    p = predict(model, x)
    old = compute_metrics(y, p, meta["threshold"])
    new = compute_metrics(y, p, t)

    print(f"\nผลบน test set ({new['n']} ภาพ):")
    print(f"{'':>10} {'acc':>8} {'prec':>8} {'recall':>8} {'f1':>8}")
    for label, m, thr in (("เดิม", old, meta["threshold"]), ("ใหม่", new, t)):
        print(f"{label} {thr:>5.2f} {m['accuracy']:>8.2%} {m['precision']:>8.2%} {m['recall']:>8.2%} {m['f1']:>8.2%}")

    meta["threshold_val"] = original
    meta["threshold"] = round(t, 3)
    meta["test"] = new
    for key, mask in (("test_glasses", glasses), ("test_no_glasses", ~glasses)):
        if mask.sum() > 0:
            m = compute_metrics(y[mask], p[mask], t)
            meta[key] = {"accuracy": m["accuracy"], "f1": m["f1"], "n": m["n"]}
    meta_path.write_text(json.dumps(meta, indent=2))
    print(f"\nบันทึก threshold = {t} ลง {meta_path.name} แล้ว ปิดและเปิด backend ใหม่เพื่อให้มีผล")


if __name__ == "__main__":
    main()
