# benchmarks/

Performance + integration benchmarks for the bin daemon.

| Bench | What it measures | Needs |
|---|---|---|
| `bench_inference.py` | TFLite single-frame + 5-frame burst latency, capture-cycle estimate | `models/trash_classifier.tflite` |
| `bench_finetune.py` | Cold-start, feature extraction, head training per epoch, full FL round vs. sample count | `tensorflow` (`uv pip install -e ".[train]"`) |
| `bench_grpc.py` | Join / GetGlobalModel / SubmitUpdate RTT against the TrashUQ FL coordinator | TrashUQ backend reachable on `:50051` |
| `bench_mqtt.py` | Publish→receive RTT through the Mosquitto broker | Mosquitto reachable on `:1883` |
| `bench_e2e.py` | PIR trigger → capture → inference → lid-open latency (camera + MCU mocked) | `models/trash_classifier.tflite` |
| `run_all.py` | Runs everything in sequence and prints a summary | as above |

Reports are written to `benchmarks/results/*.json`.

## Quickstart

```bash
# 1. Make sure the backend is up (in TrashUQ/)
cd ../TrashUQ
FL_MIN_CLIENTS_PER_ROUND=1 FL_MODEL_SIZE=16 docker compose up -d db mqtt backend

# 2. Run all benches (from trashNet/)
cd -
uv run --extra train python -m benchmarks.run_all --grpc-host localhost --mqtt-host localhost
```

If the backend isn't running, use `--skip grpc mqtt`:

```bash
uv run --extra train python -m benchmarks.run_all --skip grpc mqtt
```

## Tuning the FL weights-size mismatch

The fine-tuner ships the flattened head (~1.6k floats by default).
The backend coordinator validates `len(local_weights) == FL_MODEL_SIZE`, default `16`.

For end-to-end FL benchmarking either:
- Set `FL_MODEL_SIZE` on the backend to the value `bench_finetune` prints under "head_weight_length", **or**
- Use `bench_grpc --weights-size 16` to just measure RPC RTT with the default backend.
