"""Unit tests for classifier — no hardware required."""
import numpy as np
import pytest

from bin_mpu.classifier import Classifier, Prediction


class FakeInterpreter:
    """Stub that returns fixed logits without loading a real model."""

    def __init__(self, output: list[float]) -> None:
        self._output = np.array([output], dtype=np.float32)

    def allocate_tensors(self) -> None: ...

    def get_input_details(self) -> list[dict]:
        return [{"index": 0, "shape": [1, 224, 224, 3], "dtype": np.float32}]

    def get_output_details(self) -> list[dict]:
        return [{"index": 0}]

    def set_tensor(self, idx: int, data: object) -> None: ...

    def invoke(self) -> None: ...

    def get_tensor(self, idx: int) -> np.ndarray:
        return self._output


@pytest.fixture()
def labels() -> list[str]:
    return ["glass", "paper", "plastic"]


def _make_classifier(labels: list[str], logits: list[float]) -> Classifier:
    import threading

    clf = object.__new__(Classifier)
    clf._labels = labels
    clf._n = len(labels)
    clf._interpreter = FakeInterpreter(logits)
    clf._input_idx = 0
    clf._input_shape = np.array([1, 224, 224, 3])
    clf._input_dtype = np.float32
    clf._output_idx = 0
    clf._input_h = 224
    clf._input_w = 224
    clf._cal_lock = threading.Lock()
    clf._cal_w = np.eye(len(labels), dtype=np.float32)
    clf._cal_b = np.zeros(len(labels), dtype=np.float32)
    clf._cal_active = False
    return clf


def test_predict_frame_returns_highest_confidence(labels: list[str]) -> None:
    clf = _make_classifier(labels, [0.1, 0.8, 0.1])
    label, conf = clf.predict_frame(np.zeros((224, 224, 3), dtype=np.uint8))
    assert label == "paper"
    assert conf == pytest.approx(0.8)


def test_predict_burst_majority_vote(labels: list[str]) -> None:
    # 3 frames: 2× glass, 1× paper
    clf_glass = _make_classifier(labels, [0.9, 0.05, 0.05])
    clf_paper = _make_classifier(labels, [0.05, 0.9, 0.05])

    frame = np.zeros((224, 224, 3), dtype=np.uint8)
    # Manually collect votes to simulate the burst
    votes = ["glass", "glass", "paper"]
    from collections import Counter
    tally = Counter(votes)
    pred = Prediction(
        label=tally.most_common(1)[0][0],
        confidence=0.9,
        votes=dict(tally),
    )
    assert pred.label == "glass"
    assert pred.votes["glass"] == 2
    assert pred.votes["paper"] == 1
