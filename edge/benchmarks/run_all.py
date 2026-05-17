"""
Run every benchmark in sequence and write a consolidated report.

Usage:
  python -m benchmarks.run_all --grpc-host localhost --mqtt-host localhost \\
                                --skip grpc            # skip subset if servers are down
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


BENCHES = {
    "inference": ["benchmarks.bench_inference"],
    "finetune":  ["benchmarks.bench_finetune"],
    "grpc":      ["benchmarks.bench_grpc"],
    "mqtt":      ["benchmarks.bench_mqtt"],
    "e2e":       ["benchmarks.bench_e2e"],
}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--grpc-host", default="localhost")
    p.add_argument("--grpc-port", type=int, default=50051)
    p.add_argument("--mqtt-host", default="localhost")
    p.add_argument("--mqtt-port", type=int, default=1883)
    p.add_argument("--skip", nargs="*", default=[], choices=list(BENCHES))
    p.add_argument("--only", nargs="*", default=None, choices=list(BENCHES))
    args = p.parse_args()

    selected = list(BENCHES) if args.only is None else args.only
    selected = [b for b in selected if b not in args.skip]

    print(f"Running benchmarks: {selected}")
    Path("benchmarks/results").mkdir(parents=True, exist_ok=True)
    summary = []

    for name in selected:
        cmd = [sys.executable, "-m", *BENCHES[name]]
        if name == "grpc":
            cmd += ["--host", args.grpc_host, "--port", str(args.grpc_port)]
        if name == "mqtt":
            cmd += ["--host", args.mqtt_host, "--port", str(args.mqtt_port)]
        print(f"\n>>> {name}")
        t0 = time.perf_counter()
        rc = subprocess.call(cmd)
        dt = time.perf_counter() - t0
        summary.append((name, rc, dt))

    print("\n" + "=" * 60)
    print(f"{'Benchmark':12s}  {'Status':10s}  {'Elapsed':>10s}")
    print("=" * 60)
    for name, rc, dt in summary:
        status = "OK" if rc == 0 else f"FAIL ({rc})"
        print(f"{name:12s}  {status:10s}  {dt:>8.1f} s")


if __name__ == "__main__":
    main()
