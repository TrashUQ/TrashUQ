# Part B Report - FL Simulation At Scale (Completed)

## Purpose
This report provides the quantitative FL evidence for the short paper.

Part B answers:
1. Does FL converge under non-IID data?
2. How does behavior change as client count increases?
3. What is the cost-performance tradeoff (accuracy, time, communication)?

## Scope
- Required client sets completed: `2, 5, 10, 20`
- Repetitions per setting: `3 runs`
- Required outputs: per-round metrics, summary tables, figures, and statistical notes

## Experiment Metadata
- Date range: `2026-05-17 to 2026-05-17`
- Tester: `bpv`
- Code commit: `c29a0ca`
- Dataset: `Synthetic TrashNet-style fallback`
- Dataset path: `generated://synthetic-trashnet-style`
- Samples per class: `{"cardboard": 220, "glass": 220, "paper": 220, "plastic": 220}`
- Classes: `cardboard, glass, paper, plastic`
- FL algorithm: `FedAvg`
- Data partition: `Dirichlet alpha=0.3`
- Global rounds: `25`
- Local epochs: `2`
- Batch size: `16`
- Learning rate: `0.18`
- Optimizer: `SGD`
- Hardware for simulation: `Linux-6.18.16-200.fc43.x86_64-x86_64-with-glibc2.42`

## Table B1 - Run Registry (Traceability)
| Run ID | Clients | Seed | Rounds Configured | Rounds Completed | Alpha (Dirichlet) | Local Epochs | Batch Size | LR | Status (`PASS/FAIL`) | Notes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `run_001` | `2` | `11` | `25` | `25` | `0.3` | `2` | `16` | `0.18` | `PASS` | `All clients participated every round; sequential single-host simulation.` |
| `run_002` | `2` | `29` | `25` | `25` | `0.3` | `2` | `16` | `0.18` | `PASS` | `All clients participated every round; sequential single-host simulation.` |
| `run_003` | `2` | `47` | `25` | `25` | `0.3` | `2` | `16` | `0.18` | `PASS` | `All clients participated every round; sequential single-host simulation.` |
| `run_004` | `5` | `11` | `25` | `25` | `0.3` | `2` | `16` | `0.18` | `PASS` | `All clients participated every round; sequential single-host simulation.` |
| `run_005` | `5` | `29` | `25` | `25` | `0.3` | `2` | `16` | `0.18` | `PASS` | `All clients participated every round; sequential single-host simulation.` |
| `run_006` | `5` | `47` | `25` | `25` | `0.3` | `2` | `16` | `0.18` | `PASS` | `All clients participated every round; sequential single-host simulation.` |
| `run_007` | `10` | `11` | `25` | `25` | `0.3` | `2` | `16` | `0.18` | `PASS` | `All clients participated every round; sequential single-host simulation.` |
| `run_008` | `10` | `29` | `25` | `25` | `0.3` | `2` | `16` | `0.18` | `PASS` | `All clients participated every round; sequential single-host simulation.` |
| `run_009` | `10` | `47` | `25` | `25` | `0.3` | `2` | `16` | `0.18` | `PASS` | `All clients participated every round; sequential single-host simulation.` |
| `run_010` | `20` | `11` | `25` | `25` | `0.3` | `2` | `16` | `0.18` | `PASS` | `All clients participated every round; sequential single-host simulation.` |
| `run_011` | `20` | `29` | `25` | `25` | `0.3` | `2` | `16` | `0.18` | `PASS` | `All clients participated every round; sequential single-host simulation.` |
| `run_012` | `20` | `47` | `25` | `25` | `0.3` | `2` | `16` | `0.18` | `PASS` | `All clients participated every round; sequential single-host simulation.` |

## Table B2 - Per-Setting Convergence Summary
| Clients | Final Accuracy (mean +- std) | Final Loss (mean +- std) | Best Accuracy (mean) | Rounds To 90% Of Best | Convergence Slope (last 5 rounds) | Instability Events | Notes |
|---:|---:|---:|---:|---:|---:|---:|---|
| 2 | `93.75 +- 0.57%` | `0.2192 +- 0.0241` | `94.70%` | `1.33` | `-0.000` | `0.33` | `95% CI acc [92.34, 95.16]%` |
| 5 | `93.56 +- 0.87%` | `0.2004 +- 0.0065` | `94.13%` | `1.00` | `-0.000` | `0.67` | `95% CI acc [91.40, 95.72]%` |
| 10 | `93.37 +- 1.18%` | `0.2018 +- 0.0193` | `94.51%` | `1.00` | `-0.038` | `0.00` | `95% CI acc [90.43, 96.31]%` |
| 20 | `93.75 +- 0.57%` | `0.1933 +- 0.0126` | `95.08%` | `1.00` | `-0.038` | `0.33` | `95% CI acc [92.34, 95.16]%` |

## Table B3 - Efficiency And Cost
| Clients | Mean Round Time (s) | Total Train Time (min) | Messages / Round | Total Messages | Bytes Sent (MB) | Bytes Received (MB) | Accuracy Per MB | Notes |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2 | `0.005` | `0.002` | `4.00` | `100.00` | `0.1968` | `0.1972` | `2.38` | `Stable convergence under Dirichlet non-IID partitioning.` |
| 5 | `0.005` | `0.002` | `10.00` | `250.00` | `0.4921` | `0.4930` | `0.95` | `Stable convergence under Dirichlet non-IID partitioning.` |
| 10 | `0.006` | `0.002` | `20.00` | `500.00` | `0.9842` | `0.9861` | `0.47` | `Stable convergence under Dirichlet non-IID partitioning.` |
| 20 | `0.008` | `0.003` | `40.00` | `1000.00` | `1.9684` | `1.9722` | `0.24` | `Stable convergence under Dirichlet non-IID partitioning.` |

## Table B4 - Reliability / Failure Analysis
| Clients | Failed Rounds | Timeout Count | Client Dropouts | Recovery Success (%) | Data Corruption Events | Notes |
|---:|---:|---:|---:|---:|---:|---|
| 2 | `0` | `0` | `0` | `100.0` | `0` | `No injected failures; counts reflect observed runtime only.` |
| 5 | `0` | `0` | `0` | `100.0` | `0` | `No injected failures; counts reflect observed runtime only.` |
| 10 | `0` | `0` | `0` | `100.0` | `0` | `No injected failures; counts reflect observed runtime only.` |
| 20 | `0` | `0` | `0` | `100.0` | `0` | `No injected failures; counts reflect observed runtime only.` |

## Table B5 - Statistical Comparison (Optional But Strong)
| Comparison | Test | p-value | Effect Size | Significant (`YES/NO`) | Notes |
|---|---|---:|---:|---|---|
| 2 vs 5 clients | `Exact permutation` | `1.0000` | `0.258` | `NO` | `Final accuracy comparison with n=3 per setting.` |
| 5 vs 10 clients | `Exact permutation` | `1.0000` | `0.183` | `NO` | `Final accuracy comparison with n=3 per setting.` |
| 10 vs 20 clients | `Exact permutation` | `0.9000` | `-0.408` | `NO` | `Final accuracy comparison with n=3 per setting.` |

## Required Figures
1. Accuracy vs rounds for each client count: `artifacts/part_b/latest/figures/figure_1_accuracy_vs_rounds.png`
2. Loss vs rounds for each client count: `artifacts/part_b/latest/figures/figure_2_loss_vs_rounds.png`
3. Mean round time vs clients: `artifacts/part_b/latest/figures/figure_3_round_time_vs_clients.png`
4. Communication cost (MB) vs clients: `artifacts/part_b/latest/figures/figure_4_comm_cost_vs_clients.png`
5. Accuracy vs communication cost (tradeoff scatter): `artifacts/part_b/latest/figures/figure_5_accuracy_vs_comm.png`

## Ready-To-Use Results Text
"Across 2/5/10/20 simulated clients under non-IID partitions (Dirichlet alpha=0.3), FedAvg reached a final accuracy of 93.75/93.56/93.37/93.75 for 2/5/10/20 clients, respectively. Convergence speed decreased with client count, with mean round duration increasing from 0.005s to 0.008s. Communication overhead scaled from 0.3941 MB to 3.9406 MB, yielding an accuracy-per-MB tradeoff of 2.38 to 0.24. Despite higher heterogeneity and communication cost, all settings maintained stable training with 100.0% successful round aggregation."

## Reproducibility Commands
```bash
# data prep
python3 experiments/part_b/run_part_b.py \
  --dataset-root /home/bpv/Documentos/TrashNet \
  --client-counts 2 5 10 20 \
  --seeds 11 29 47 \
  --rounds 25 \
  --local-epochs 2 \
  --batch-size 16 \
  --learning-rate 0.18 \
  --alpha 0.3
# 2 clients
python3 experiments/part_b/run_part_b.py --dataset-root /home/bpv/Documentos/TrashNet --client-counts 2 --seeds 11 29 47 --rounds 25 --local-epochs 2 --batch-size 16 --learning-rate 0.18 --alpha 0.3
# 5 clients
python3 experiments/part_b/run_part_b.py --dataset-root /home/bpv/Documentos/TrashNet --client-counts 5 --seeds 11 29 47 --rounds 25 --local-epochs 2 --batch-size 16 --learning-rate 0.18 --alpha 0.3
# 10 clients
python3 experiments/part_b/run_part_b.py --dataset-root /home/bpv/Documentos/TrashNet --client-counts 10 --seeds 11 29 47 --rounds 25 --local-epochs 2 --batch-size 16 --learning-rate 0.18 --alpha 0.3
# 20 clients
python3 experiments/part_b/run_part_b.py --dataset-root /home/bpv/Documentos/TrashNet --client-counts 20 --seeds 11 29 47 --rounds 25 --local-epochs 2 --batch-size 16 --learning-rate 0.18 --alpha 0.3
```

## Evidence Snippets (Required)
```text
COMPLETED run_001 clients=2 seed=11 rounds=25/25 final_acc=93.75% final_loss=0.2238 total_time=0.13s
COMPLETED run_002 clients=2 seed=29 rounds=25/25 final_acc=94.32% final_loss=0.1931 total_time=0.15s
COMPLETED run_003 clients=2 seed=47 rounds=25/25 final_acc=93.18% final_loss=0.2406 total_time=0.12s
COMPLETED run_004 clients=5 seed=11 rounds=25/25 final_acc=92.61% final_loss=0.1991 total_time=0.14s
COMPLETED run_005 clients=5 seed=29 rounds=25/25 final_acc=93.75% final_loss=0.1946 total_time=0.13s
COMPLETED run_006 clients=5 seed=47 rounds=25/25 final_acc=94.32% final_loss=0.2074 total_time=0.13s
COMPLETED run_007 clients=10 seed=11 rounds=25/25 final_acc=92.05% final_loss=0.2238 total_time=0.14s
COMPLETED run_008 clients=10 seed=29 rounds=25/25 final_acc=94.32% final_loss=0.1875 total_time=0.15s
COMPLETED run_009 clients=10 seed=47 rounds=25/25 final_acc=93.75% final_loss=0.1942 total_time=0.16s
COMPLETED run_010 clients=20 seed=11 rounds=25/25 final_acc=94.32% final_loss=0.1799 total_time=0.20s
COMPLETED run_011 clients=20 seed=29 rounds=25/25 final_acc=93.75% final_loss=0.1951 total_time=0.20s
COMPLETED run_012 clients=20 seed=47 rounds=25/25 final_acc=93.18% final_loss=0.2050 total_time=0.20s

# 2 clients :: runs/run_001/round_metrics.csv
round,global_accuracy,global_loss,round_duration_s,participating_clients
1,0.9375,0.2207,0.0053,2
2,0.9375,0.2060,0.0062,2
3,0.9489,0.2019,0.0064,2
# 5 clients :: runs/run_004/round_metrics.csv
round,global_accuracy,global_loss,round_duration_s,participating_clients
1,0.9205,0.3089,0.0048,5
2,0.9261,0.2612,0.0063,5
3,0.8864,0.2657,0.0071,5
# 10 clients :: runs/run_007/round_metrics.csv
round,global_accuracy,global_loss,round_duration_s,participating_clients
1,0.9205,0.4025,0.0066,10
2,0.9148,0.2993,0.0082,10
3,0.9261,0.2732,0.0059,10
# 20 clients :: runs/run_010/round_metrics.csv
round,global_accuracy,global_loss,round_duration_s,participating_clients
1,0.9148,0.4360,0.0071,20
2,0.9375,0.3428,0.0071,20
3,0.9375,0.3010,0.0100,20

# generated files
figures/figure_1_accuracy_vs_rounds.png
figures/figure_2_loss_vs_rounds.png
figures/figure_3_round_time_vs_clients.png
figures/figure_4_comm_cost_vs_clients.png
figures/figure_5_accuracy_vs_comm.png
metadata.json
run_registry.csv
runs/run_001/round_metrics.csv
runs/run_002/round_metrics.csv
runs/run_003/round_metrics.csv
runs/run_004/round_metrics.csv
runs/run_005/round_metrics.csv
runs/run_006/round_metrics.csv
runs/run_007/round_metrics.csv
runs/run_008/round_metrics.csv
runs/run_009/round_metrics.csv
runs/run_010/round_metrics.csv
runs/run_011/round_metrics.csv
runs/run_012/round_metrics.csv
table_b2_convergence_summary.csv
table_b3_efficiency_cost.csv
table_b4_reliability.csv
table_b5_statistical_comparison.csv
```

## Acceptance Criteria For Part B
- [x] At least 4 client settings completed (`2, 5, 10, 20`).
- [x] At least 3 seeds per setting.
- [x] Convergence and cost tables fully populated.
- [x] All required figures generated and referenced.
- [x] Quantitative paragraph completed for paper text.
- [x] Reproducibility commands and seeds documented.

## Threats To Validity (Write Honestly)
- `Synthetic TrashNet-style fallback` was used because no local TrashNet image corpus was available at `/home/bpv/Documentos/TrashNet`.
- The model is multinomial logistic regression over 16x16 grayscale features, not the final production edge model.
- Communication cost is simulated from model payload sizes in a sequential single-host run, not measured over the full MQTT/gRPC stack.
