"""preview_compare.py - วางภาพตาจาก dataset เทียบกับภาพจาก webcam (หลัง preprocess) เพื่อตรวจ domain gap ด้วยตา

    python ml/preview_compare.py --mrl data/mrl/test.npz --webcam data/webcam_test
บันทึกเป็น preview_compare.png : แถว 1-2 = MRL (เปิด/ปิด), แถว 3-4 = webcam (เปิด/ปิด)
"""
import argparse
import random
from pathlib import Path

import cv2
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from preprocess import preprocess_uint8

ap = argparse.ArgumentParser()
ap.add_argument("--mrl", default="data/mrl/test.npz")
ap.add_argument("--webcam", default="data/webcam_test")
ap.add_argument("--n", type=int, default=8)
ap.add_argument("--out", default="preview_compare.png")
args = ap.parse_args()

z = np.load(args.mrl)
rows = []
for state in (1, 0):  # MRL: 1 = open, 0 = closed
    idx = np.where(z["y"] == state)[0]
    pick = random.sample(list(idx), min(args.n, len(idx)))
    rows.append(("MRL " + ("open" if state else "closed"), [z["x"][i] for i in pick]))
for folder in ("open", "closed"):
    files = sorted((Path(args.webcam) / folder).glob("*.png"))
    pick = random.sample(files, min(args.n, len(files)))
    rows.append(("webcam " + folder, [preprocess_uint8(cv2.imread(str(f))) for f in pick]))

fig, axes = plt.subplots(4, args.n, figsize=(args.n * 1.4, 6.4))
for r, (title, imgs) in enumerate(rows):
    for c in range(args.n):
        ax = axes[r][c]
        ax.axis("off")
        if c < len(imgs):
            ax.imshow(imgs[c], cmap="gray", vmin=0, vmax=255)
        if c == 0:
            ax.set_title(title, loc="left", fontsize=9)
plt.tight_layout()
plt.savefig(args.out, dpi=120)
print(f"บันทึก {args.out}")
