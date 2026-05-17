"""TFLite inference + majority-vote ensemble over a burst of frames.

Optionally applies a small learned *calibration head* (an n×n linear layer +
bias on top of the base model's class probabilities). The calibration head is
what the on-device fine-tuner trains and what travels through the federated
learning loop — it is tiny (n_classes² + n_classes floats) so it needs no
TensorFlow on the edge device.
"""
import logging
import threading
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    # Fall back to full TF when running on a dev machine
    import tensorflow.lite as tflite  # type: ignore[no-reattr]


@dataclass
class Prediction:
    label: str
    confidence: float  # confidence of the winning vote
    votes: dict[str, int]  # per-label vote count across burst


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - np.max(x))
    return e / np.sum(e)


class Classifier:
    def __init__(self, model_path: Path, labels: list[str]) -> None:
        if not model_path.exists():
            raise FileNotFoundError(f"TFLite model not found: {model_path}")
        self._labels = labels
        self._n = len(labels)
        self._interpreter = tflite.Interpreter(model_path=str(model_path))
        self._interpreter.allocate_tensors()

        input_details = self._interpreter.get_input_details()
        self._input_idx = input_details[0]["index"]
        self._input_shape = input_details[0]["shape"]  # [1, H, W, C]
        self._input_dtype = input_details[0]["dtype"]

        output_details = self._interpreter.get_output_details()
        self._output_idx = output_details[0]["index"]

        h, w = int(self._input_shape[1]), int(self._input_shape[2])
        self._input_h = h
        self._input_w = w

        # Calibration head: q = softmax(W @ p + b). Identity init = near no-op.
        self._cal_lock = threading.Lock()
        self._cal_w: np.ndarray = np.eye(self._n, dtype=np.float32)
        self._cal_b: np.ndarray = np.zeros(self._n, dtype=np.float32)
        self._cal_active = False

        logger.info("Classifier loaded: input=%dx%d labels=%s", w, h, labels)

    # ── calibration head ─────────────────────────────────────────────────────
    def set_calibration(self, w: np.ndarray, b: np.ndarray) -> None:
        """Install a trained calibration head (called by the fine-tuner / FL client)."""
        with self._cal_lock:
            self._cal_w = np.asarray(w, dtype=np.float32).reshape(self._n, self._n)
            self._cal_b = np.asarray(b, dtype=np.float32).reshape(self._n)
            self._cal_active = True
        logger.info("Calibration head installed")

    def get_calibration(self) -> tuple[np.ndarray, np.ndarray]:
        with self._cal_lock:
            return self._cal_w.copy(), self._cal_b.copy()

    def _apply_calibration(self, probs: np.ndarray) -> np.ndarray:
        if not self._cal_active:
            return probs
        with self._cal_lock:
            return _softmax(self._cal_w @ probs + self._cal_b)

    # ── inference ────────────────────────────────────────────────────────────
    def predict_proba(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Raw base-model probabilities for a single BGR frame (pre-calibration)."""
        import cv2

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (self._input_w, self._input_h))
        tensor = resized.astype(self._input_dtype)
        if self._input_dtype == np.float32:
            # MobileNetV2 expects [-1, 1] (same as keras preprocess_input)
            tensor = (tensor / 127.5) - 1.0
        tensor = np.expand_dims(tensor, axis=0)

        self._interpreter.set_tensor(self._input_idx, tensor)
        self._interpreter.invoke()
        return np.asarray(self._interpreter.get_tensor(self._output_idx)[0], dtype=np.float32)

    def predict_frame(self, frame_bgr: np.ndarray) -> tuple[str, float]:
        """Run inference on a single BGR frame. Returns (label, confidence).

        Applies the calibration head if one has been installed.
        """
        probs = self._apply_calibration(self.predict_proba(frame_bgr))
        idx = int(np.argmax(probs))
        return self._labels[idx], float(probs[idx])

    def predict_burst(self, frames: list[np.ndarray]) -> Prediction:
        """Majority-vote ensemble over a burst of frames."""
        votes: list[str] = []
        confidences: dict[str, list[float]] = {label: [] for label in self._labels}

        for frame in frames:
            label, conf = self.predict_frame(frame)
            votes.append(label)
            confidences[label].append(conf)

        tally = Counter(votes)
        winner = tally.most_common(1)[0][0]
        win_conf = float(np.mean(confidences[winner])) if confidences[winner] else 0.0

        return Prediction(
            label=winner,
            confidence=win_conf,
            votes=dict(tally),
        )
