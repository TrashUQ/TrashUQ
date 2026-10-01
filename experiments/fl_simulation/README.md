# Federated learning simulations

These scripts produce the synthetic-data scalability and compression experiments
reported in the paper. Run commands from the repository root in a Python environment
with the dependencies from `experiments/fl_simulation/requirements.txt` installed.

```sh
python -m pip install -r experiments/fl_simulation/requirements.txt
python experiments/fl_simulation/run_part_b.py
python experiments/fl_simulation/compare_methods.py --output-dir artifacts/comparison
```

The default Part B run uses 2, 5, 10, and 20 clients, 25 rounds, three seeds, and
Dirichlet alpha 0.3. If the default TrashNet dataset directory is unavailable, the
runner uses synthetic data and records that choice in its metadata. Supply
`--dataset-root` to use a real dataset. Synthetic-data accuracy does not measure
real-world waste classification accuracy.

Outputs under `artifacts/` are ignored by Git. Preserve results needed for your
submission before rerunning with the same output directory. Use `--help` to inspect
all options. A quick smoke run is:

```sh
python experiments/fl_simulation/run_part_b.py --client-counts 2 --seeds 11 --rounds 2 --output-dir artifacts/smoke
```
