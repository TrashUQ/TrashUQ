"""Shared helpers for benchmark scripts."""
from __future__ import annotations

import json
import statistics
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass


@dataclass
class TimingStats:
    name: str
    n: int
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    stdev_ms: float

    def pretty(self) -> str:
        return (
            f"{self.name:38s}  n={self.n:4d}  "
            f"mean={self.mean_ms:7.2f}ms  "
            f"p50={self.p50_ms:7.2f}  "
            f"p95={self.p95_ms:7.2f}  "
            f"p99={self.p99_ms:7.2f}  "
            f"min={self.min_ms:7.2f}  max={self.max_ms:7.2f}"
        )


def time_block(fn: Callable[[], None], iterations: int, warmup: int = 0, name: str = "") -> TimingStats:
    for _ in range(warmup):
        fn()
    samples: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return stats_of(name or fn.__name__, samples)


def stats_of(name: str, samples_ms: list[float]) -> TimingStats:
    s = sorted(samples_ms)
    n = len(s)
    if n == 0:
        return TimingStats(name, 0, 0, 0, 0, 0, 0, 0, 0)
    return TimingStats(
        name=name,
        n=n,
        mean_ms=statistics.fmean(s),
        p50_ms=s[n // 2],
        p95_ms=s[min(n - 1, int(n * 0.95))],
        p99_ms=s[min(n - 1, int(n * 0.99))],
        min_ms=s[0],
        max_ms=s[-1],
        stdev_ms=statistics.pstdev(s) if n > 1 else 0.0,
    )


def write_report(path: str, results: list[TimingStats], meta: dict | None = None) -> None:
    obj = {
        "meta": meta or {},
        "results": [asdict(r) for r in results],
        "timestamp": time.time(),
    }
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)


def banner(s: str) -> None:
    print()
    print("─" * 88)
    print(f"  {s}")
    print("─" * 88)
