"""eyecrop.py - ตัด ROI ดวงตาจาก MediaPipe Face Mesh (ใช้ร่วมกันทั้งตอนเก็บข้อมูล webcam และ backend)"""
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]


def crop_eye(frame, landmarks, idx, margin=0.4):
    """คืน (crop_bgr, (x, y, w, h) แบบ normalized 0-1) หรือ None ถ้าตัดไม่ได้"""
    h, w = frame.shape[:2]
    xs = [landmarks[i].x * w for i in idx]
    ys = [landmarks[i].y * h for i in idx]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    half = max(max(xs) - min(xs), max(ys) - min(ys)) / 2 * (1 + margin)
    x0, y0 = int(max(cx - half, 0)), int(max(cy - half, 0))
    x1, y1 = int(min(cx + half, w)), int(min(cy + half, h))
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    return frame[y0:y1, x0:x1], (x0 / w, y0 / h, (x1 - x0) / w, (y1 - y0) / h)


def extract_eyes(frame, face_landmarks, margin=0.4):
    """คืน list ของ (crop, box) สำหรับตาซ้ายและขวา (เฉพาะที่ตัดได้)"""
    lm = face_landmarks.landmark
    out = []
    for idx in (LEFT_EYE, RIGHT_EYE):
        r = crop_eye(frame, lm, idx, margin)
        if r is not None:
            out.append(r)
    return out
