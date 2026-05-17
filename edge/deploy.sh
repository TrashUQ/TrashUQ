#!/usr/bin/env bash
# Sync the bin daemon to the UNO Q over SSH.
#
#   ./deploy.sh                 # rsync code only
#   ./deploy.sh --run           # rsync, then start the daemon over SSH
#
# Override the target with env vars:
#   BOARD=arduino@192.168.1.40 DEVICE_ID=unoq-01 CAMERA=real ./deploy.sh --run
#   BOARD=arduino@192.168.1.41 DEVICE_ID=unoq-02 CAMERA=fake ./deploy.sh --run
set -euo pipefail

BOARD="${BOARD:-arduino@172.20.10.2}"
REMOTE_DIR="${REMOTE_DIR:-~/trashNet}"
SERVER_HOST="${SERVER_HOST:-172.20.10.12}"       # where TrashUQ backend + MQTT run
CAMERA_INDEX="${CAMERA_INDEX:-2}"                # UVC USB camera index
CAMERA="${CAMERA:-real}"                         # real | fake
DEVICE_ID="${DEVICE_ID:-}"                       # e.g. unoq-01 / unoq-02 (empty → daemon default)
BIN_CLASS="${BIN_CLASS:-paper}"
FL_TRIGGER_SAMPLES="${FL_TRIGGER_SAMPLES:-2}"
HTTP_PORT="${HTTP_PORT:-8080}"

echo "→ Syncing to ${BOARD}:${REMOTE_DIR}"
rsync -avz --delete \
  --exclude '.git/' --exclude '__pycache__/' --exclude '.venv/' \
  --exclude '.ruff_cache/' --exclude '.mypy_cache/' --exclude '.pytest_cache/' \
  --exclude '.DS_Store' --exclude 'data/' \
  --exclude 'model/output/' --exclude 'model/TrashBox/' \
  --exclude 'model/trashnet/data/dataset-resized/' \
  --exclude 'benchmarks/_workdir/' --exclude 'benchmarks/results/' \
  ./ "${BOARD}:${REMOTE_DIR}/"

REMOTE_PATH='export PATH="$HOME/.local/bin:$PATH"'

echo "→ Ensuring NumPy<2 is pinned on the board"
ssh "${BOARD}" "${REMOTE_PATH} && cd ${REMOTE_DIR} && uv pip install --quiet 'numpy<2'"

if [[ "${CAMERA}" == "fake" ]]; then
  CAM_ARGS="--fake-camera"
else
  CAM_ARGS="--camera-index ${CAMERA_INDEX}"
fi

DEVICE_ARGS=""
if [[ -n "${DEVICE_ID}" ]]; then
  DEVICE_ARGS="--device-id ${DEVICE_ID}"
fi

CMD="${REMOTE_PATH} && uv run --no-sync python -m bin_mpu.main \
  --bin-class ${BIN_CLASS} ${DEVICE_ARGS} \
  ${CAM_ARGS} --no-mcu \
  --http-port ${HTTP_PORT} \
  --mqtt-host ${SERVER_HOST} \
  --fl --fl-host ${SERVER_HOST} --fl-trigger-samples ${FL_TRIGGER_SAMPLES} \
  --log-level INFO"

if [[ "${1:-}" == "--run" ]]; then
  echo "→ Starting daemon on ${BOARD}"
  echo "    device_id=${DEVICE_ID:-<default>}  camera=${CAMERA}  bin=${BIN_CLASS}  server=${SERVER_HOST}"
  ssh -t "${BOARD}" "cd ${REMOTE_DIR} && ${CMD}"
else
  echo "✓ Synced. To run the daemon:"
  echo "  ssh ${BOARD}"
  echo "  cd ${REMOTE_DIR} && ${CMD}"
fi
