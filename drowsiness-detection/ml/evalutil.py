"""evalutil.py - ฟังก์ชันคำนวณ metrics จริง (positive class = ตาปิด = 1)"""
import numpy as np
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, precision_score, recall_score,
                             roc_auc_score)


def compute_metrics(y_true, p_closed, thr):
    y_true = np.asarray(y_true).astype(int)
    pred = (np.asarray(p_closed) >= thr).astype(int)
    cm = confusion_matrix(y_true, pred, labels=[0, 1])  # [[TN, FP], [FN, TP]]; 0 = open, 1 = closed
    auc = float(roc_auc_score(y_true, p_closed)) if len(set(y_true.tolist())) > 1 else None
    return {
        "accuracy": float(accuracy_score(y_true, pred)),
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "auc": auc,
        "confusion_matrix": cm.tolist(),
        "n": int(len(y_true)),
    }


def best_threshold(y_true, p_closed):
    """เลือก threshold ที่ให้ F1 (ของคลาสตาปิด) สูงสุดบน validation set"""
    best_t, best_f1 = 0.5, -1.0
    for t in np.linspace(0.05, 0.95, 91):
        f1 = f1_score(y_true, (p_closed >= t).astype(int), zero_division=0)
        if f1 > best_f1:
            best_t, best_f1 = float(t), float(f1)
    return best_t
