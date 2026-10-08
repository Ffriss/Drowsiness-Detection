"""arch.py - สถาปัตยกรรมโมเดลทั้ง 3 ตัว (input เดียวกัน: 64x64x1 ช่วง 0-1, output = P(closed))"""
import tensorflow as tf
from tensorflow.keras import layers, models

IMG_SIZE = 64
BACKBONE_INPUT = 96
LABELS = {"custom_cnn": "CNN", "mobilenetv2": "MobileNetV2", "resnet50": "ResNet50"}


def build_custom_cnn(weights=None):
    inp = layers.Input((IMG_SIZE, IMG_SIZE, 1))
    x = inp
    for f in (32, 64, 128):
        for _ in range(2):
            x = layers.Conv2D(f, 3, padding="same", use_bias=False)(x)
            x = layers.BatchNormalization()(x)
            x = layers.ReLU()(x)
        x = layers.MaxPooling2D()(x)
        x = layers.Dropout(0.2)(x)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(64, activation="relu")(x)
    x = layers.Dropout(0.4)(x)
    out = layers.Dense(1, activation="sigmoid")(x)
    return models.Model(inp, out, name="custom_cnn"), None


def _build_pretrained(kind, weights):
    inp = layers.Input((IMG_SIZE, IMG_SIZE, 1))
    x = layers.Resizing(BACKBONE_INPUT, BACKBONE_INPUT)(inp)
    x = layers.Concatenate()([x, x, x])
    shape = (BACKBONE_INPUT, BACKBONE_INPUT, 3)
    if kind == "mobilenetv2":
        x = layers.Rescaling(2.0, offset=-1.0)(x)  # -> [-1, 1]
        base = tf.keras.applications.MobileNetV2(input_shape=shape, include_top=False, weights=weights)
    else:
        x = layers.Rescaling(255.0)(x)
        x = layers.Normalization(axis=-1, mean=[103.939, 116.779, 123.68], variance=[1.0, 1.0, 1.0])(x)
        base = tf.keras.applications.ResNet50(input_shape=shape, include_top=False, weights=weights)
    base.trainable = False
    x = base(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.3)(x)
    out = layers.Dense(1, activation="sigmoid")(x)
    return models.Model(inp, out, name=kind), base


def build_mobilenetv2(weights="imagenet"):
    return _build_pretrained("mobilenetv2", weights)


def build_resnet50(weights="imagenet"):
    return _build_pretrained("resnet50", weights)


BUILDERS = {"custom_cnn": build_custom_cnn, "mobilenetv2": build_mobilenetv2, "resnet50": build_resnet50}


def unfreeze_top(base, n_layers=30):
    """ปลดล็อกชั้นบนสุดของ backbone เพื่อ fine-tune (BatchNorm ยังคงถูกล็อก)"""
    base.trainable = True
    for layer in base.layers[:-n_layers]:
        layer.trainable = False
    for layer in base.layers:
        if isinstance(layer, layers.BatchNormalization):
            layer.trainable = False
