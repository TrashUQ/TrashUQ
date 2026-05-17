"""
On-device fine-tuning — NumPy only, no TensorFlow required.

Why this design:
  Running a full Keras/TF training loop on the UNO Q MPU (ARM, modest CPU) is
  heavy and fragile. Instead we freeze the TFLite base model and train a tiny
  *calibration head* on top of its class probabilities:

        q = softmax(W · p + b)

  where `p` is the base model's probability vector and `W` (n×n) + `b` (n) are
  the only trainable parameters — n_classes² + n_classes floats total
  (20 floats for the 4-class model). This is what the federated-learning loop
  exchanges with the coordinator.

Training data is the set of user-labeled samples in the local SQLite store
(`label_src = 'user'`). Each image is run once through the frozen TFLite model
to get `p`; the head is then trained with plain SGD + cross-entropy.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path

import numpy as np

from .classifier import Classifier, _softmax
from .config import Config

logger = logging.getLogger(__name__)


def _read_image(path: Path):
    import cv2
    return cv2.imread(str(path))


class FineTuner:
    """Trains the Classifier's calibration head on locally collected user labels."""

    def __init__(self, cfg: Config, classifier: Classifier) -> None:
        self._cfg = cfg
        self._clf = classifier
        self._labels = cfg.labels
        self._n = len(cfg.labels)
        self._lock = threading.Lock()
        # Start from the classifier's current calibration (identity by default)
        self._w, self._b = classifier.get_calibration()

    # ── data ─────────────────────────────────────────────────────────────────
    def _load_features(self) -> tuple[np.ndarray, np.ndarray]:
        """Run every user-labeled image through the frozen base model once.

        Returns (P, y): P is (N, n) base probabilities, y is (N,) label indices.
        """
        conn = sqlite3.connect(str(self._cfg.db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT image_path, label FROM samples WHERE label_src = 'user'"
        ).fetchall()
        conn.close()

        feats: list[np.ndarray] = []
        ys: list[int] = []
        for row in rows:
            if row["label"] not in self._labels:
                continue
            img = _read_image(Path(row["image_path"]))
            if img is None:
                continue
            feats.append(self._clf.predict_proba(img))
            ys.append(self._labels.index(row["label"]))

        if not feats:
            return np.empty((0, self._n), dtype=np.float32), np.empty(0, dtype=np.int64)
        return np.stack(feats), np.array(ys, dtype=np.int64)

    def num_user_samples(self) -> int:
        conn = sqlite3.connect(str(self._cfg.db_path))
        n = conn.execute("SELECT COUNT(*) FROM samples WHERE label_src = 'user'").fetchone()[0]
        conn.close()
        return int(n)

    # ── training ─────────────────────────────────────────────────────────────
    def run_round(self) -> dict | None:
        """Train the calibration head one round. Returns metrics+weights, or None."""
        with self._lock:
            P, y = self._load_features()
            if len(P) < 2:
                logger.info("FineTuner: not enough user samples (%d), skipping", len(P))
                return None

            w = self._w.astype(np.float64).copy()
            b = self._b.astype(np.float64).copy()
            lr = self._cfg.fl_learning_rate
            n_epochs = self._cfg.fl_epochs
            batch = max(1, self._cfg.fl_batch_size)
            rng = np.random.default_rng(0)

            final_loss = 0.0
            for _ in range(n_epochs):
                order = rng.permutation(len(P))
                for start in range(0, len(P), batch):
                    idx = order[start : start + batch]
                    pb, yb = P[idx], y[idx]
                    # Forward
                    logits = pb @ w.T + b               # (B, n)
                    q = np.apply_along_axis(_softmax, 1, logits)
                    # Cross-entropy gradient
                    onehot = np.eye(self._n)[yb]
                    dlogits = (q - onehot) / len(idx)    # (B, n)
                    dw = dlogits.T @ pb                  # (n, n)
                    db = dlogits.sum(axis=0)             # (n,)
                    w -= lr * dw
                    b -= lr * db

            # Final epoch metrics over the full set
            logits = P @ w.T + b
            q = np.apply_along_axis(_softmax, 1, logits)
            eps = 1e-9
            final_loss = float(-np.mean(np.log(q[np.arange(len(y)), y] + eps)))
            final_acc = float(np.mean(np.argmax(q, axis=1) == y))

            self._w = w.astype(np.float32)
            self._b = b.astype(np.float32)
            # Install the freshly trained head so inference uses it immediately
            self._clf.set_calibration(self._w, self._b)

            weights = self._flatten()
            logger.info(
                "FineTuner: round done — n=%d loss=%.4f acc=%.3f weights=%d",
                len(P), final_loss, final_acc, len(weights),
            )
            return {
                "num_samples": int(len(P)),
                "local_weights": weights,
                "local_loss": final_loss,
                "local_accuracy": final_acc,
            }

    # ── FL weight exchange ───────────────────────────────────────────────────
    def head_weight_length(self) -> int:
        return self._n * self._n + self._n

    def _flatten(self) -> list[float]:
        return self._w.flatten().tolist() + self._b.flatten().tolist()

    def apply_global_weights(self, weights: list[float]) -> None:
        """Install an aggregated calibration head received from the coordinator."""
        expected = self.head_weight_length()
        if len(weights) != expected:
            logger.warning(
                "Global weight length %d != expected %d — skipping apply",
                len(weights), expected,
            )
            return
        flat = np.asarray(weights, dtype=np.float32)
        # The coordinator initialises its global model to all-zeros. A zero W
        # makes softmax(W·p + b) uniform and destroys the classifier, so treat
        # an all-zero vector as "no global model yet" and keep the local head.
        if not np.any(flat):
            logger.info("Global weights are all-zero (no aggregated model yet) — keeping local head")
            return
        with self._lock:
            self._w = flat[: self._n * self._n].reshape(self._n, self._n)
            self._b = flat[self._n * self._n :].reshape(self._n)
            self._clf.set_calibration(self._w, self._b)
        logger.info("Applied global calibration head (%d floats)", expected)
