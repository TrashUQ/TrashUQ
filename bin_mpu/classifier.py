"""TFLite inference + majority-vote ensemble over a burst of frames."""
import logging
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


class Classifier:
    def __init__(self, model_path: Path, labels: list[str]) -> None:
        if not model_path.exists():
            raise FileNotFoundError(f"TFLite model not found: {model_path}")
        self._labels = labels
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
        logger.info("Classifier loaded: input=%dx%d labels=%s", w, h, labels)

    def predict_frame(self, frame_bgr: np.ndarray) -> tuple[str, float]:
        """Run inference on a single BGR frame. Returns (label, confidence)."""
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

        output = self._interpreter.get_tensor(self._output_idx)[0]
        idx = int(np.argmax(output))
        return self._labels[idx], float(output[idx])

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
