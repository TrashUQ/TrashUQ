"""Tests for the NumPy calibration-head fine-tuner — no model/hardware needed."""
import sqlite3
from datetime import datetime, timezone

import numpy as np
import pytest

from bin_mpu.config import Config
from bin_mpu.finetuner import FineTuner
from bin_mpu.sample_store import CREATE_TABLE


class FakeClassifier:
    """Returns a fixed base-prob vector per image path, tracks installed calibration."""

    def __init__(self, labels, prob_by_path):
        self._labels = labels
        self._n = len(labels)
        self._prob_by_path = prob_by_path
        self.calibration = None

    def predict_proba(self, img):
        # img here is actually the path string (see _read_image monkeypatch)
        return np.asarray(self._prob_by_path[img], dtype=np.float32)

    def get_calibration(self):
        return np.eye(self._n, dtype=np.float32), np.zeros(self._n, dtype=np.float32)

    def set_calibration(self, w, b):
        self.calibration = (np.asarray(w), np.asarray(b))


@pytest.fixture()
def cfg(tmp_path):
    return Config(
        db_path=tmp_path / "samples.db",
        image_dir=tmp_path / "images",
        labels=["cardboard", "glass", "paper", "plastic"],
        fl_epochs=200,
        fl_batch_size=4,
        fl_learning_rate=0.5,
    )


def _seed(cfg: Config, rows: list[tuple[str, str]]) -> None:
    cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(cfg.db_path))
    conn.execute(CREATE_TABLE)
    for path, label in rows:
        conn.execute(
            "INSERT INTO samples (id, captured_at, image_path, label, label_src, confidence) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (path, datetime.now(timezone.utc).isoformat(), path, label, "user", 0.4),
        )
    conn.commit()
    conn.close()


def test_head_weight_length(cfg):
    ft = FineTuner(cfg, FakeClassifier(cfg.labels, {}))
    # 4 classes → 4*4 + 4 = 20
    assert ft.head_weight_length() == 20


def test_run_round_learns_to_correct_a_systematic_bias(cfg, monkeypatch):
    # Base model always says "glass" (idx 1) strongly, but the items are "paper" (idx 2).
    # A trained calibration head should learn to remap glass→paper.
    paths = [f"img{i}" for i in range(8)]
    prob_by_path = {p: [0.1, 0.7, 0.1, 0.1] for p in paths}
    _seed(cfg, [(p, "paper") for p in paths])

    monkeypatch.setattr("bin_mpu.finetuner._read_image", lambda path: str(path))
    fake = FakeClassifier(cfg.labels, prob_by_path)
    ft = FineTuner(cfg, fake)

    result = ft.run_round()
    assert result is not None
    assert len(result["local_weights"]) == 20
    assert result["num_samples"] == 8
    # After enough epochs the head should classify these as paper
    assert result["local_accuracy"] == pytest.approx(1.0)
    # Calibration was installed on the classifier
    assert fake.calibration is not None


def test_run_round_skips_when_too_few_samples(cfg, monkeypatch):
    _seed(cfg, [("only-one", "paper")])
    monkeypatch.setattr("bin_mpu.finetuner._read_image", lambda path: str(path))
    ft = FineTuner(cfg, FakeClassifier(cfg.labels, {"only-one": [0.25, 0.25, 0.25, 0.25]}))
    assert ft.run_round() is None


def test_apply_global_weights_roundtrip(cfg):
    ft = FineTuner(cfg, FakeClassifier(cfg.labels, {}))
    weights = [float(i) for i in range(20)]
    ft.apply_global_weights(weights)
    assert ft._flatten() == weights


def test_apply_global_weights_rejects_wrong_length(cfg):
    fake = FakeClassifier(cfg.labels, {})
    ft = FineTuner(cfg, fake)
    ft.apply_global_weights([1.0, 2.0, 3.0])  # wrong length
    assert fake.calibration is None  # nothing installed


def test_apply_global_weights_ignores_all_zeros(cfg):
    # The coordinator's untouched global model is all-zeros — applying it would
    # make softmax uniform and destroy the classifier. It must be ignored.
    fake = FakeClassifier(cfg.labels, {})
    ft = FineTuner(cfg, fake)
    ft.apply_global_weights([0.0] * 20)
    assert fake.calibration is None  # local identity head kept
