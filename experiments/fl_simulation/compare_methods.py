#!/usr/bin/env python3
"""
Compare stochastic rounding quantization vs Top-k sparsification vs baseline
for communication-efficient FL. Reuses dataset/training from run_part_b.py.
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
import time
from pathlib import Path

import numpy as np

# Import existing helpers from the Part B runner
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_part_b import (
    CLASSES,
    FEATURE_DIM,
    DatasetBundle,
    compute_loss_and_accuracy,
    generate_synthetic_dataset,
    local_train,
    params_to_vector,
    partition_dirichlet,
    quantize_stochastic,
    dequantize,
    stratified_split,
    standardize,
    vector_to_params,
    weighted_average,
)


# ── Top-k Sparsification ──────────────────────────────────────────────────────


def topk_sparsify(weights: np.ndarray, keep_ratio: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Keep top `keep_ratio` fraction of elements by magnitude; zero the rest.
    Returns (sparse_weights, indices_of_kept, values_of_kept)."""
    flat = weights.reshape(-1)
    n_keep = max(1, int(round(len(flat) * keep_ratio)))
    magnitudes = np.abs(flat)
    threshold = -np.partition(-magnitudes, n_keep - 1)[n_keep - 1]
    mask = magnitudes >= threshold
    # ensure at least n_keep elements (handle ties)
    if mask.sum() < n_keep:
        # find the top n_keep by argsort
        idx = np.argpartition(magnitudes, -n_keep)[-n_keep:]
        mask = np.zeros_like(magnitudes, dtype=bool)
        mask[idx] = True
    sparse = flat.copy()
    sparse[~mask] = 0.0
    return sparse.reshape(weights.shape), np.where(mask)[0].astype(np.int32), flat[mask].copy()


def topk_compress(weights: np.ndarray, keep_ratio: float) -> tuple[np.ndarray, float, float]:
    """Compress via Top-k: return (indices_and_values_packed, metadata)."""
    sparse, indices, values = topk_sparsify(weights, keep_ratio)
    # We send: float32 values + int32 indices for the kept elements
    # Plus 2 floats for min/max (or metadata)
    # For communication accounting: compressed size = indices.nbytes + values.nbytes + 8
    return sparse, float(keep_ratio), float(len(indices))


def topk_decompress(sparse: np.ndarray, _ratio: float, _n_kept: float) -> np.ndarray:
    """In the simulation, the sparse array is already in the right shape
    (zeroed-out elements). The server just uses it directly."""
    return sparse


# ── Method runners ────────────────────────────────────────────────────────────


def run_baseline(
    model_vector: np.ndarray,
    X_train_part: np.ndarray,
    y_train_part: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    local_epochs: int,
    batch_size: int,
    learning_rate: float,
    seed: int,
    num_classes: int,
) -> tuple[np.ndarray, float, float, int]:
    """Standard FedAvg with float32. Returns (global_model, acc, loss, total_bytes)."""
    local_model, _, _ = local_train(
        model_vector, X_train_part, y_train_part,
        local_epochs, batch_size, learning_rate, seed, num_classes,
    )
    total_bytes = int(model_vector.nbytes)  # sent + received
    return local_model, 0.0, 0.0, total_bytes


def run_quantized(
    model_vector: np.ndarray,
    X_train_part: np.ndarray,
    y_train_part: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    local_epochs: int,
    batch_size: int,
    learning_rate: float,
    seed: int,
    num_classes: int,
    bits: int,
) -> tuple[np.ndarray, float, float, int]:
    local_model, local_loss, local_acc = local_train(
        model_vector, X_train_part, y_train_part,
        local_epochs, batch_size, learning_rate, seed, num_classes,
    )
    q_weights, q_min, q_scale = quantize_stochastic(local_model, bits)
    q_bytes = int(q_weights.nbytes) + 8
    received = dequantize(q_weights, q_min, q_scale, bits)
    return received, local_loss, local_acc, q_bytes


def run_topk(
    model_vector: np.ndarray,
    X_train_part: np.ndarray,
    y_train_part: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    local_epochs: int,
    batch_size: int,
    learning_rate: float,
    seed: int,
    num_classes: int,
    keep_ratio: float,
) -> tuple[np.ndarray, float, float, int]:
    local_model, local_loss, local_acc = local_train(
        model_vector, X_train_part, y_train_part,
        local_epochs, batch_size, learning_rate, seed, num_classes,
    )
    sparse, ratio, n_kept = topk_compress(local_model, keep_ratio)
    # Communication: indices (int32) + values (float32)
    n = int(n_kept)
    compressed_bytes = n * 4 + n * 4 + 8  # indices + values + metadata
    received = topk_decompress(sparse, ratio, n_kept)
    return received, local_loss, local_acc, compressed_bytes


# ── Main comparison ───────────────────────────────────────────────────────────


def run_comparison(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    num_classes = len(CLASSES)

    # Generate synthetic dataset
    print("Generating synthetic dataset...")
    X, y, counts = generate_synthetic_dataset(args.synthetic_samples_per_class, args.synthetic_seed)
    X_train, y_train, X_test, y_test = stratified_split(X, y, test_fraction=0.2, seed=args.synthetic_seed)
    X_train, X_test = standardize(X_train, X_test)
    print(f"  Train: {len(X_train)}, Test: {len(X_test)}")

    # Methods to compare
    methods = [
        ("float32", lambda mv, Xp, yp, s: run_baseline(mv, Xp, yp, X_test, y_test, args.local_epochs, args.batch_size, args.learning_rate, s, num_classes), 1.0),
        ("SR-8bit",  lambda mv, Xp, yp, s: run_quantized(mv, Xp, yp, X_test, y_test, args.local_epochs, args.batch_size, args.learning_rate, s, num_classes, 8), 4.0),
        ("SR-6bit",  lambda mv, Xp, yp, s: run_quantized(mv, Xp, yp, X_test, y_test, args.local_epochs, args.batch_size, args.learning_rate, s, num_classes, 6), 5.33),
        ("SR-4bit",  lambda mv, Xp, yp, s: run_quantized(mv, Xp, yp, X_test, y_test, args.local_epochs, args.batch_size, args.learning_rate, s, num_classes, 4), 8.0),
        ("Top-50%",  lambda mv, Xp, yp, s: run_topk(mv, Xp, yp, X_test, y_test, args.local_epochs, args.batch_size, args.learning_rate, s, num_classes, 0.50), 2.0),
        ("Top-10%",  lambda mv, Xp, yp, s: run_topk(mv, Xp, yp, X_test, y_test, args.local_epochs, args.batch_size, args.learning_rate, s, num_classes, 0.10), 10.0),
        ("Top-1%",   lambda mv, Xp, yp, s: run_topk(mv, Xp, yp, X_test, y_test, args.local_epochs, args.batch_size, args.learning_rate, s, num_classes, 0.01), 100.0),
    ]

    results = []

    for method_name, runner, reported_ratio in methods:
        print(f"\n=== {method_name} (theoretical ratio: {reported_ratio}x) ===")
        method_accs = []
        method_losses = []
        method_comms = []
        method_best = []

        for seed in args.seeds:
            rng = np.random.default_rng(seed)
            partitions = partition_dirichlet(y_train, args.clients, args.alpha, seed)
            model_vector = np.zeros(FEATURE_DIM * num_classes + num_classes, dtype=np.float32)
            model_bytes = int(model_vector.nbytes)

            round_accs = []
            round_losses = []
            total_bytes_round = 0
            total_comm = 0

            for round_idx in range(1, args.rounds + 1):
                local_models = []
                sample_counts = []
                round_comm = 0

                for client_id, sample_idx in enumerate(partitions):
                    if len(sample_idx) == 0:
                        continue
                    local_seed = seed * 1000 + round_idx * 100 + client_id
                    local_model, local_loss, local_acc, comm_bytes = runner(
                        model_vector, X_train[sample_idx], y_train[sample_idx], local_seed
                    )
                    if not np.all(np.isfinite(local_model)):
                        continue
                    # Server receives this model (comm counted in runner)
                    round_comm += comm_bytes
                    # Server also sends the global model
                    round_comm += model_bytes
                    local_models.append(local_model)
                    sample_counts.append(int(len(sample_idx)))

                if not local_models:
                    continue

                model_vector = weighted_average(local_models, sample_counts)
                global_w, global_b = vector_to_params(model_vector, FEATURE_DIM, num_classes)
                g_loss, g_acc = compute_loss_and_accuracy(global_w, global_b, X_test, y_test)
                round_accs.append(g_acc)
                round_losses.append(g_loss)
                total_comm += round_comm

            if round_accs:
                avg_acc = sum(round_accs) / len(round_accs)
                final_acc = round_accs[-1]
                best_acc = max(round_accs)
                method_accs.append(final_acc)
                method_losses.append(round_losses[-1])
                method_comms.append(total_comm)
                method_best.append(best_acc)
                print(f"  seed={seed}: final_acc={final_acc*100:.2f}%, best={best_acc*100:.2f}%, comm={total_comm/(1024*1024):.3f}MB")

        if method_accs:
            mean_acc = sum(method_accs) / len(method_accs) * 100
            mean_best = sum(method_best) / len(method_best) * 100
            mean_comm_mb = sum(method_comms) / len(method_comms) / (1024 * 1024)
            std_acc = (max(method_accs) - min(method_accs)) / 2 * 100 if len(method_accs) > 1 else 0
            results.append({
                "method": method_name,
                "acc": mean_acc,
                "acc_std": std_acc,
                "best": mean_best,
                "comm_mb": mean_comm_mb,
                "ratio": reported_ratio,
            })
            print(f"  => {method_name}: {mean_acc:.2f}% ± {std_acc:.2f}, best={mean_best:.2f}%, comm={mean_comm_mb:.3f}MB")

    # ── Output comparison table ─────────────────────────────────────────────
    print("\n\n" + "=" * 120)
    print("COMPARISON: Communication-Efficient FL Methods (20 clients, 25 rounds)")
    print("=" * 120)
    print(f"{'Method':<12} {'Acc(%)':<10} {'Best(%)':<10} {'Comm(MB)':<12} {'Ratio':<12} {'Savings vs float32':<20} {'Acc drop vs float32':<20}")
    print("-" * 120)

    float32_acc = next(r["acc"] for r in results if r["method"] == "float32")
    float32_comm = next(r["comm_mb"] for r in results if r["method"] == "float32")

    for r in results:
        savings = (1 - r["comm_mb"] / float32_comm) * 100
        drop = float32_acc - r["acc"]
        print(f"{r['method']:<12} {r['acc']:<10.2f} {r['best']:<10.2f} {r['comm_mb']:<12.3f} {r['ratio']:<12} {savings:<20.1f}% {drop:<20.2f}p.p.")

    # Save CSV
    csv_path = output_dir / "comparison_results.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["method", "acc", "acc_std", "best", "comm_mb", "ratio"])
        w.writeheader()
        w.writerows(results)
    print(f"\nResults saved to {csv_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Compare FL compression methods")
    p.add_argument("--clients", type=int, default=20)
    p.add_argument("--seeds", nargs="+", type=int, default=[11, 29, 47])
    p.add_argument("--rounds", type=int, default=25)
    p.add_argument("--local-epochs", type=int, default=2)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--learning-rate", type=float, default=0.18)
    p.add_argument("--alpha", type=float, default=0.3)
    p.add_argument("--synthetic-samples-per-class", type=int, default=220)
    p.add_argument("--synthetic-seed", type=int, default=20260517)
    p.add_argument("--output-dir", default="/tmp/trashuq_comparison")
    run_comparison(p.parse_args())
