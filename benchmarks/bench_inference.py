"""
Inference benchmarks — TFLite single-frame + 5-frame burst latency.

Usage:
  python -m benchmarks.bench_inference --iterations 100
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from bin_mpu.classifier import Classifier
from bin_mpu.config import Config

from ._common import TimingStats, banner, stats_of, time_block, write_report


def make_synthetic_frame(h: int = 720, w: int = 1280) -> np.ndarray:
    rng = np.random.default_rng(0)
    return rng.integers(0, 256, (h, w, 3), dtype=np.uint8)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--model", type=Path, default=Path("models/trash_classifier.tflite"))
    parser.add_argument("--burst", type=int, default=5)
    parser.add_argument("--report", default="benchmarks/results/inference.json")
    args = parser.parse_args()

    if not args.model.exists():
        raise SystemExit(f"Model not found: {args.model}")

    cfg = Config(model_path=args.model)
    clf = Classifier(cfg.model_path, cfg.labels)

    banner(f"Inference benchmark — model={args.model} burst={args.burst}")
    frame = make_synthetic_frame()
    frames = [frame.copy() for _ in range(args.burst)]

    results: list[TimingStats] = []

    # Per-frame inference
    results.append(time_block(
        lambda: clf.predict_frame(frame),
        iterations=args.iterations, warmup=args.warmup,
        name="predict_frame (single)",
    ))

    # Burst (majority-vote ensemble over N frames)
    results.append(time_block(
        lambda: clf.predict_burst(frames),
        iterations=max(20, args.iterations // 5), warmup=args.warmup,
        name=f"predict_burst ({args.burst} frames)",
    ))

    # End-to-end "capture-cycle" estimate: burst_interval_s gaps + inference
    cycle_total = []
    burst_interval_ms = cfg.burst_interval_s * 1000
    for r in results:
        if r.name.startswith("predict_burst"):
            cycle_total.append(r.mean_ms + (args.burst - 1) * burst_interval_ms)
    if cycle_total:
        # Synthetic stat capturing the dominant component
        results.append(stats_of(
            f"capture-cycle est. (with {burst_interval_ms:.0f}ms gaps)",
            [cycle_total[0]] * 10,
        ))

    for r in results:
        print(r.pretty())

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    write_report(args.report, results, meta={"model": str(args.model), "burst": args.burst})
    print(f"\n→ Saved report: {args.report}")


if __name__ == "__main__":
    main()
