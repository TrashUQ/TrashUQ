#!/usr/bin/env python3
import argparse
import random
import time

import grpc

from app import fl_pb2, fl_pb2_grpc


def random_local_weights(global_weights: list[float], noise: float = 0.05) -> list[float]:
    return [w + random.uniform(-noise, noise) for w in global_weights]


def main() -> None:
    parser = argparse.ArgumentParser(description="gRPC FL mock clients for TrashUQ")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=50051)
    parser.add_argument("--clients", type=int, default=3)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--sleep", type=float, default=0.5)
    args = parser.parse_args()

    channel = grpc.insecure_channel(f"{args.host}:{args.port}")
    stub = fl_pb2_grpc.FederatedLearningServiceStub(channel)

    client_ids = [f"uno-{i}" for i in range(1, args.clients + 1)]

    for client_id in client_ids:
        resp = stub.Join(fl_pb2.JoinRequest(client_id=client_id))
        print(f"join {client_id}: ok={resp.ok} round={resp.round} model_version={resp.model_version}")

    for r in range(1, args.rounds + 1):
        print(f"\n=== round {r} ===")
        for client_id in client_ids:
            global_resp = stub.GetGlobalModel(fl_pb2.GetGlobalModelRequest(client_id=client_id))
            if not global_resp.ok:
                print(f"get_model {client_id}: {global_resp.message}")
                continue

            local = random_local_weights(list(global_resp.global_weights))
            submit = stub.SubmitUpdate(
                fl_pb2.SubmitUpdateRequest(
                    client_id=client_id,
                    round=global_resp.round,
                    num_samples=random.randint(40, 120),
                    local_weights=local,
                    local_loss=random.uniform(0.1, 1.0),
                    local_accuracy=random.uniform(0.6, 0.99),
                )
            )
            print(
                f"submit {client_id}: ok={submit.ok} aggregated={submit.round_aggregated} "
                f"current_round={submit.current_round} model_version={submit.model_version}"
            )
            time.sleep(args.sleep)


if __name__ == "__main__":
    main()
