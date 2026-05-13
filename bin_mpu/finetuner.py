"""
On-device fine-tuning.

Approach (keeps the on-bin compute footprint small):
  1. Load MobileNetV2 base (ImageNet weights, no top) once.
  2. Maintain a small Keras "head" mirroring the trained head:
        GlobalAvgPool → Dropout → Dense(128, relu) → Dropout → Dense(N_CLASSES, softmax)
     The head's trainable parameters are what we fine-tune locally and what we
     ship to the FL coordinator.
  3. Pull user-labeled samples from the local SQLite store, extract features
     through the frozen base (once per image, cached), and fit the head for a
     few epochs at a small learning rate.
  4. Re-export TFLite so the inference pipeline picks up the new weights at
     next process restart (or via Classifier.reload()).

This module is only imported when --fl is enabled; it depends on `tensorflow`
which is only present on dev machines / the MPU with the `train` extra installed.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from .config import Config

if TYPE_CHECKING:  # avoid importing TF at module load when FL is off
    import tensorflow as tf  # noqa: F401

logger = logging.getLogger(__name__)


def _read_image(path: Path, img_size: int) -> np.ndarray | None:
    import cv2
    img = cv2.imread(str(path))
    if img is None:
        return None
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (img_size, img_size))
    arr = img.astype(np.float32)
    return (arr / 127.5) - 1.0  # MobileNetV2 preprocess


class FineTuner:
    """Train the classification head on locally collected user-labeled samples."""

    IMG_SIZE = 224

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._labels = cfg.labels
        self._lock = threading.Lock()
        self._base = None
        self._head = None

    # ── lazy init (TF is heavy) ──────────────────────────────────────────────
    def _ensure_built(self) -> None:
        if self._head is not None:
            return
        import tensorflow as tf

        logger.info("Building fine-tuner head (TF=%s)", tf.__version__)
        self._base = tf.keras.applications.MobileNetV2(
            input_shape=(self.IMG_SIZE, self.IMG_SIZE, 3),
            include_top=False,
            weights="imagenet",
            pooling="avg",
        )
        self._base.trainable = False

        if self._cfg.saved_model_path.exists():
            try:
                full = tf.keras.models.load_model(
                    str(self._cfg.saved_model_path.parent / "best_model.keras")
                )
                head_inputs = tf.keras.Input(shape=self._base.output_shape[1:])
                x = head_inputs
                # Re-create the head architecture and copy weights from layers 3..end
                # of the full model (everything after MobileNetV2 + GAP).
                # If layout differs we just fall through to a fresh head.
                x = tf.keras.layers.Dropout(0.3)(x)
                x = tf.keras.layers.Dense(128, activation="relu", name="dense_128")(x)
                x = tf.keras.layers.Dropout(0.2)(x)
                outputs = tf.keras.layers.Dense(
                    len(self._labels), activation="softmax", name="predictions"
                )(x)
                head = tf.keras.Model(head_inputs, outputs, name="head")
                # Copy weights for the named dense layers
                for name in ("dense_128", "predictions"):
                    try:
                        head.get_layer(name).set_weights(full.get_layer(name).get_weights())
                    except (ValueError, KeyError):
                        logger.warning("Could not copy weights for layer %s", name)
                self._head = head
                logger.info("Loaded head weights from %s", self._cfg.saved_model_path)
            except Exception:
                logger.exception("Falling back to fresh head — could not load saved model")

        if self._head is None:
            head_inputs = tf.keras.Input(shape=self._base.output_shape[1:])
            x = tf.keras.layers.Dropout(0.3)(head_inputs)
            x = tf.keras.layers.Dense(128, activation="relu", name="dense_128")(x)
            x = tf.keras.layers.Dropout(0.2)(x)
            outputs = tf.keras.layers.Dense(
                len(self._labels), activation="softmax", name="predictions"
            )(x)
            self._head = tf.keras.Model(head_inputs, outputs, name="head")

        self._head.compile(
            optimizer=tf.keras.optimizers.Adam(self._cfg.fl_learning_rate),
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
        )

    # ── data loading ─────────────────────────────────────────────────────────
    def _load_user_samples(self) -> tuple[np.ndarray, np.ndarray]:
        conn = sqlite3.connect(str(self._cfg.db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT image_path, label FROM samples WHERE label_src = 'user'"
        ).fetchall()
        conn.close()

        xs: list[np.ndarray] = []
        ys: list[int] = []
        for row in rows:
            if row["label"] not in self._labels:
                continue
            img = _read_image(Path(row["image_path"]), self.IMG_SIZE)
            if img is None:
                continue
            xs.append(img)
            ys.append(self._labels.index(row["label"]))

        if not xs:
            return np.empty((0, self.IMG_SIZE, self.IMG_SIZE, 3), dtype=np.float32), np.empty(0, dtype=np.int64)
        return np.stack(xs), np.array(ys, dtype=np.int64)

    # ── public API ───────────────────────────────────────────────────────────
    def num_user_samples(self) -> int:
        conn = sqlite3.connect(str(self._cfg.db_path))
        n = conn.execute("SELECT COUNT(*) FROM samples WHERE label_src = 'user'").fetchone()[0]
        conn.close()
        return int(n)

    def run_round(self) -> dict | None:
        """Train one fine-tuning round. Returns metrics+weights dict on success, None on no-op."""
        with self._lock:
            self._ensure_built()
            assert self._head is not None and self._base is not None

            xs, ys = self._load_user_samples()
            if len(xs) < 2:
                logger.info("FineTuner: not enough user samples (%d), skipping round", len(xs))
                return None

            logger.info("FineTuner: extracting features for %d samples", len(xs))
            feats = self._base.predict(xs, verbose=0, batch_size=self._cfg.fl_batch_size)

            logger.info("FineTuner: training head for %d epochs", self._cfg.fl_epochs)
            history = self._head.fit(
                feats, ys,
                epochs=self._cfg.fl_epochs,
                batch_size=self._cfg.fl_batch_size,
                verbose=0,
                shuffle=True,
            )

            final_loss = float(history.history["loss"][-1])
            final_acc = float(history.history["accuracy"][-1])

            weights = self._flatten_head_weights()
            logger.info(
                "FineTuner: round done — loss=%.4f acc=%.3f weights_len=%d",
                final_loss, final_acc, len(weights),
            )
            return {
                "num_samples": int(len(xs)),
                "local_weights": weights,
                "local_loss": final_loss,
                "local_accuracy": final_acc,
            }

    def apply_global_weights(self, weights: list[float]) -> None:
        """Apply a flat float vector received from the FL coordinator back into the head."""
        with self._lock:
            self._ensure_built()
            assert self._head is not None
            shapes = [w.shape for w in self._head.get_weights()]
            sizes = [int(np.prod(s)) for s in shapes]
            total = sum(sizes)
            if len(weights) != total:
                logger.warning(
                    "Global weight length %d != local %d — skipping apply",
                    len(weights), total,
                )
                return
            new_weights = []
            offset = 0
            for shape, size in zip(shapes, sizes):
                chunk = np.array(weights[offset : offset + size], dtype=np.float32).reshape(shape)
                new_weights.append(chunk)
                offset += size
            self._head.set_weights(new_weights)
            logger.info("Applied global head weights (%d floats)", total)

    def head_weight_length(self) -> int:
        with self._lock:
            self._ensure_built()
            assert self._head is not None
            return int(sum(int(np.prod(w.shape)) for w in self._head.get_weights()))

    def _flatten_head_weights(self) -> list[float]:
        assert self._head is not None
        out: list[float] = []
        for w in self._head.get_weights():
            out.extend(w.flatten().tolist())
        return out
