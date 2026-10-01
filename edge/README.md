# TrashUQ edge runtime

The UNO Q MPU daemon captures camera bursts, classifies cardboard, glass, paper,
and plastic with the included TFLite model, and communicates with the MCU over
serial. It publishes MQTT telemetry and optionally trains a small NumPy
calibration head for federated learning. TensorFlow is only needed for model
training or as a desktop fallback interpreter.

## Setup and run

Run commands from this directory. Supported Python versions are 3.11 and 3.12
(use 3.11 on the MPU). Install `uv`, then:

```sh
uv sync --extra hardware
uv run python -m bin_mpu.main --bin-class paper --mqtt-host localhost
```

The `hardware` extra requires a compatible `tflite-runtime` wheel. On a compatible
desktop Python environment, use `uv sync --extra train` for the TensorFlow fallback.
For synthetic camera frames and a stub MCU, add `--fake-camera --no-mcu`.
The labeling UI is at `http://localhost:8080` and the monitor at `/monitor`.
Use `--help` for device ID, camera, model, serial, and server options. Defaults
target the historical validation host `bepes-server`; override hosts for local demos.

For FL, start the backend with `FL_MODEL_SIZE=20`, then add `--fl --fl-host localhost`.
The four-class calibration head contains 4×4 weights and 4 biases. Its size must
match the coordinator. Fine-tuning needs user-labeled samples, not TensorFlow.

## Validate without hardware

```sh
uv run --extra dev pytest
uv run python -m bin_mpu.main --help
```

Tests use fake classifiers and do not require TensorFlow or a real model interpreter.
For dashboard telemetry and gRPC demos without hardware, see
[demo scripts](../docs/demos/mockups/README.md) and the root README.
For performance measurements see [benchmarks](benchmarks/README.md).

## Source and data

- `bin_mpu/`: Python runtime, monitoring, labeling, and FL client.
- `bin_mcu/`: Arduino firmware for sensors, LEDs, and the lid.
- `models/trash_classifier.tflite`: included inference model.
- `model/`: training and export scripts; `model/trashnet/` preserves upstream source and license.
- `tests/`, `benchmarks/`, `tools/`, and `scripts/manual/`: validation and demo utilities.

Training datasets and `model/output/` are not included. The old `.gitmodules`
metadata describes the original dataset sources, but this repository contains
vendored TrashNet source rather than registered submodules. `setup_data.py` needs
the dataset archives/directories supplied separately; it cannot provision them
from a fresh clone. This does not affect the included inference model or telemetry demo.
