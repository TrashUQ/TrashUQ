#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat << 'USAGE'
Mosquitto hardening setup (auth + ACL + websockets).

Usage:
  bash scripts/mosquitto-hardening.sh [options]

Options:
  --topic-root <root>           MQTT topic root (default: arduino)
  --dashboard-user <user>       Read-only dashboard user (default: dashboard_ro)
  --publisher-user <user>       Write publisher user for devices/coordinator (default: edge_rw)
  --bind-all                    Bind listeners to 0.0.0.0 (default is localhost-only)
  --yes                         Non-interactive mode (requires env passwords)
  -h, --help                    Show help

Environment (optional):
  DASHBOARD_PASS                Password for dashboard user
  PUBLISHER_PASS                Password for publisher user

Notes:
  - Requires sudo permissions.
  - This script writes:
      /etc/mosquitto/conf.d/security-auth.conf
      /etc/mosquitto/acl
      /etc/mosquitto/passwd
USAGE
}

TOPIC_ROOT="arduino"
DASHBOARD_USER="dashboard_ro"
PUBLISHER_USER="edge_rw"
BIND_ADDR="127.0.0.1"
ASSUME_YES="0"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --topic-root)
      TOPIC_ROOT="$2"
      shift 2
      ;;
    --dashboard-user)
      DASHBOARD_USER="$2"
      shift 2
      ;;
    --publisher-user)
      PUBLISHER_USER="$2"
      shift 2
      ;;
    --bind-all)
      BIND_ADDR="0.0.0.0"
      shift
      ;;
    --yes)
      ASSUME_YES="1"
      shift
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

if ! command -v mosquitto_passwd >/dev/null 2>&1; then
  echo "mosquitto_passwd is required but not found." >&2
  exit 1
fi

DASHBOARD_PASS="${DASHBOARD_PASS:-}"
PUBLISHER_PASS="${PUBLISHER_PASS:-}"

if [ -z "$DASHBOARD_PASS" ]; then
  read -r -s -p "Password for ${DASHBOARD_USER}: " DASHBOARD_PASS
  echo
fi
if [ -z "$PUBLISHER_PASS" ]; then
  read -r -s -p "Password for ${PUBLISHER_USER}: " PUBLISHER_PASS
  echo
fi

if [ -z "$DASHBOARD_PASS" ] || [ -z "$PUBLISHER_PASS" ]; then
  echo "Passwords cannot be empty." >&2
  exit 1
fi

if [ "$ASSUME_YES" != "1" ]; then
  echo ""
  echo "Will apply hardening with these settings:"
  echo "  topic root      : ${TOPIC_ROOT}"
  echo "  dashboard user  : ${DASHBOARD_USER} (read-only)"
  echo "  publisher user  : ${PUBLISHER_USER} (write)"
  echo "  bind address    : ${BIND_ADDR}"
  read -r -p "Continue? [y/N]: " confirm
  case "$confirm" in
    y|Y|yes|YES) ;;
    *) echo "Aborted."; exit 1 ;;
  esac
fi

tmpdir="$(mktemp -d)"
cleanup() {
  rm -rf "$tmpdir"
}
trap cleanup EXIT

ACL_FILE_TMP="$tmpdir/acl"
CONF_FILE_TMP="$tmpdir/security-auth.conf"
PASSWD_FILE_TMP="$tmpdir/passwd"

cat > "$ACL_FILE_TMP" <<ACL
# Dashboard user: read-only access to UI topics
user ${DASHBOARD_USER}
topic read ${TOPIC_ROOT}/+/status
topic read ${TOPIC_ROOT}/+/metrics
topic read ${TOPIC_ROOT}/+/event
topic read ${TOPIC_ROOT}/+/classification
topic read ${TOPIC_ROOT}/+/help
topic read ${TOPIC_ROOT}/+/logs

# Publisher user: write access for devices/coordinator
user ${PUBLISHER_USER}
topic write ${TOPIC_ROOT}/+/status
topic write ${TOPIC_ROOT}/+/metrics
topic write ${TOPIC_ROOT}/+/event
topic write ${TOPIC_ROOT}/+/classification
topic write ${TOPIC_ROOT}/+/help
topic write ${TOPIC_ROOT}/+/logs
ACL

cat > "$CONF_FILE_TMP" <<CONF
per_listener_settings true

listener 1883 ${BIND_ADDR}
protocol mqtt
allow_anonymous false
password_file /etc/mosquitto/passwd
acl_file /etc/mosquitto/acl

listener 9001 ${BIND_ADDR}
protocol websockets
allow_anonymous false
password_file /etc/mosquitto/passwd
acl_file /etc/mosquitto/acl
CONF

mosquitto_passwd -b -c "$PASSWD_FILE_TMP" "$DASHBOARD_USER" "$DASHBOARD_PASS" >/dev/null 2>&1
mosquitto_passwd -b "$PASSWD_FILE_TMP" "$PUBLISHER_USER" "$PUBLISHER_PASS" >/dev/null 2>&1

sudo mkdir -p /etc/mosquitto/conf.d
sudo install -m 600 "$ACL_FILE_TMP" /etc/mosquitto/acl
sudo install -m 600 "$PASSWD_FILE_TMP" /etc/mosquitto/passwd

# Remove old listener files to avoid duplicate port bindings
sudo rm -f /etc/mosquitto/conf.d/websockets.conf /etc/mosquitto/conf.d/mosquitto-websockets.conf
sudo install -m 644 "$CONF_FILE_TMP" /etc/mosquitto/conf.d/security-auth.conf

# Ensure include_dir exists exactly once
sudo sed -i '\#^include_dir /etc/mosquitto/conf.d$#d' /etc/mosquitto/mosquitto.conf
printf '%s\n' 'include_dir /etc/mosquitto/conf.d' | sudo tee -a /etc/mosquitto/mosquitto.conf >/dev/null

sudo systemctl reset-failed mosquitto
sudo systemctl restart mosquitto

echo ""
echo "Mosquitto hardening applied."
echo ""
echo "Check service/ports:"
echo "  sudo systemctl status mosquitto --no-pager -l"
echo "  sudo ss -ltnp | grep -E ':1883|:9001'"
echo ""
echo "Update dashboard .env.local with:"
echo "  NEXT_PUBLIC_MQTT_BROKER_URL=ws://localhost:9001"
echo "  NEXT_PUBLIC_MQTT_TOPIC_ROOT=${TOPIC_ROOT}"
echo "  NEXT_PUBLIC_MQTT_USERNAME=${DASHBOARD_USER}"
echo "  NEXT_PUBLIC_MQTT_PASSWORD=<your-dashboard-password>"
echo ""
echo "For simulator/manual publish use:"
echo "  MQTT_USERNAME=${PUBLISHER_USER} MQTT_PASSWORD=<your-publisher-password> npm run mqtt:sim"
