"""Merge TrashNet + TrashBox and build train/val/test tf.data pipelines."""
import random
from pathlib import Path

import tensorflow as tf

from config import BATCH_SIZE, CLASSES, IMG_SIZE, SEED, TRASHBOX_DIR, TRASHNET_DIR


def _collect_paths(root: Path, classes: list[str]) -> dict[str, list[Path]]:
    """Return {class: [image_path, ...]} for every class folder found under root."""
    result: dict[str, list[Path]] = {}
    for cls in classes:
        folder = root / cls
        if not folder.exists():
            print(f"  [WARN] {folder} not found, skipping")
            continue
        images = [
            p for p in folder.iterdir()
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
            and p.stat().st_size > 0
        ]
        result[cls] = images
    return result


def collect_all_paths() -> dict[str, list[Path]]:
    """Merge TrashNet + TrashBox paths per class."""
    print("Scanning TrashNet …")
    tn = _collect_paths(TRASHNET_DIR, CLASSES)
    print("Scanning TrashBox …")
    tb = _collect_paths(TRASHBOX_DIR, CLASSES)

    merged: dict[str, list[Path]] = {}
    for cls in CLASSES:
        merged[cls] = tn.get(cls, []) + tb.get(cls, [])
        print(f"  {cls}: {len(tn.get(cls, []))} + {len(tb.get(cls, []))} = {len(merged[cls])}")
    return merged


def split_paths(
    merged: dict[str, list[Path]],
    val_split: float,
    test_split: float,
) -> tuple[list[tuple[Path, int]], list[tuple[Path, int]], list[tuple[Path, int]]]:
    """Stratified split → (train, val, test) lists of (path, label_index)."""
    rng = random.Random(SEED)
    train_items: list[tuple[Path, int]] = []
    val_items: list[tuple[Path, int]] = []
    test_items: list[tuple[Path, int]] = []

    for idx, cls in enumerate(CLASSES):
        paths = merged[cls][:]
        rng.shuffle(paths)
        n = len(paths)
        n_test = int(n * test_split)
        n_val = int(n * val_split)
        test_items += [(p, idx) for p in paths[:n_test]]
        val_items += [(p, idx) for p in paths[n_test: n_test + n_val]]
        train_items += [(p, idx) for p in paths[n_test + n_val:]]

    rng.shuffle(train_items)
    return train_items, val_items, test_items


def _load_and_preprocess(path: tf.Tensor, label: tf.Tensor) -> tuple[tf.Tensor, tf.Tensor]:
    raw = tf.io.read_file(path)
    img = tf.image.decode_image(raw, channels=3, expand_animations=False)
    img = tf.image.resize(img, [IMG_SIZE, IMG_SIZE])
    img = tf.keras.applications.mobilenet_v2.preprocess_input(img)
    return img, label


def _augment(img: tf.Tensor, label: tf.Tensor) -> tuple[tf.Tensor, tf.Tensor]:
    img = tf.image.random_flip_left_right(img)
    img = tf.image.random_brightness(img, max_delta=0.2)
    img = tf.image.random_contrast(img, 0.8, 1.2)
    img = tf.image.random_saturation(img, 0.8, 1.2)
    img = tf.clip_by_value(img, -1.0, 1.0)
    return img, label


def build_dataset(
    items: list[tuple[Path, int]],
    augment: bool = False,
    shuffle: bool = False,
) -> tf.data.Dataset:
    paths = [str(p) for p, _ in items]
    labels = [l for _, l in items]

    ds = tf.data.Dataset.from_tensor_slices((paths, labels))
    if shuffle:
        ds = ds.shuffle(buffer_size=len(items), seed=SEED)
    ds = ds.map(_load_and_preprocess, num_parallel_calls=tf.data.AUTOTUNE)
    ds = ds.apply(tf.data.experimental.ignore_errors())
    if augment:
        ds = ds.map(_augment, num_parallel_calls=tf.data.AUTOTUNE)
    ds = ds.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)
    return ds


def load_datasets(
    val_split: float = 0.15,
    test_split: float = 0.15,
) -> tuple[tf.data.Dataset, tf.data.Dataset, tf.data.Dataset]:
    merged = collect_all_paths()
    train_items, val_items, test_items = split_paths(merged, val_split, test_split)
    print(f"\nSplit sizes — train: {len(train_items)}, val: {len(val_items)}, test: {len(test_items)}")

    train_ds = build_dataset(train_items, augment=True, shuffle=True)
    val_ds = build_dataset(val_items)
    test_ds = build_dataset(test_items)
    return train_ds, val_ds, test_ds
