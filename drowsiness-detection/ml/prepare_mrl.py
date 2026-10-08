"""prepare_mrl.py - อ่าน MRL Eye Dataset -> preprocess -> แบ่ง train/val/test ตามตัวบุคคล

    python ml/prepare_mrl.py --root path/to/mrl-eye-dataset --out data/mrl

ชื่อไฟล์ MRL: s0001_00001_0_0_0_0_0_01.png
    subject_image_gender_glasses_eyestate_reflections_lighting_sensor   (eyestate: 0 = closed, 1 = open)

แบ่งตาม subject เพื่อกัน data leakage (คนเดียวกันห้ามอยู่ทั้ง train และ test)
แต่ละคนมีจำนวนภาพไม่เท่ากันมาก จึงสุ่มจัดกลุ่มหลายพันแบบ แล้วเลือกแบบที่
(1) สัดส่วนจำนวนภาพใกล้ 70/15/15 และ (2) สัดส่วนตาปิดในแต่ละ split ใกล้กับภาพรวมมากที่สุด
"""
import argparse
import json
import random
from pathlib import Path

import cv2
import numpy as np

from preprocess import IMG_SIZE, preprocess_uint8

EXTS = {".png", ".jpg", ".jpeg"}
SPLITS = ("train", "val", "test")
TARGET = {"train": 0.70, "val": 0.15, "test": 0.15}


def parse_name(path: Path):
    parts = path.stem.split("_")
    if len(parts) < 5 or not parts[0].startswith("s"):
        return None
    try:
        return {"subject": parts[0], "gender": int(parts[2]), "glasses": int(parts[3]), "state": int(parts[4])}
    except ValueError:
        return None


def choose_split(items, seed=42, trials=20000, min_subjects=3):
    """คืน dict subject -> split ที่สมดุลทั้งจำนวนภาพและสัดส่วนคลาส"""
    per = {}
    for it in items:
        c = per.setdefault(it["subject"], [0, 0])  # [ภาพทั้งหมด, ตาปิด]
        c[0] += 1
        c[1] += it["state"] == 0
    subjects = sorted(per)
    total = sum(v[0] for v in per.values())
    overall_closed = sum(v[1] for v in per.values()) / total
    rng = random.Random(seed)

    best, best_score = None, float("inf")
    for _ in range(trials):
        order = subjects[:]
        rng.shuffle(order)
        assign, n, closed, cum = {}, {s: 0 for s in SPLITS}, {s: 0 for s in SPLITS}, 0
        for subj in order:
            frac = cum / total
            split = "train" if frac < TARGET["train"] else "val" if frac < TARGET["train"] + TARGET["val"] else "test"
            assign[subj] = split
            n[split] += per[subj][0]
            closed[split] += per[subj][1]
            cum += per[subj][0]
        counts = {s: sum(1 for v in assign.values() if v == s) for s in SPLITS}
        if min(counts.values()) < min_subjects:
            continue
        score = sum(abs(n[s] / total - TARGET[s]) for s in SPLITS)
        score += sum(abs(closed[s] / n[s] - overall_closed) for s in SPLITS)
        if score < best_score:
            best, best_score = assign, score
    if best is None:
        raise SystemExit("จัดกลุ่มไม่ได้ ลองลด --min-subjects")
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", default="data/mrl")
    ap.add_argument("--size", type=int, default=IMG_SIZE)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--trials", type=int, default=20000)
    ap.add_argument("--min-subjects", type=int, default=3, help="จำนวนคนขั้นต่ำในแต่ละ split")
    args = ap.parse_args()

    items = []
    for p in Path(args.root).rglob("*"):
        if p.suffix.lower() in EXTS:
            meta = parse_name(p)
            if meta:
                meta["path"] = p
                items.append(meta)
    if not items:
        raise SystemExit("ไม่พบไฟล์ที่ชื่อตรงรูปแบบ MRL (sXXXX_..._eyestate_...) ตรวจ --root และชื่อไฟล์")
    print(f"พบ {len(items)} ภาพ จาก {len({i['subject'] for i in items})} subjects")

    split_of = choose_split(items, args.seed, args.trials, args.min_subjects)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    buckets = {s: {"x": [], "y": [], "glasses": [], "subject": []} for s in SPLITS}

    for i, it in enumerate(items):
        img = cv2.imread(str(it["path"]), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        b = buckets[split_of[it["subject"]]]
        b["x"].append(preprocess_uint8(img, args.size))
        b["y"].append(it["state"])
        b["glasses"].append(it["glasses"])
        b["subject"].append(it["subject"])
        if (i + 1) % 10000 == 0:
            print(f"  ประมวลผลแล้ว {i + 1}/{len(items)}")

    total = sum(len(b["y"]) for b in buckets.values())
    summary = {}
    for name, b in buckets.items():
        x = np.stack(b["x"]).astype("uint8")
        y = np.array(b["y"], dtype="uint8")  # 0 closed, 1 open (ตาม MRL)
        np.savez_compressed(out / f"{name}.npz", x=x, y=y, glasses=np.array(b["glasses"], dtype="uint8"))
        summary[name] = {"images": int(len(y)), "subjects": sorted(set(b["subject"])),
                         "closed": int((y == 0).sum()), "open": int((y == 1).sum())}
        print(f"{name}: {len(y)} ภาพ ({len(y) / total:.1%}) | {len(summary[name]['subjects'])} คน | "
              f"closed={summary[name]['closed']} ({summary[name]['closed'] / len(y):.1%}) open={summary[name]['open']}")

    (out / "split_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"บันทึกที่ {out}/")


if __name__ == "__main__":
    main()