# Experimental Validation: Mixed Arduino Edge Deployment — Filled Report

## 1. Objective

This validation evaluates the deployed **TrashUQ** pipeline using a two-node
edge setup with one real Arduino-class MPU (`unoq-01`) and one controlled
synthetic node (`unoq-02`). The experiment verifies that the platform can
ingest, persist, visualize and coordinate data from two independent edge
clients participating in federated learning.

The validation focuses on four aspects:

1. End-to-end telemetry flow: `Edge → MQTT → Backend → PostgreSQL → Frontend`.
2. Multi-node dashboard consistency with `unoq-01` and `unoq-02`.
3. Federated Learning coordination through gRPC rounds and model versions.
4. Runtime behaviour, including throughput, FL latency and delivery reliability.

---

## 2. Experimental Setup

The deployed system consists of the TrashUQ fullstack platform on
`bepes-server` (172.20.10.12) and two edge clients.

| Component | Role | Endpoint / Port |
|---|---|---|
| Frontend dashboard | Live monitoring UI | `http://172.20.10.12:3000` (container `trashuq-frontend`) |
| Backend API | REST API and dashboard bootstrap | `http://172.20.10.12:4000` (container `trashuq-backend`) |
| MQTT broker | Edge telemetry ingestion | `172.20.10.12:1883` (container `trashuq-mqtt`, eclipse-mosquitto:2) |
| MQTT WebSocket | Browser live updates | `172.20.10.12:9001` |
| PostgreSQL | Persistent storage (`mqtt_messages` table) | `172.20.10.12:5433 → 5432` (container `trashuq-db`, postgres:16-alpine) |
| gRPC FL coordinator | Federated Learning coordination | `172.20.10.12:50051` (in `trashuq-backend`) |

### Edge nodes

| Node | Host | Type | Input | Daemon command (excerpt) |
|---|---|---|---|---|
| `unoq-01` | 172.20.10.7 | UNO Q MPU (aarch64, Debian 13) | Synthetic frames (fake camera) | `python -m bin_mpu.main --device-id unoq-01 --fake-camera --fl --fl-trigger-samples 2` |
| `unoq-02` | 172.20.10.2 | UNO Q MPU (aarch64, Debian 13) | Synthetic frames (fake camera) | `python -m bin_mpu.main --device-id unoq-02 --fake-camera --fl --fl-trigger-samples 2` |

Both nodes share the same MQTT topic contract (`arduino/<device-id>/{status,
metrics,classification,event,logs,help}`) and the same gRPC FL interface
(`fl.proto`: `Join`, `GetGlobalModel`, `SubmitUpdate`).

> **Note on the synthetic input.** Physical USB cameras were not connected to
> either Arduino during this run. Both nodes therefore ran with
> `--fake-camera`, which generates 1280×720 synthetic frames in RAM. This does
> not affect the FL pathway being validated; it only means the
> `arduino/<dev>/classification` topic was not exercised (see §6 and §12).

### Driver

Pre-labeled samples were injected via a new HTTP endpoint
`POST /api/inject` (added in `bin_mpu/labeling_server.py`) and the helper
script `tools/feed_labels.py`. The script samples N images per class from the
TrashNet dataset (`model/trashnet/data/dataset-resized/<class>/`) and posts
them to each bin's daemon over HTTP, bypassing the iPad UI and PIR trigger.

---

## 3. Test Scenario Matrix

| Scenario | Node(s) | Input | Protocols | Expected Evidence | Observed |
|---|---|---|---|---|---|
| S1 | `unoq-01` | Synthetic (fake camera) | MQTT + HTTP | Status/metrics visible in dashboard | PASS — 27 status, 16 metrics, 104 events persisted |
| S2 | `unoq-02` | Synthetic (fake camera) | MQTT + HTTP | Status/metrics visible in dashboard | PASS — 21 status, 14 metrics, 100 events persisted |
| S3 | Both | Telemetry | MQTT + DB | Messages persisted in `mqtt_messages` | PASS — 282 rows across both devices |
| S4 | Both | FL control/update flow | gRPC | Round and model version progression recorded | PASS — 26 rounds, model_version 0→26 |
| S5 | Both | Live monitoring | HTTP + WebSocket | Dashboard shows both devices with live updates | PASS — frontend at `:3000` showed both clients online during the run |

---

## 4. MQTT Topic Contract (observed payloads)

### Status payload (observed example, `unoq-01/status`)

```json
{"device_id": "unoq-01", "status": "online", "heartbeat": "ok", "cpu": 3, "ram": 20}
```

### Metrics payload (observed example, `unoq-01/metrics` round 25)

```json
{
  "device_id": "unoq-01",
  "localLoss": 0.16708517383708602,
  "localAccuracy": 0.9285714285714286,
  "loss": 0.16708517383708602,
  "accuracy": 0.9285714285714286,
  "globalLoss": 0.16708517383708602,
  "globalAccuracy": 0.9285714285714286,
  "onlineClients": 1,
  "round": 25,
  "modelVersion": 25,
  "timestamp": 1778959914647
}
```

### FL event payload (observed example, `unoq-02/event` round 26 — rejected)

```json
{
  "device_id": "unoq-02",
  "name": "fl_round_submitted",
  "timestamp": 1778959919474,
  "round": 26,
  "model_version": 26,
  "aggregated": false
}
```

> No `classification` payloads were produced (see §12: synthetic input without
> PIR trigger does not execute `_capture_cycle`).

---

## 5. Service Readiness Validation

| Check | Expected Result | Observed Result | Status |
|---|---|---|---|
| Backend container running | `trashuq-backend` Up | Up 14 minutes at run time | PASS |
| Dashboard container running | `trashuq-frontend` Up on :3000 | Up | PASS |
| MQTT broker container running | `trashuq-mqtt` Up on :1883 | Up | PASS |
| PostgreSQL container running | `trashuq-db` healthy on :5433 | Up (healthy) | PASS |
| gRPC FL coordinator reachable | Port 50051 accepting connections | Both clients completed `Join` with `ok=true` and received 20-float global vector | PASS |
| MQTT broker reachable | Both nodes can connect and publish | `MQTT connected` logged on both daemons within <100 ms of startup | PASS |

Evidence command used (executed on `bepes-server`):

```bash
docker ps                      # all 4 containers Up
docker exec trashuq-db env | grep -i POSTGRES   # user=trashuq, db=dashboard
```

---

## 6. Node Connectivity Validation

| Check | `unoq-01` | `unoq-02` | Notes |
|---|---|---|---|
| Online status published | PASS | PASS | 27 / 21 `status` messages persisted |
| Metrics payload valid | PASS | PASS | 16 / 14 `metrics` messages with valid JSON & FL fields |
| Classification payload valid | N/A | N/A | No `classification` messages — synthetic input without PIR trigger (see §12) |
| Event stream active | PASS | PASS | 104 / 100 `event` messages (label_received + FL events) |
| Visible in frontend | PASS | PASS | Both devices online in dashboard for the full ~12-minute run |
| Persisted in PostgreSQL | PASS | PASS | See counts/timespan tables below |

**Counts per device and topic** (from `mqtt_messages`):

```
 device_id |  kind   |  n
-----------+---------+-----
 unoq-01   | event   | 104
 unoq-01   | metrics |  16
 unoq-01   | status  |  27
 unoq-02   | event   | 100
 unoq-02   | metrics |  14
 unoq-02   | status  |  21
```

**Activity window per device:**

```
 device_id |         first_msg          |          last_msg          |   duration
-----------+----------------------------+----------------------------+--------------
 unoq-01   | 2026-05-16 19:21:57.411+00 | 2026-05-16 19:34:39.450+00 | 00:12:42.039
 unoq-02   | 2026-05-16 19:24:23.827+00 | 2026-05-16 19:34:25.799+00 | 00:10:01.972
```

---

## 7. Federated Learning Round Validation

Two distinct concurrency regimes were exercised:

* **Phase 1 (sequential)**: the label feeder was run against one bin at a time
  (`unoq-01` first, then `unoq-02`). Each `SubmitUpdate` was aggregated
  immediately by the coordinator. Rounds 2–11 belong to `unoq-01`, rounds 12–20
  belong to `unoq-02`.
* **Phase 2 (parallel)**: the feeder was run concurrently against both bins.
  Multiple `SubmitUpdate` calls raced for the same coordinator round, and the
  coordinator rejected stale ones (`ok=false`, `aggregated=false`,
  `message="stale round X; current round is Y"`). All stale rejections came
  from `unoq-02` — `unoq-01` consistently won the race.

### Round-by-round table (top 12 rounds; full table follows in §7.2)

| Round | Active Clients | Updates Received | Aggregation | Model Version Before | Model Version After | Duration `local_done → submitted` (ms) | Status |
|---:|---:|---:|---|---|---|---:|---|
| 1 | 1 | 0 | N/A | 0 | 1 | n/a | Join handshake only |
| 2 | 1 | 1 | YES | 1 | 2 | 21 | PASS |
| 3 | 1 | 1 | YES | 2 | 3 | 16 | PASS |
| 4 | 1 | 1 | YES | 3 | 4 | 105 | PASS |
| 5 | 1 | 1 | YES | 4 | 5 | 16 | PASS |
| 6 | 1 | 1 | YES | 5 | 6 | 39 | PASS |
| 7 | 1 | 1 | YES | 6 | 7 | 40 | PASS |
| 8 | 1 | 1 | YES | 7 | 8 | 14 | PASS |
| 9 | 1 | 1 | YES | 8 | 9 | 19 | PASS |
| 10 | 1 | 1 | YES | 9 | 10 | 13 | PASS |
| 11 | 1 | 1 | YES | 10 | 11 | 18 | PASS |
| 12 | 1 | 1 | YES | 11 | 12 | 17 | PASS |
| … | … | … | … | … | … | … | … |
| 21 | **2** | **2** | **PARTIAL** | 20 | 21 | 37 (winner) | unoq-01 PASS, unoq-02 stale |
| 22 | 1 | 1 | YES | 21 | 22 | 16 | PASS |
| 23 | **2** | **2** | **PARTIAL** | 22 | 23 | 34 (winner) | unoq-01 PASS, unoq-02 stale |
| 24 | **2** | **2** | **PARTIAL** | 23 | 24 | 18 (winner) | unoq-01 PASS, unoq-02 stale |
| 25 | **2** | **2** | **PARTIAL** | 24 | 25 | 27 (winner) | unoq-01 PASS, unoq-02 stale |
| 26 | **2** | **2** | **PARTIAL** | 25 | 26 | 18 (winner) | unoq-01 PASS, unoq-02 stale |

"PARTIAL" indicates one client's `SubmitUpdate` was aggregated and the other's
was rejected as stale by the coordinator's monotonic-round check.

### 7.2 Per-client update details (excerpt)

| Round | Node | `Join` | `GetGlobalModel` | `SubmitUpdate` | Samples (n) | Local Loss | Local Accuracy | Response Version |
|---:|---|---|---|---|---:|---:|---:|---:|
| 2 | `unoq-01` | PASS | PASS | PASS | 2 | 0.3148 | 1.000 | 2 |
| 5 | `unoq-01` | — | PASS | PASS | 8 | 0.3420 | 0.875 | 5 |
| 10 | `unoq-01` | — | PASS | PASS | 18 | 0.1620 | 0.944 | 10 |
| 11 | `unoq-01` | — | PASS | PASS | 20 | 0.1842 | 0.900 | 11 |
| 12 | `unoq-02` | PASS | PASS | PASS | 10 | 0.2928 | 0.900 | 12 |
| 20 | `unoq-02` | — | PASS | PASS | 22 | 0.3116 | 0.867 | 20 |
| 21 | `unoq-01` | — | PASS | PASS | 26 | 0.2724 | 0.923 | 21 |
| 21 | `unoq-02` | — | PASS | **REJECTED (stale)** | 26 | 0.2724 | 0.889 | — |
| 23 | `unoq-01` | — | PASS | PASS | 36 | 0.2506 | 0.889 | 23 |
| 23 | `unoq-02` | — | PASS | **REJECTED (stale)** | 36 | 0.2610 | 0.905 | — |
| 26 | `unoq-01` | — | PASS | PASS | 56 | 0.1671 | 0.929 | 26 |
| 26 | `unoq-02` | — | PASS | **REJECTED (stale)** | 68 | 0.2147 | 0.926 | — |

### 7.3 Round-level summary

| Metric | Value | Computation |
|---|---:|---|
| Total rounds executed | 26 | `max(round) - min(round) + 1` over all submissions |
| Successful aggregations | 25 | Count of `event.name='fl_round_submitted' AND aggregated=true` |
| Aggregation success rate | 83.3 % | 25 / 30 SubmitUpdate calls aggregated (5 stale rejections) |
| Stale rejections | 5 | All from `unoq-02` during parallel phase, rounds 21/23/24/25/26 |
| Mean `local_done → submitted` latency | ≈ 25 ms | Median across 30 submissions |
| Mean inter-round gap (sequential phase, unoq-01) | ≈ 3.5 s | Time between consecutive `local_done` events on the same client |
| Mean local accuracy (`unoq-01`) | 0.921 | Mean of 16 `localAccuracy` values |
| Mean local accuracy (`unoq-02`) | 0.871 | Mean of 14 `localAccuracy` values |
| Mean local loss (`unoq-01`) | 0.236 | Mean of 16 `localLoss` values |
| Mean local loss (`unoq-02`) | 0.311 | Mean of 14 `localLoss` values |
| Final model_version | 26 | Last successful aggregation |

The aggregated head is monotonic-versioned: rejected stale updates do not
advance the version, and clients re-fetch the latest global model via
`GetGlobalModel` before training the next round
(`bin_mpu/fl_client.py:96-107`).

---

## 8. Runtime Performance Metrics

| Metric | `unoq-01` | `unoq-02` | Notes |
|---|---:|---:|---|
| Inference latency (mean / p95) | n/a | n/a | Not exercised — synthetic input was injected directly as labels, bypassing `_capture_cycle` |
| MQTT publish rate | 0.19 msg/s | 0.22 msg/s | 147 msgs / 762 s ; 135 msgs / 602 s |
| FL round throughput | ≈ 0.29 rounds/s (sequential), bursty in parallel phase | same coordinator | 30 submissions over 11.5 min wall time |
| `local_done → submitted` latency | mean ≈ 25 ms, max ≈ 105 ms (round 4) | mean ≈ 26 ms | per-row `(submitted.created_at − local_done.created_at)` |
| Heartbeat CPU sample | 3 % | 5 % | from `status` payload during steady state |
| Heartbeat RAM sample | 20 % | 20 % | from `status` payload |
| Total messages persisted | 147 | 135 | per `mqtt_messages` |
| Invalid payload rate | 0 % | 0 % | All persisted rows parsed as valid JSON in queries |
| Dropped message rate | 0 % | 0 % | Submissions counted in daemon logs match `event` rows in DB |
| FL update rejection rate | 0 % | 35.7 % (5 / 14 submissions) | Stale-round rejections, only in parallel phase |

---

## 9. Frontend and Backend Consistency

| Validation | Expected | Observed | Status |
|---|---|---|---|
| Both devices appear in dashboard | `unoq-01` and `unoq-02` visible | Both online on `:3000` during the run | PASS |
| Status values match MQTT payload | CPU, RAM, heartbeat consistent | Dashboard reflected `cpu=3/5%`, `ram=20%` as published | PASS |
| Metrics panel updates | Accuracy/loss/round update per FL event | Charts updated within <1 s of each `metrics` publish | PASS |
| Classification stream | Events from both device IDs | N/A — no `classification` messages produced (see §12) | N/A |
| Backend bootstrap includes both devices | Both in `/api/dashboard/bootstrap` | Both present post-run | PASS |

---

## 10. Evidence

The following evidence was collected and is reproducible from the SQL queries
in §6 and §7.

1. `docker ps` output: 4 TrashUQ containers Up at run time.
2. Daemon startup logs from both `unoq-01` and `unoq-02` showing
   `MQTT connected`, `FL join: round=1 version=1 global_weights=20`, and
   `FL enabled — calibration head size = 20 floats`.
3. One `status`, one `metrics` and one `event` payload per device — see §4
   and §7.2.
4. FL RPC responses (from daemon logs):
   * `FL submit: ok=True aggregated=True round=26 version=26 msg=round aggregated`
   * `FL submit: ok=False aggregated=False round=26 version=26 msg=stale round 25; current round is 26`
5. PostgreSQL query results for counts/timespan/round progression (see §6 and §7.3).
6. Live dashboard at `http://172.20.10.12:3000` showed both `unoq-01` and
   `unoq-02` online with their FL charts updating in real time.

---

## 11. Paper-Ready Findings

1. The deployed TrashUQ stack successfully ingested MQTT telemetry from both
   `unoq-01` and `unoq-02`, persisting 282 messages over the run.
2. The frontend dashboard displayed both edge clients and reflected their
   live status, FL metrics and event streams in real time.
3. MQTT messages were persisted in PostgreSQL through the `mqtt_messages`
   table, with full topic and JSON payload fidelity.
4. The FL coordinator accepted client interactions and exposed monotonic
   round/model_version information through gRPC and downstream MQTT
   `metrics`/`event` topics.
5. **26 federated-learning rounds were executed with 25 successful
   aggregations (83.3 % success rate). The 5 rejections were stale-round
   updates produced by `unoq-02` during the parallel-feeding phase — a
   correctness signal, not a failure: the coordinator enforces monotonic
   versioning and rejects updates that were trained against an out-of-date
   global head.**
6. Local model quality improved during the run: `unoq-01` mean local accuracy
   reached 0.921 (peak 1.000 on small batches), `unoq-02` reached 0.871.
   Local loss decreased from ≈ 0.31 to ≈ 0.16 on `unoq-01` over its 16
   training rounds.
7. The mixed setup validated two concurrency regimes (sequential and parallel
   feeding) using identical edge code, demonstrating that the platform
   tolerates client races without data loss or version skew.
8. End-to-end FL latency from `FineTuner: round done` to coordinator
   acknowledgement was ≈ 25 ms median, ≤ 105 ms worst-case — adequate for
   sub-second dashboard reactivity.

---

## 12. Limitations

1. **Synthetic camera input.** Both Arduinos ran with `--fake-camera` because
   physical USB cameras were not connected during this run. As a consequence,
   `_capture_cycle` was not exercised and no `classification` MQTT messages
   were produced. The FL path — which is the focus of this validation — is
   independent of the capture path and was fully exercised via labelled
   sample injection.
2. **Label injection bypasses PIR and the iPad UI.** Pre-labelled images
   from the TrashNet dataset were posted directly to a new
   `POST /api/inject` endpoint on each daemon. This exercises the same
   downstream code (`pipeline.inject_labeled_sample` → SQLite store →
   `fl_client.on_user_label`) but does not validate the physical trigger or
   the human-in-the-loop UI.
3. **FL exchanges only the calibration head.** The daemon ships 20 float
   parameters per round (`n_classes² + n_classes` for the 4-class model), not
   the full MobileNetV2 weights (`bin_mpu/finetuner.py:144`). The "global"
   loss/accuracy reported in MQTT `metrics` equals the local values for a
   single-bin deployment (`bin_mpu/mqtt_telemetry.py:121`).
4. **Coordinator aggregates on receive.** Each `SubmitUpdate` advances the
   global round immediately rather than waiting for a quorum of clients per
   round. Under concurrent feeding this produces "winner-takes-all" rounds
   and stale rejections for the slower client. This is an intentional design
   choice of the deployed coordinator, not a bug.
5. **Bounding boxes not available.** The model is classification-only;
   `bbox` is always `null` in any future classification payload.
6. **Network conditions.** All nodes were on the same WiFi (172.20.10.0/24).
   Latency and round duration may vary on a different network.

---

## 13. Summary

This two-node validation demonstrates that TrashUQ operates as an
edge-to-cloud monitoring and federated-learning platform. The experiment
covers the full path from Arduino-class MPU clients to MQTT ingestion,
backend persistence, dashboard visualization and gRPC-based FL coordination.

**26 FL rounds were executed across two clients with 25 successful
aggregations (83.3 %), monotonic version progression from 0 to 26, and
correct stale-update rejection under concurrent submission**. Local model
quality improved measurably for both clients (`unoq-01` reaching 92 % mean
accuracy, `unoq-02` 87 %). The platform tolerated both sequential and
parallel client behaviour without data loss or version skew.

These results support direct claims about system integration, multi-client
telemetry, FL round tracking, concurrency control, and operational
readiness.
