"""train.py - เทรน Custom CNN / MobileNetV2 / ResNet50 ด้วย dataset และ split เดียวกัน แล้วบันทึก metrics จริงลง models/

    python ml/train.py --data data/mrl                      # เทรนทั้ง 3 ตัว
    python ml/train.py --data data/mrl --models custom_cnn  # เทรนตัวเดียว
    python ml/train.py --weights none                       # ไม่ใช้ ImageNet weights (กรณีออฟไลน์)

Label ภายใน: 1 = ตาปิด (positive), 0 = ตาเปิด ; โมเดลคืนค่า P(closed)
"""
import argparse
import datetime
import json
import time
from pathlib import Path

import numpy as np
import tensorflow as tf

from arch import BUILDERS, LABELS, unfreeze_top
from evalutil import best_threshold, compute_metrics

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"


def load_split(data_dir, name):
    z = np.load(Path(data_dir) / f"{name}.npz")
    return z["x"], (1 - z["y"]).astype("float32"), z["glasses"]


def augment_batch(x):
    """augmentation ด้วย tf ops ล้วน (ใช้ได้ทั้ง Keras 2 และ 3, ใช้ใน tf.data ได้)
    x: (B, H, W, 1) ช่วง 0-1"""
    b = tf.shape(x)[0]
    size = tf.cast(tf.shape(x)[1], tf.float32)
    c = (size - 1.0) / 2.0

    # หมุน ±15°, zoom 0.9-1.1, เลื่อน ±8%
    theta = tf.random.uniform((b,), -15.0, 15.0) * (3.14159265 / 180.0)
    scale = tf.random.uniform((b,), 0.9, 1.1)
    tx = tf.random.uniform((b,), -0.08, 0.08) * size
    ty = tf.random.uniform((b,), -0.08, 0.08) * size
    cos, sin = tf.cos(theta) / scale, tf.sin(theta) / scale
    zeros = tf.zeros_like(cos)
    transforms = tf.stack([
        cos, sin, c - tx - (cos * c + sin * c),
        -sin, cos, c - ty - (-sin * c + cos * c),
        zeros, zeros,
    ], axis=1)
    x = tf.raw_ops.ImageProjectiveTransformV3(
        images=x, transforms=transforms, output_shape=tf.shape(x)[1:3],
        fill_value=0.0, interpolation="BILINEAR", fill_mode="REFLECT")

    x = tf.image.random_flip_left_right(x)
    x = x + tf.random.uniform((b, 1, 1, 1), -0.3, 0.3)              # ความสว่าง
    mean = tf.reduce_mean(x, axis=[1, 2, 3], keepdims=True)
    x = (x - mean) * tf.random.uniform((b, 1, 1, 1), 0.7, 1.3) + mean  # contrast
    blurred = tf.nn.avg_pool2d(x, 3, 1, "SAME")                       # blur 30% ของภาพ
    x = tf.where(tf.random.uniform((b, 1, 1, 1)) < 0.3, blurred, x)
    x = x + tf.random.normal(tf.shape(x), stddev=0.03)               # noise
    return tf.clip_by_value(x, 0.0, 1.0)


def make_ds(x, y, batch, training):
    ds = tf.data.Dataset.from_tensor_slices((x, y))
    if training:
        ds = ds.shuffle(min(len(x), 20000), seed=42)
    ds = ds.batch(batch)
    ds = ds.map(lambda a, b: (tf.cast(a, tf.float32)[..., None] / 255.0, b), num_parallel_calls=tf.data.AUTOTUNE)
    if training:
        ds = ds.map(lambda a, b: (augment_batch(a), b), num_parallel_calls=tf.data.AUTOTUNE)
    return ds.prefetch(tf.data.AUTOTUNE)


def callbacks():
    return [
        tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=4, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2, min_lr=1e-6),
    ]


def merge_history(histories):
    out = {k: [] for k in ("loss", "val_loss", "accuracy", "val_accuracy")}
    for h in histories:
        for k in out:
            out[k].extend(float(v) for v in h.history.get(k, []))
    return out


def measure_latency(model, x_one):
    for _ in range(10):
        model(x_one, training=False)
    t0 = time.perf_counter()
    for _ in range(100):
        model(x_one, training=False)
    return (time.perf_counter() - t0) / 100 * 1000


def train_one(name, args, data):
    (x_tr, y_tr, _), (x_va, y_va, _), (x_te, y_te, g_te) = data
    print(f"\n===== {LABELS[name]} =====")
    tf.keras.backend.clear_session()
    tf.keras.utils.set_random_seed(42)
    model, base = BUILDERS[name](None if args.weights == "none" else "imagenet")

    ds_tr = make_ds(x_tr, y_tr, args.batch, True)
    ds_va = make_ds(x_va, y_va, args.batch, False)
    n_closed = float(y_tr.sum())
    n_open = float(len(y_tr) - n_closed)
    class_weight = {0: len(y_tr) / (2 * n_open), 1: len(y_tr) / (2 * n_closed)}

    histories = []
    if base is None:
        model.compile(tf.keras.optimizers.Adam(1e-3), "binary_crossentropy", metrics=["accuracy"])
        histories.append(model.fit(ds_tr, validation_data=ds_va, epochs=args.epochs,
                                   class_weight=class_weight, callbacks=callbacks(), verbose=2))
    else:
        model.compile(tf.keras.optimizers.Adam(1e-3), "binary_crossentropy", metrics=["accuracy"])
        histories.append(model.fit(ds_tr, validation_data=ds_va, epochs=args.head_epochs,
                                   class_weight=class_weight, callbacks=callbacks(), verbose=2))
        unfreeze_top(base)
        model.compile(tf.keras.optimizers.Adam(3e-5), "binary_crossentropy", metrics=["accuracy"])
        histories.append(model.fit(ds_tr, validation_data=ds_va, epochs=args.ft_epochs,
                                   class_weight=class_weight, callbacks=callbacks(), verbose=2))

    history = merge_history(histories)
    p_val = model.predict(ds_va, verbose=0).ravel()
    thr = best_threshold(y_va, p_val)
    p_te = model.predict(make_ds(x_te, y_te, args.batch, False), verbose=0).ravel()

    test = compute_metrics(y_te, p_te, thr)
    glasses = g_te.astype(bool)
    subsets = {}
    for key, mask in (("test_glasses", glasses), ("test_no_glasses", ~glasses)):
        if mask.sum() > 0:
            m = compute_metrics(y_te[mask], p_te[mask], thr)
            subsets[key] = {"accuracy": m["accuracy"], "f1": m["f1"], "n": m["n"]}

    MODELS_DIR.mkdir(exist_ok=True)
    path = MODELS_DIR / f"{name}.keras"
    model.save(path)
    x_one = tf.convert_to_tensor(x_te[:1].astype("float32")[..., None] / 255.0)
    gpu = bool(tf.config.list_physical_devices("GPU"))

    result = {
        "name": name, "label": LABELS[name],
        "params": int(model.count_params()),
        "size_mb": round(path.stat().st_size / 1e6, 2),
        "latency_ms": round(measure_latency(model, x_one), 2),
        "device": "GPU" if gpu else "CPU",
        "threshold": round(thr, 3),
        "epochs_trained": len(history["loss"]),
        "dataset": {"train": int(len(y_tr)), "val": int(len(y_va)), "test": int(len(y_te))},
        "test": test, **subsets, "history": history,
        "trained_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    (MODELS_DIR / f"{name}_metrics.json").write_text(json.dumps(result, indent=2))
    print(f"[{LABELS[name]}] test acc={test['accuracy']:.4f} precision={test['precision']:.4f} "
          f"recall={test['recall']:.4f} f1={test['f1']:.4f} thr={thr:.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/mrl")
    ap.add_argument("--models", nargs="+", default=list(BUILDERS), choices=list(BUILDERS))
    ap.add_argument("--epochs", type=int, default=25, help="Custom CNN")
    ap.add_argument("--head-epochs", type=int, default=3, help="pretrained: เทรนเฉพาะหัวก่อน")
    ap.add_argument("--ft-epochs", type=int, default=12, help="pretrained: fine-tune")
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--weights", choices=["imagenet", "none"], default="imagenet")
    args = ap.parse_args()

    data = [load_split(args.data, s) for s in ("train", "val", "test")]
    for name in args.models:
        train_one(name, args, data)


if __name__ == "__main__":
    main()
