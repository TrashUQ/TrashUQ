# MQTT Guide - FederatedCans Dashboard

This document covers the MQTT side owned by this repo (operational telemetry and live UI).
Federated training truth (rounds, aggregation, model lifecycle) is managed by gRPC.

## 0) Run The Project End-To-End

### Requirements
- Node.js `>= 22.13` (tested on `22.22.0`)
- npm
- Mosquitto running locally with:
  - MQTT listener on `127.0.0.1:1883`
  - WebSocket listener on `127.0.0.1:9001`

### First-time setup

```bash
npm install
npm run db:migrate
```

### Local demo mode (anonymous broker, no username/password)

`.env.local`:

```env
NEXT_PUBLIC_MQTT_BROKER_URL=ws://localhost:9001
NEXT_PUBLIC_MQTT_TOPIC_ROOT=arduino
```

### Start dashboard

```bash
npm run dev
```

### Send live data quickly (recommended)

```bash
npm run mqtt:sim:alert
```

### Build check (production compile)

```bash
npm run build
```

## 1) Topic Contract (What MQTT Must Publish)

Topic root defaults to `arduino` (configurable by `NEXT_PUBLIC_MQTT_TOPIC_ROOT`).

Dashboard connection env vars:
- `NEXT_PUBLIC_MQTT_BROKER_URL` (e.g. `ws://localhost:9001`)
- `NEXT_PUBLIC_MQTT_TOPIC_ROOT` (e.g. `arduino`)
- `NEXT_PUBLIC_MQTT_USERNAME` (required when `allow_anonymous false`)
- `NEXT_PUBLIC_MQTT_PASSWORD` (required when `allow_anonymous false`)

### Device status
- Topic: `arduino/<deviceId>/status`
- Purpose: live device health and runtime state.
- Example payload:

```json
{"cpu":80,"ram":67,"temp":"58C","heartbeat":"35 ms","mode":"Training","status":"Online"}
```

Accepted fields by UI validator:
- `cpu` number (0..100, clamped)
- `ram` number (0..100, clamped)
- `temp` string
- `heartbeat` string
- `mode` string
- `status` string

### Coordinator metrics (non-round)
- Topic: `arduino/<coordinatorId>/metrics`
- Purpose: operational summary used in Overview.
- Example payload:

```json
{"globalAccuracy":93.4,"globalLoss":0.28,"avgCpu":61,"avgRam":58,"onlineClients":2}
```

Used fields by UI validator:
- `globalAccuracy` or `global_accuracy` or `accuracy` (number)
- `globalLoss` or `global_loss` or `loss` (number)

### Event stream
- Topic: `arduino/<deviceId>/event`
- Purpose: free text event lines in Event Stream.
- Example:

```text
17:02:10 UNO-Q1 local batch processed
```

### Logs
- Topic: `arduino/<deviceId>/logs`
- Purpose: diagnostic logs in Event Stream.
- Example:

```text
17:02:10 UNO-Q1 heap=1520 free=710
```

### Classification
- Topic: `arduino/<deviceId>/classification`
- Purpose: live inference/classification feed.
- Example payload:

```json
{"device":"UNO-Q1","label":"plastic","confidence":0.91,"ts":"17:02:10","seq":42}
```

### Help requests
- Topic: `arduino/<deviceId>/help`
- Purpose: escalation/help feed.
- Example:

```text
critical: UNO-Q2 high temp 74C / check cooling
```

---

## 2) Retained + QoS Policy (Recommended)

### Why
- Retained status/metrics let the dashboard show last known values immediately after reload.
- QoS 1 reduces chance of losing important messages.

### Recommended policy
- `status`: `retain=true`, `qos=1`
- `metrics`: `retain=true`, `qos=1`
- `event/logs/classification/help`: `retain=false`, `qos=0` (or `qos=1` if needed)

### Manual publish examples

Status retained + QoS 1:

```bash
mosquitto_pub -h 127.0.0.1 -p 1883 -q 1 -r -t arduino/UNO-Q1/status -m '{"cpu":80,"ram":66,"temp":"58C","heartbeat":"35 ms","mode":"Training","status":"Online"}'
```

Metrics retained + QoS 1:

```bash
mosquitto_pub -h 127.0.0.1 -p 1883 -q 1 -r -t arduino/coordinator/metrics -m '{"globalAccuracy":93.2,"globalLoss":0.25}'
```

Non-retained event:

```bash
mosquitto_pub -h 127.0.0.1 -p 1883 -q 0 -t arduino/UNO-Q1/event -m 'manual event test'
```

### Clear a retained topic
Publish empty retained payload:

```bash
mosquitto_pub -h 127.0.0.1 -p 1883 -r -t arduino/UNO-Q1/status -n
```

---

## 3) MQTT Simulator

File: `scripts/mqtt-simulator.sh`

### Quick start

Normal traffic:

```bash
npm run mqtt:sim
```

Alert traffic:

```bash
npm run mqtt:sim:alert
```

Chaos traffic:

```bash
npm run mqtt:sim:chaos
```

Short demo (30 ticks, 1 second interval):

```bash
npm run mqtt:sim:demo
```

If broker auth is enabled:

```bash
MQTT_USERNAME=edge_rw MQTT_PASSWORD='<publisher-pass>' npm run mqtt:sim
```

### What simulator publishes
Per device (`UNO-Q1..Q3` by default):
- `status`
- `classification`
- `logs`
- `event`
- `help` (more frequent in alert/chaos)

Per coordinator:
- `metrics` (globalAccuracy/globalLoss + aggregate fields)
- `event` (in alert/chaos)

### Advanced options

```bash
npm run mqtt:sim -- alert --interval 1 --ticks 120 --devices UNO-Q1,UNO-Q2
```

Supported flags:
- `--host`
- `--port`
- `--topic-root`
- `--devices`
- `--coordinator-id`
- `--interval`
- `--ticks` (0 = infinite)
- `--qos-status-metrics`
- `--qos-stream`
- `--retain-status-metrics` (0/1)
- `--inject-invalid-every` (for validator testing)

Examples:

Retained/QoS strict run:

```bash
npm run mqtt:sim -- normal --qos-status-metrics 1 --qos-stream 0 --retain-status-metrics 1
```

Validation stress (inject invalid payload every 10 ticks):

```bash
npm run mqtt:sim -- chaos --inject-invalid-every 10
```

Validation stress with authenticated broker:

```bash
MQTT_USERNAME=edge_rw MQTT_PASSWORD='<publisher-pass>' npm run mqtt:sim -- chaos --inject-invalid-every 10
```

### Test scenarios checklist

1. Live device updates:
- Open `Live Devices`, run `mqtt:sim:normal`, verify CPU/RAM/temp/mode/status changes.

2. Overview updates:
- Verify Active Devices, Avg CPU, Avg RAM, Global Accuracy, Global loss update.

3. Alerts & Logs feed:
- Run `mqtt:sim:alert`, verify Event Stream, Live Classifications, Help Requests all update continuously.

4. Validator behavior:
- Run with `--inject-invalid-every 10` and verify invalid payload messages appear in Event Stream while UI stays stable.

---

## Current split of responsibilities

MQTT-owned tabs/data:
- Overview (operational fields)
- Live Devices
- Alerts & Logs

gRPC-owned tabs/data:
- Federated Rounds
- Model Performance
- Network & Privacy
- Model Registry

---

## 4) Dashboard Database (Implemented)

The dashboard now persists MQTT data in SQLite (local file DB) using Node's `node:sqlite`.

DB file:
- `data/dashboard.sqlite` (auto-created at runtime)

Core server module:
- `lib/dashboard-db.ts`

Migration files:
- `db/migrations/*.sql`

Migration scripts:
- `npm run db:migrate`
- `npm run db:status`
- `npm run db:reset`

### Persistence flow

1. Browser receives MQTT message.
2. Frontend posts message to `POST /api/mqtt/ingest`.
3. API stores data in SQLite.
4. On page load, frontend fetches `GET /api/dashboard/bootstrap` to restore latest state/history.

### API endpoints

- `POST /api/mqtt/ingest`
  - input: `{ "topic": string, "payload": string, "timestamp"?: number }`
  - used by frontend to persist every incoming MQTT message

- `GET /api/dashboard/bootstrap`
  - returns latest device states, latest metrics, and recent stream data
  - used by frontend at startup to hydrate dashboard state from DB

### Tables

- `mqtt_messages`
- `device_status_latest`
- `device_status_history`
- `coordinator_metrics`
- `schema_migrations` (applied migration registry)

### Runtime requirement

- Node.js `>= 22.13` recommended (repo currently tested on Node `22.22.0`).

### Migration workflow

Apply all pending migrations:

```bash
npm run db:migrate
```

Check DB tables + applied migrations:

```bash
npm run db:status
```

Reset DB file and recreate from migrations:

```bash
npm run db:reset
npm run db:migrate
```

### Create a new migration

1. Create a new file in `db/migrations` with ordered prefix, e.g.:
   - `002_add_indexes.sql`
   - `003_add_new_table.sql`
2. Put SQL changes in that file (`CREATE TABLE`, `ALTER TABLE`, `CREATE INDEX`, etc.).
3. Run:

```bash
npm run db:migrate
```

4. Verify:

```bash
npm run db:status
```

Notes:
- Migrations are applied once and recorded in `schema_migrations`.
- Keep migration files immutable after they are applied.
- Add new migration files instead of editing old ones.

---

## 5) Broker Hardening (Critical for shared environments)

For local-only demo, anonymous can be acceptable temporarily.  
If the broker is shared or exposed, apply auth + ACL and disable anonymous clients.

### One-command setup script

Run:

```bash
bash scripts/mosquitto-hardening.sh
```

This script will:
- create `/etc/mosquitto/passwd` with two users:
  - `dashboard_ro` (read-only topics for dashboard)
  - `edge_rw` (write topics for devices/simulator)
- create `/etc/mosquitto/acl`
- create `/etc/mosquitto/conf.d/security-auth.conf` with:
  - `allow_anonymous false`
  - listener `1883` (mqtt)
  - listener `9001` (websockets)
- restart Mosquitto

Options:
- `--bind-all` to listen on `0.0.0.0` (shared network)
- `--topic-root`, `--dashboard-user`, `--publisher-user`
- `--yes` for non-interactive flow (with env passwords)

Example:

```bash
DASHBOARD_PASS='strong-dashboard-pass' PUBLISHER_PASS='strong-publisher-pass' \
bash scripts/mosquitto-hardening.sh --yes --bind-all
```

### Dashboard auth config after hardening

Set `.env.local`:

```env
NEXT_PUBLIC_MQTT_BROKER_URL=ws://localhost:9001
NEXT_PUBLIC_MQTT_TOPIC_ROOT=arduino
NEXT_PUBLIC_MQTT_USERNAME=dashboard_ro
NEXT_PUBLIC_MQTT_PASSWORD=<dashboard-pass>
```

Restart `npm run dev` after changing `.env.local`.

### Publisher/simulator auth after hardening

Manual publish:

```bash
mosquitto_pub -h 127.0.0.1 -p 1883 -u edge_rw -P '<publisher-pass>' -t arduino/UNO-Q1/status -m '{"cpu":80,"ram":66,"temp":"58C","heartbeat":"35 ms","mode":"Training","status":"Online"}'
```

Simulator:

```bash
MQTT_USERNAME=edge_rw MQTT_PASSWORD='<publisher-pass>' npm run mqtt:sim:alert
```

### Verify hardening

```bash
sudo systemctl status mosquitto --no-pager -l
sudo ss -ltnp | grep -E ':1883|:9001'
```

---

## 6) Handoff Checklist (MQTT -> gRPC Teammate)

Use this checklist before sharing the repo:

1. MQTT side validated:
- `Live Devices` updates from `status`
- `Overview` operational cards update from `status` + `metrics`
- `Alerts & Logs` updates from `event/logs/classification/help`

2. gRPC ownership clearly separated:
- `Federated Rounds`
- `Model Performance`
- `Network & Privacy`
- `Model Registry`

3. Simulator working:
- `npm run mqtt:sim:normal`
- `npm run mqtt:sim:alert`
- optional stress: `npm run mqtt:sim -- chaos --inject-invalid-every 10`

4. Topic contract shared:
- Share section **1) Topic Contract** from this document with the teammate.

5. Runtime mode agreed:
- Local demo mode (current): anonymous local broker
- Shared/network mode: apply section **5) Broker Hardening**

### Current local demo mode (no user/password)

Current intended setup for quick Arduino integration:
- broker at `127.0.0.1:1883` (mqtt) and `127.0.0.1:9001` (websockets)
- `allow_anonymous true`
- dashboard `.env.local` without username/password

`.env.local`:

```env
NEXT_PUBLIC_MQTT_BROKER_URL=ws://localhost:9001
NEXT_PUBLIC_MQTT_TOPIC_ROOT=arduino
```

### Message to send to gRPC teammate (copy/paste)

```text
MQTT side is ready and stable. Contract/topic root is in MQTT_README.md section 1.
UI sections owned by MQTT are: Overview (operational), Live Devices, Alerts & Logs.
gRPC-owned sections to wire are: Federated Rounds, Model Performance, Network & Privacy, Model Registry.
Current local mode is anonymous broker (no user/pass) for Arduino testing.
Use `npm run mqtt:sim:alert` to see the MQTT side alive while you wire gRPC data.
```
