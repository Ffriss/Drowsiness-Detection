"""preprocess.py - ใช้ไฟล์เดียวนี้ทั้งตอนเตรียมข้อมูล เทรน และตอน inference ใน backend"""
import cv2
import numpy as np

IMG_SIZE = 64
_clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))


def preprocess_uint8(eye_img, size=IMG_SIZE):
    """รับภาพตา (BGR หรือ gray) -> gray + CLAHE + resize, คืน uint8 (size, size)"""
    if eye_img.ndim == 3:
        eye_img = cv2.cvtColor(eye_img, cv2.COLOR_BGR2GRAY)
    g = _clahe.apply(eye_img)
    return cv2.resize(g, (size, size), interpolation=cv2.INTER_AREA)


def to_model_input(g_uint8):
    """uint8 (H, W) -> float32 (H, W, 1) ช่วง 0-1 (โมเดลทุกตัวรับ input รูปแบบนี้)"""
    return (g_uint8.astype("float32") / 255.0)[..., None]
