"""
End-to-end pipeline timing (no real hardware) — measures the path:
  PIR trigger  →  capture_burst  →  inference  →  lid open

Camera + MCU are mocked; everything else is the real pipeline.
This is the closest you can get to measuring the "user drops trash → lid opens"
latency without a physical bin.

Usage:
  python -m benchmarks.bench_e2e --iterations 30
"""
from __future__ import annotations

import argparse
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

from bin_mpu.classifier import Classifier
from bin_mpu.config import Config
from bin_mpu.pipeline import BinState, Pipeline

from ._common import banner, stats_of, write_report


def _make_pipeline(cfg: Config) -> Pipeline:
    p = object.__new__(Pipeline)
    p._cfg = cfg
    p._state = BinState.IDLE
    p._state_lock = threading.Lock()
    p._camera = MagicMock()
    p._classifier = Classifier(cfg.model_path, cfg.labels)
    p._store = MagicMock()
    p._mcu = MagicMock()
    p._telemetry = None
    p._pending_item = None
    p._label_timer = None
    p._finetune_hook = None
    return p


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--model", type=Path, default=Path("models/trash_classifier.tflite"))
    parser.add_argument("--bin-class", default="paper")
    parser.add_argument("--workdir", type=Path, default=Path("benchmarks/_workdir"))
    parser.add_argument("--report", default="benchmarks/results/e2e.json")
    args = parser.parse_args()

    cfg = Config(
        bin_class=args.bin_class,
        model_path=args.model,
        db_path=args.workdir / "samples.db",
        image_dir=args.workdir / "images",
        mqtt_enabled=False,
    )
    pipeline = _make_pipeline(cfg)

    rng = np.random.default_rng(0)
    frames = [rng.integers(0, 256, (720, 1280, 3), dtype=np.uint8)
              for _ in range(cfg.burst_frames)]
    pipeline._camera.capture_burst.return_value = frames

    lid_event = threading.Event()
    # Hook lid_open: signal so we can stop the clock there
    original_lid_open = pipeline._mcu.lid_open
    def lid_open_signal():
        lid_event.set()
        return original_lid_open()
    pipeline._mcu.lid_open = lid_open_signal

    banner(f"End-to-end PIR→inference→lid latency  iter={args.iterations} bin={args.bin_class}")
    samples: list[float] = []
    outcomes = {"high_conf_correct": 0, "high_conf_wrong": 0, "low_conf": 0, "timeout": 0}
    for _ in range(args.iterations):
        pipeline._state = BinState.IDLE
        lid_event.clear()
        t0 = time.perf_counter()
        pipeline._handle_mcu_event("PIR_TRIG")
        # Poll: break as soon as state leaves CAPTURING (any decision path)
        deadline = t0 + 5.0
        while time.perf_counter() < deadline:
            if pipeline._state != BinState.CAPTURING:
                break
            time.sleep(0.005)
        elapsed = (time.perf_counter() - t0) * 1000
        if pipeline._state == BinState.CAPTURING:
            outcomes["timeout"] += 1
        elif lid_event.is_set():
            outcomes["high_conf_correct"] += 1
        elif pipeline._state == BinState.WAITING_LABEL:
            outcomes["low_conf"] += 1
        else:
            outcomes["high_conf_wrong"] += 1
        samples.append(elapsed)
        pipeline._pending_item = None

    s = stats_of("PIR→capture→inference→decision", samples)
    banner("Results")
    print(s.pretty())
    print("\nDecision-path outcomes:")
    for k, v in outcomes.items():
        print(f"  {k:20s} {v:4d}")
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    write_report(args.report, [s], meta={
        "bin_class": args.bin_class, "model": str(args.model), "outcomes": outcomes,
    })
    print(f"\n→ Saved report: {args.report}")


if __name__ == "__main__":
    main()
