"""
gRPC FL-client benchmark — measures roundtrip latency for Join,
GetGlobalModel, and SubmitUpdate against a running TrashUQ backend.

The backend default `FL_MODEL_SIZE=16` and `FL_MIN_CLIENTS_PER_ROUND=2`.
For single-client benchmarking, start the backend with FL_MIN_CLIENTS_PER_ROUND=1
and FL_MODEL_SIZE matching the value you pass via --weights-size.

Usage:
  python -m benchmarks.bench_grpc --host bepes-server --port 50051 \\
                                  --iterations 50 --weights-size 16
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import grpc

from bin_mpu import fl_pb2, fl_pb2_grpc

from ._common import banner, stats_of, write_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=50051)
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--weights-size", type=int, default=20,
                        help="Must match FL_MODEL_SIZE on backend (20 = 4-class calibration head)")
    parser.add_argument("--client-id", default="bench-client-01")
    parser.add_argument("--report", default="benchmarks/results/grpc.json")
    args = parser.parse_args()

    banner(f"gRPC FL benchmark → {args.host}:{args.port}")
    channel = grpc.insecure_channel(f"{args.host}:{args.port}")
    stub = fl_pb2_grpc.FederatedLearningServiceStub(channel)

    # Test the channel is alive with a single Join
    print("Probing channel…")
    try:
        resp = stub.Join(fl_pb2.JoinRequest(client_id=args.client_id), timeout=5.0)
        print(f"  Join → ok={resp.ok} round={resp.round} weights_len={len(resp.global_weights)}")
    except grpc.RpcError as exc:
        raise SystemExit(f"FATAL: cannot reach gRPC server: {exc}")

    weights = [0.01 * i for i in range(args.weights_size)]
    results = []

    # Join latency
    join_ms: list[float] = []
    for i in range(args.iterations):
        t0 = time.perf_counter()
        stub.Join(fl_pb2.JoinRequest(client_id=f"{args.client_id}-{i}"), timeout=10.0)
        join_ms.append((time.perf_counter() - t0) * 1000)
    results.append(stats_of("Join", join_ms))

    # GetGlobalModel latency
    get_ms: list[float] = []
    for _ in range(args.iterations):
        t0 = time.perf_counter()
        stub.GetGlobalModel(
            fl_pb2.GetGlobalModelRequest(client_id=args.client_id), timeout=10.0
        )
        get_ms.append((time.perf_counter() - t0) * 1000)
    results.append(stats_of("GetGlobalModel", get_ms))

    # SubmitUpdate latency (note: backend may return "stale round" once aggregated)
    sub_ms: list[float] = []
    submit_outcomes: dict[str, int] = {}
    for i in range(args.iterations):
        # Fetch latest round so we don't always submit a stale one
        cur = stub.GetGlobalModel(
            fl_pb2.GetGlobalModelRequest(client_id=args.client_id), timeout=5.0
        )
        t0 = time.perf_counter()
        resp = stub.SubmitUpdate(
            fl_pb2.SubmitUpdateRequest(
                client_id=f"{args.client_id}-{i % 4}",  # rotate so >=2-client coordinators see >1 id
                round=cur.round,
                num_samples=32,
                local_weights=weights,
                local_loss=0.5,
                local_accuracy=0.7,
            ),
            timeout=15.0,
        )
        sub_ms.append((time.perf_counter() - t0) * 1000)
        submit_outcomes[resp.message] = submit_outcomes.get(resp.message, 0) + 1
    results.append(stats_of("SubmitUpdate", sub_ms))

    banner("Results")
    for r in results:
        print(r.pretty())

    print("\nSubmitUpdate response breakdown:")
    for msg, count in submit_outcomes.items():
        print(f"  {count:4d}  {msg}")

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    write_report(args.report, results, meta={
        "host": args.host, "port": args.port,
        "weights_size": args.weights_size,
        "submit_outcomes": submit_outcomes,
    })
    print(f"\n→ Saved report: {args.report}")
    channel.close()


if __name__ == "__main__":
    main()
