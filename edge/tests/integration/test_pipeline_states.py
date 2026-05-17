"""Test pipeline state machine — no hardware, no model."""
import threading
import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from bin_mpu.config import Config
from bin_mpu.pipeline import BinState, Pipeline


@pytest.fixture()
def cfg(tmp_path):
    return Config(
        model_path=tmp_path / "fake.tflite",
        db_path=tmp_path / "samples.db",
        image_dir=tmp_path / "images",
        bin_class="paper",
    )


def _make_pipeline(cfg: Config) -> Pipeline:
    p = object.__new__(Pipeline)
    p._cfg = cfg
    p._state = BinState.IDLE
    p._state_lock = threading.Lock()
    p._camera = MagicMock()
    p._classifier = MagicMock()
    p._store = MagicMock()
    p._mcu = MagicMock()
    p._telemetry = None
    p._pending_item = None
    p._label_timer = None
    p._finetune_hook = None
    return p


def test_pir_trigger_moves_to_capturing(cfg: Config) -> None:
    p = _make_pipeline(cfg)

    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    p._camera.capture_burst.return_value = [frame] * 5
    p._classifier.predict_frame.return_value = ("paper", 0.95)

    from bin_mpu.classifier import Prediction
    p._classifier.predict_burst.return_value = Prediction(
        label="paper", confidence=0.95, votes={"paper": 5}
    )

    p._handle_mcu_event("PIR_TRIG")
    # Give the capture thread time to complete
    time.sleep(0.3)

    p._mcu.led_on.assert_called_once()
    p._store.save.assert_called_once()
    # Correct bin classification → lid must be opened
    p._mcu.lid_open.assert_called()


def test_wrong_bin_does_not_open_lid(cfg: Config) -> None:
    p = _make_pipeline(cfg)

    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    p._camera.capture_burst.return_value = [frame] * 5
    p._classifier.predict_frame.return_value = ("paper", 0.95)

    from bin_mpu.classifier import Prediction
    # High-confidence "glass" in a paper bin → wrong bin, no lid open
    p._classifier.predict_burst.return_value = Prediction(
        label="glass", confidence=0.95, votes={"glass": 5}
    )

    p._handle_mcu_event("PIR_TRIG")
    time.sleep(0.3)

    p._mcu.lid_open.assert_not_called()


def test_low_confidence_waits_for_label(cfg: Config) -> None:
    p = _make_pipeline(cfg)

    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    p._camera.capture_burst.return_value = [frame] * 5
    p._classifier.predict_frame.return_value = ("paper", 0.95)

    from bin_mpu.classifier import Prediction
    p._classifier.predict_burst.return_value = Prediction(
        label="paper", confidence=0.4, votes={"paper": 3, "glass": 2}
    )
    p._store.save.return_value = "abc-id"

    p._handle_mcu_event("PIR_TRIG")
    time.sleep(0.3)

    assert p._state == BinState.WAITING_LABEL
    assert p._pending_item is not None
    p._mcu.lid_open.assert_not_called()


def test_second_pir_ignored_during_capture(cfg: Config) -> None:
    p = _make_pipeline(cfg)
    p._state = BinState.CAPTURING  # already in progress

    p._handle_mcu_event("PIR_TRIG")
    p._mcu.led_on.assert_not_called()
