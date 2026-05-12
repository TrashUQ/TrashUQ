#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat << 'USAGE'
MQTT simulator for FederatedCans dashboard.

Usage:
  bash scripts/mqtt-simulator.sh [profile] [options]

Profiles:
  normal (default)
  alert
  chaos

Options:
  --host <ip-or-host>             MQTT host (default from MQTT_HOST or 127.0.0.1)
  --port <port>                   MQTT port (default from MQTT_PORT or 1883)
  --topic-root <root>             Topic root (default from MQTT_TOPIC_ROOT or arduino)
  --username <username>           MQTT username (optional, default from MQTT_USERNAME)
  --password <password>           MQTT password (optional, default from MQTT_PASSWORD)
  --devices <csv>                 Device IDs CSV (default UNO-Q1,UNO-Q2,UNO-Q3)
  --coordinator-id <id>           Coordinator ID (default coordinator)
  --interval <seconds>            Loop interval in seconds (default 2)
  --ticks <count>                 Stop after N ticks (default 0 = run forever)
  --qos-status-metrics <0|1|2>    QoS for status/metrics (default 1)
  --qos-stream <0|1|2>            QoS for event/log/help/classification (default 0)
  --retain-status-metrics <0|1>   Retain status/metrics messages (default 1)
  --inject-invalid-every <N>      Publish invalid status/metrics every N ticks (default 0 = off)
  -h, --help                      Show this help

Examples:
  npm run mqtt:sim
  npm run mqtt:sim -- alert --interval 1
  npm run mqtt:sim -- chaos --ticks 60 --inject-invalid-every 10
USAGE
}

HOST="${MQTT_HOST:-127.0.0.1}"
PORT="${MQTT_PORT:-1883}"
TOPIC_ROOT="${MQTT_TOPIC_ROOT:-arduino}"
MQTT_USERNAME="${MQTT_USERNAME:-}"
MQTT_PASSWORD="${MQTT_PASSWORD:-}"
PROFILE="${1:-normal}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-2}"
SIM_MAX_TICKS="${SIM_MAX_TICKS:-0}"
COORDINATOR_ID="${COORDINATOR_ID:-coordinator}"
DEVICES_CSV="${DEVICES:-UNO-Q1,UNO-Q2,UNO-Q3}"
QOS_STATUS_METRICS="${QOS_STATUS_METRICS:-1}"
QOS_STREAM="${QOS_STREAM:-0}"
RETAIN_STATUS_METRICS="${RETAIN_STATUS_METRICS:-1}"
INJECT_INVALID_EVERY="${INJECT_INVALID_EVERY:-0}"

if [[ "${PROFILE}" == "-h" || "${PROFILE}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "${PROFILE}" == --* ]]; then
  PROFILE="normal"
else
  shift || true
fi

while [ "$#" -gt 0 ]; do
  case "$1" in
    --host)
      HOST="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --topic-root)
      TOPIC_ROOT="$2"
      shift 2
      ;;
    --devices)
      DEVICES_CSV="$2"
      shift 2
      ;;
    --username)
      MQTT_USERNAME="$2"
      shift 2
      ;;
    --password)
      MQTT_PASSWORD="$2"
      shift 2
      ;;
    --coordinator-id)
      COORDINATOR_ID="$2"
      shift 2
      ;;
    --interval)
      INTERVAL_SECONDS="$2"
      shift 2
      ;;
    --ticks)
      SIM_MAX_TICKS="$2"
      shift 2
      ;;
    --qos-status-metrics)
      QOS_STATUS_METRICS="$2"
      shift 2
      ;;
    --qos-stream)
      QOS_STREAM="$2"
      shift 2
      ;;
    --retain-status-metrics)
      RETAIN_STATUS_METRICS="$2"
      shift 2
      ;;
    --inject-invalid-every)
      INJECT_INVALID_EVERY="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if ! command -v mosquitto_pub >/dev/null 2>&1; then
  echo "mosquitto_pub is required but not installed." >&2
  exit 1
fi

is_uint() {
  [[ "$1" =~ ^[0-9]+$ ]]
}

require_uint_ge() {
  local value="$1"
  local min="$2"
  local label="$3"
  if ! is_uint "$value" || [ "$value" -lt "$min" ]; then
    echo "$label must be an integer >= $min" >&2
    exit 1
  fi
}

require_qos() {
  local value="$1"
  local label="$2"
  if [[ "$value" != "0" && "$value" != "1" && "$value" != "2" ]]; then
    echo "$label must be 0, 1, or 2" >&2
    exit 1
  fi
}

require_bool_01() {
  local value="$1"
  local label="$2"
  if [[ "$value" != "0" && "$value" != "1" ]]; then
    echo "$label must be 0 or 1" >&2
    exit 1
  fi
}

require_uint_ge "$INTERVAL_SECONDS" 1 "INTERVAL_SECONDS"
require_uint_ge "$SIM_MAX_TICKS" 0 "SIM_MAX_TICKS"
require_uint_ge "$INJECT_INVALID_EVERY" 0 "INJECT_INVALID_EVERY"
require_qos "$QOS_STATUS_METRICS" "QOS_STATUS_METRICS"
require_qos "$QOS_STREAM" "QOS_STREAM"
require_bool_01 "$RETAIN_STATUS_METRICS" "RETAIN_STATUS_METRICS"

if [[ "$PROFILE" != "normal" && "$PROFILE" != "alert" && "$PROFILE" != "chaos" ]]; then
  echo "Unknown profile: $PROFILE (use: normal | alert | chaos)" >&2
  exit 1
fi

IFS=',' read -r -a DEVICES <<< "$DEVICES_CSV"
if [ "${#DEVICES[@]}" -eq 0 ]; then
  echo "No devices configured. Set DEVICES env var or --devices." >&2
  exit 1
fi

publish() {
  local topic="$1"
  local payload="$2"
  local qos="$3"
  local retain="$4"
  local auth_args=()

  if [ -n "$MQTT_USERNAME" ]; then
    auth_args+=("-u" "$MQTT_USERNAME")
    if [ -n "$MQTT_PASSWORD" ]; then
      auth_args+=("-P" "$MQTT_PASSWORD")
    fi
  fi

  if [ "$retain" = "1" ]; then
    mosquitto_pub -h "$HOST" -p "$PORT" -q "$qos" "${auth_args[@]}" -r -t "$topic" -m "$payload"
  else
    mosquitto_pub -h "$HOST" -p "$PORT" -q "$qos" "${auth_args[@]}" -t "$topic" -m "$payload"
  fi
}

rand_between() {
  local min="$1"
  local max="$2"
  echo $((min + RANDOM % (max - min + 1)))
}

pick_label() {
  local labels=("plastic" "metal" "paper" "glass" "organic")
  echo "${labels[RANDOM % ${#labels[@]}]}"
}

on_exit() {
  echo
  echo "Stopping MQTT simulator."
}
trap on_exit EXIT INT TERM

echo "MQTT simulator started"
echo "broker=${HOST}:${PORT} topic_root=${TOPIC_ROOT} profile=${PROFILE} interval=${INTERVAL_SECONDS}s"
echo "devices=${DEVICES[*]} max_ticks=${SIM_MAX_TICKS} qos_status_metrics=${QOS_STATUS_METRICS} qos_stream=${QOS_STREAM} retain_status_metrics=${RETAIN_STATUS_METRICS}"

tick=0
while true; do
  tick=$((tick + 1))
  now="$(date '+%H:%M:%S')"

  online_count=0
  cpu_total=0
  ram_total=0

  for device in "${DEVICES[@]}"; do
    status="Online"
    mode="Training"

    case "$PROFILE" in
      alert)
        cpu="$(rand_between 75 98)"
        ram="$(rand_between 68 96)"
        temp="$(rand_between 62 78)"
        if [ $((RANDOM % 8)) -eq 0 ]; then
          status="Offline"
          mode="Disconnected"
          cpu=0
          ram=0
          temp=0
        fi
        ;;
      chaos)
        cpu="$(rand_between 5 99)"
        ram="$(rand_between 8 99)"
        temp="$(rand_between 35 85)"
        roll=$((RANDOM % 6))
        if [ "$roll" -eq 0 ]; then
          mode="Idle"
        elif [ "$roll" -eq 1 ]; then
          mode="Recovery"
        fi
        if [ $((RANDOM % 4)) -eq 0 ]; then
          status="Offline"
          mode="Disconnected"
          cpu=0
          ram=0
          temp=0
        fi
        ;;
      *)
        cpu="$(rand_between 22 88)"
        ram="$(rand_between 28 84)"
        temp="$(rand_between 42 64)"
        if [ $((RANDOM % 12)) -eq 0 ]; then
          mode="Idle"
        fi
        if [ $((RANDOM % 25)) -eq 0 ]; then
          status="Offline"
          mode="Disconnected"
          cpu=0
          ram=0
          temp=0
        fi
        ;;
    esac

    heartbeat_ms="$(rand_between 24 120)"

    publish "${TOPIC_ROOT}/${device}/status" \
      "{\"cpu\":${cpu},\"ram\":${ram},\"temp\":\"${temp}C\",\"heartbeat\":\"${heartbeat_ms} ms\",\"mode\":\"${mode}\",\"status\":\"${status}\"}" \
      "$QOS_STATUS_METRICS" "$RETAIN_STATUS_METRICS"

    label="$(pick_label)"
    confidence="$(rand_between 62 99)"
    publish "${TOPIC_ROOT}/${device}/classification" \
      "{\"device\":\"${device}\",\"label\":\"${label}\",\"confidence\":${confidence},\"ts\":\"${now}\",\"seq\":${tick}}" \
      "$QOS_STREAM" "0"

    if [ "$PROFILE" = "alert" ] || [ "$PROFILE" = "chaos" ] || [ $((tick % 3)) -eq 0 ]; then
      publish "${TOPIC_ROOT}/${device}/logs" \
        "${now} ${device} heap=$(rand_between 1200 2000) free=$(rand_between 400 900)" \
        "$QOS_STREAM" "0"
    fi

    if [ "$PROFILE" = "alert" ] || [ "$PROFILE" = "chaos" ]; then
      publish "${TOPIC_ROOT}/${device}/event" \
        "${now} ${device} ${PROFILE} tick=${tick} temp=${temp}C" \
        "$QOS_STREAM" "0"
    elif [ $((tick % 4)) -eq 0 ]; then
      publish "${TOPIC_ROOT}/${device}/event" \
        "${now} ${device} local batch processed" \
        "$QOS_STREAM" "0"
    fi

    if [ "$status" = "Online" ]; then
      online_count=$((online_count + 1))
      cpu_total=$((cpu_total + cpu))
      ram_total=$((ram_total + ram))
    fi

    if [ "$PROFILE" = "alert" ] && [ $((RANDOM % 5)) -eq 0 ]; then
      publish "${TOPIC_ROOT}/${device}/help" \
        "critical: ${device} high temp ${temp}C / check cooling" \
        "$QOS_STREAM" "0"
    fi

    if [ "$PROFILE" = "chaos" ] && [ $((RANDOM % 3)) -eq 0 ]; then
      publish "${TOPIC_ROOT}/${device}/help" \
        "urgent: ${device} unstable telemetry spike" \
        "$QOS_STREAM" "0"
    fi
  done

  if [ "$online_count" -gt 0 ]; then
    avg_cpu=$((cpu_total / online_count))
    avg_ram=$((ram_total / online_count))
  else
    avg_cpu=0
    avg_ram=0
  fi

  case "$PROFILE" in
    alert)
      global_accuracy="$(rand_between 78 91)"
      global_loss="0.$(rand_between 35 78)"
      ;;
    chaos)
      global_accuracy="$(rand_between 70 95)"
      global_loss="0.$(rand_between 15 95)"
      ;;
    *)
      global_accuracy="$(rand_between 88 96)"
      global_loss="0.$(rand_between 12 42)"
      ;;
  esac

  publish "${TOPIC_ROOT}/${COORDINATOR_ID}/metrics" \
    "{\"globalAccuracy\":${global_accuracy},\"globalLoss\":${global_loss},\"avgCpu\":${avg_cpu},\"avgRam\":${avg_ram},\"onlineClients\":${online_count}}" \
    "$QOS_STATUS_METRICS" "$RETAIN_STATUS_METRICS"

  if [ "$PROFILE" = "alert" ] && [ $((tick % 2)) -eq 0 ]; then
    publish "${TOPIC_ROOT}/${COORDINATOR_ID}/event" \
      "${now} coordinator degraded mode: packet retries increased" \
      "$QOS_STREAM" "0"
  fi

  if [ "$PROFILE" = "chaos" ] && [ $((tick % 2)) -eq 0 ]; then
    publish "${TOPIC_ROOT}/${COORDINATOR_ID}/event" \
      "${now} coordinator jitter: retransmit burst" \
      "$QOS_STREAM" "0"
  fi

  if [ "$INJECT_INVALID_EVERY" -gt 0 ] && [ $((tick % INJECT_INVALID_EVERY)) -eq 0 ]; then
    publish "${TOPIC_ROOT}/${DEVICES[0]}/status" '{"cpu":"bad","ram":"NaN","status":77}' "$QOS_STREAM" "0"
    publish "${TOPIC_ROOT}/${COORDINATOR_ID}/metrics" '{"globalAccuracy":"bad","globalLoss":"oops"}' "$QOS_STREAM" "0"
  fi

  if [ "$SIM_MAX_TICKS" -gt 0 ] && [ "$tick" -ge "$SIM_MAX_TICKS" ]; then
    echo "Reached max ticks (${SIM_MAX_TICKS}). Exiting."
    break
  fi

  sleep "$INTERVAL_SECONDS"
done
