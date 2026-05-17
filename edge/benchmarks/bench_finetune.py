"""
Edge fine-tuning benchmark (NumPy calibration head — no TensorFlow).

Measures, on the current host:
  1. Feature pass: time to run the frozen TFLite model over the labeled set
  2. Head training time (SGD over the n×n calibration head)
  3. Total FL-round wall time as a function of sample count

Runs with synthetic samples (no labelled data required):
  python -m benchmarks.bench_finetune --samples 8 16 32 64 --epochs 3
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from bin_mpu.classifier import Classifier
from bin_mpu.config import Config
from bin_mpu.finetuner import FineTuner
from bin_mpu.sample_store import CREATE_TABLE

from ._common import banner, stats_of, write_report


def seed_synthetic_samples(cfg: Config, count: int) -> None:
    """Drop & re-create the SQLite store, then insert `count` synthetic
    user-labeled samples spread evenly across cfg.labels."""
    if cfg.db_path.exists():
        cfg.db_path.unlink()
    cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
    if cfg.image_dir.exists():
        shutil.rmtree(cfg.image_dir)
    cfg.image_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(cfg.db_path))
    conn.execute(CREATE_TABLE)
    rng = np.random.default_rng(0)
    for i in range(count):
        sid = str(uuid.uuid4())
        img = rng.integers(0, 256, (224, 224, 3), dtype=np.uint8)
        path = cfg.image_dir / f"{sid}.jpg"
        cv2.imwrite(str(path), img)
        label = cfg.labels[i % len(cfg.labels)]
        conn.execute(
            "INSERT INTO samples (id, captured_at, image_path, label, label_src, confidence) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (sid, datetime.now(timezone.utc).isoformat(), str(path), label, "user", 0.5),
        )
    conn.commit()
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, nargs="+", default=[8, 16, 32])
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--model", type=Path, default=Path("models/trash_classifier.tflite"))
    parser.add_argument("--workdir", type=Path, default=Path("benchmarks/_workdir"))
    parser.add_argument("--report", default="benchmarks/results/finetune.json")
    args = parser.parse_args()

    cfg = Config(
        model_path=args.model,
        db_path=args.workdir / "samples.db",
        image_dir=args.workdir / "images",
        fl_epochs=args.epochs,
        fl_batch_size=args.batch_size,
    )

    banner(f"Fine-tuning benchmark (NumPy head) — epochs={args.epochs} batch={args.batch_size}")

    clf = Classifier(cfg.model_path, cfg.labels)
    ft = FineTuner(cfg, clf)
    print(f"  calibration head size: {ft.head_weight_length()} floats")
    print(f"  → set FL_MODEL_SIZE={ft.head_weight_length()} on the backend")

    results = []

    # Feature pass: run TFLite over N images
    seed_synthetic_samples(cfg, 16)
    results.append(_time(
        lambda: ft._load_features(),
        iterations=5,
        name="feature pass (16 imgs through TFLite)",
    ))

    # Full round vs sample count
    per_sample_round_ms = []
    for n in args.samples:
        seed_synthetic_samples(cfg, n)
        timings: list[float] = []
        for _ in range(3):
            t0 = time.perf_counter()
            r = ft.run_round()
            timings.append((time.perf_counter() - t0) * 1000)
            if r is None:
                print(f"  WARN: run_round returned None for n={n}")
        s = stats_of(f"fl_round n={n} epochs={args.epochs}", timings)
        results.append(s)
        per_sample_round_ms.append((n, s.mean_ms))

    banner("Results")
    print(f"head_weight_length = {ft.head_weight_length()}")
    for r in results:
        print(r.pretty())

    print("\nPer-sample fine-tune cost:")
    for n, ms in per_sample_round_ms:
        print(f"  {n:4d} samples → {ms:7.1f} ms  ({ms / n:5.2f} ms/sample)")

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    write_report(args.report, results, meta={
        "head_weight_length": ft.head_weight_length(),
        "per_sample_round_ms": per_sample_round_ms,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
    })
    print(f"\n→ Saved report: {args.report}")


def _time(fn, iterations: int, name: str):
    samples = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000)
    return stats_of(name, samples)


if __name__ == "__main__":
    main()
