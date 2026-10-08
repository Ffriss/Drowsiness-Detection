"""collect_webcam.py - เก็บภาพตาจาก webcam จริงเพื่อใช้เป็น test set แยก (ห้ามเอาไปเทรน)

    python ml/collect_webcam.py --person alice

ปุ่ม: o = เริ่ม/หยุดบันทึกตาเปิด | c = เริ่ม/หยุดบันทึกตาปิด | q = ออก
บันทึกเป็น data/webcam_test/open/*.png และ data/webcam_test/closed/*.png (ภาพ crop ดิบ ยังไม่ผ่าน preprocess)
แนะนำ: เก็บอย่างละ 100-200 ภาพ ต่อคน หลายแสง/ใส่-ไม่ใส่แว่น
"""
import argparse
import time
from pathlib import Path

import cv2
import mediapipe as mp

from eyecrop import extract_eyes

ap = argparse.ArgumentParser()
ap.add_argument("--out", default="data/webcam_test")
ap.add_argument("--person", default="p1")
ap.add_argument("--camera", type=int, default=0)
ap.add_argument("--interval", type=float, default=0.15, help="วินาทีระหว่างการบันทึกแต่ละครั้ง")
args = ap.parse_args()

out = Path(args.out)
for d in ("open", "closed"):
    (out / d).mkdir(parents=True, exist_ok=True)

mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, refine_landmarks=False)
cap = cv2.VideoCapture(args.camera)
mode, last_save, counts = None, 0.0, {"open": 0, "closed": 0}
print("o = บันทึกตาเปิด | c = บันทึกตาปิด | q = ออก")

while True:
    ok, frame = cap.read()
    if not ok:
        break
    res = mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    eyes = extract_eyes(frame, res.multi_face_landmarks[0]) if res.multi_face_landmarks else []

    now = time.time()
    if mode and eyes and now - last_save >= args.interval:
        for side, (crop, _) in zip(("L", "R"), eyes):
            cv2.imwrite(str(out / mode / f"{args.person}_{mode}_{int(now * 1000)}_{side}.png"), crop)
            counts[mode] += 1
        last_save = now

    view = frame.copy()
    h, w = view.shape[:2]
    for _, (x, y, bw, bh) in eyes:
        cv2.rectangle(view, (int(x * w), int(y * h)), (int((x + bw) * w), int((y + bh) * h)), (0, 255, 0), 2)
    cv2.putText(view, f"mode={mode} open={counts['open']} closed={counts['closed']}", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.imshow("collect_webcam", cv2.flip(view, 1))

    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break
    if key == ord("o"):
        mode = None if mode == "open" else "open"
    if key == ord("c"):
        mode = None if mode == "closed" else "closed"

cap.release()
cv2.destroyAllWindows()
print(f"บันทึกแล้ว: open={counts['open']} closed={counts['closed']} -> {out}")
