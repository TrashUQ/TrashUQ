# Experimental Validation: Mixed Arduino Edge Deployment

## 1. Objective

This validation evaluates the deployed **TrashUQ** pipeline using a mixed two-node edge setup. The experiment combines one real Arduino camera node and one controlled mock/synthetic node to verify that the platform can ingest, persist, visualize and coordinate data from heterogeneous edge clients.

The validation focuses on four aspects:

1. End-to-end telemetry flow: `Edge → MQTT → Backend → PostgreSQL → Frontend`.
2. Multi-node dashboard consistency with `unoq-01` and `unoq-02`.
3. Federated Learning coordination through gRPC rounds and model versions.
4. Runtime performance, including latency, throughput, confidence and delivery reliability.

---

## 2. Experimental Setup

The deployed system consists of the TrashUQ fullstack platform and two Arduino/edge clients.

| Component | Role | Endpoint / Port |
|---|---|---|
| Frontend dashboard | Live monitoring UI | `http://<host>:3000` |
| Backend API | REST API and dashboard bootstrap | `http://<host>:4000` |
| MQTT broker | Edge telemetry ingestion | `<host>:1883` |
| MQTT WebSocket | Browser live updates | `<host>:9001` |
| PostgreSQL | Persistent storage | `<host>:5432` |
| gRPC FL coordinator | Federated Learning coordination | `<host>:50051` |

### Edge nodes

| Node | Type | Input | Purpose |
|---|---|---|---|
| `unoq-01` | Real Arduino camera node | Camera frames | Validate real capture, classification and telemetry publishing |
| `unoq-02` | Mock/synthetic node | Synthetic or preloaded samples | Validate multi-client behaviour and controlled input flow |

Both nodes use the same MQTT topic contract and the same FL coordination interface.

---

## 3. Test Scenario Matrix

| Scenario | Node(s) | Input | Protocols | Expected Evidence |
|---|---|---|---|---|
| S1 | `unoq-01` | Real camera | MQTT + HTTP | Camera classifications visible in dashboard |
| S2 | `unoq-02` | Mock/synthetic | MQTT + HTTP | Synthetic classifications visible in dashboard |
| S3 | Both | Telemetry | MQTT + DB | Messages persisted in `mqtt_messages` |
| S4 | Both | FL control/update flow | gRPC | Round and model version progression recorded |
| S5 | Both | Live monitoring | HTTP + WebSocket | Dashboard shows both devices and live updates |

---

## 4. MQTT Topic Contract

Each node publishes telemetry under the `arduino` topic root:

```text
arduino/<device-id>/status
arduino/<device-id>/metrics
arduino/<device-id>/classification
arduino/<device-id>/event
arduino/<device-id>/logs
arduino/<device-id>/help
```

The most relevant payloads for the dashboard are shown below.

### Status payload

```json
{
  "device_id": "unoq-01",
  "online": true,
  "status": "online",
  "state": "running",
  "mode": "real_camera",
  "cpu": 54.2,
  "ram": 41.8,
  "heartbeat": "2026-05-14T10:20:00Z",
  "model_version": "v1",
  "ts": "2026-05-14T10:20:00Z"
}
```

### Metrics payload

```json
{
  "device_id": "unoq-01",
  "round": 3,
  "localLoss": 0.42,
  "localAccuracy": 0.86,
  "globalLoss": 0.38,
  "globalAccuracy": 0.89,
  "samplesTrained": 128,
  "fps": 9.7,
  "inference_ms": 92.4,
  "drift": 1.8,
  "ts": "2026-05-14T10:20:00Z"
}
```

### Classification payload

```json
{
  "device_id": "unoq-01",
  "label": "plastic",
  "confidence": 0.91,
  "bbox": null,
  "source": "real_model",
  "model_version": "v1",
  "ts": "2026-05-14T10:20:00Z"
}
```

---

## 5. Service Readiness Validation

| Check | Expected Result | Observed Result | Status |
|---|---|---|---|
| Backend health endpoint | `GET /health` returns healthy status | `...` | `PASS/FAIL` |
| Dashboard bootstrap endpoint | `/api/dashboard/bootstrap` returns valid JSON | `...` | `PASS/FAIL` |
| Frontend dashboard | Dashboard loads without critical errors | `...` | `PASS/FAIL` |
| MQTT broker | Both nodes can connect and publish | `...` | `PASS/FAIL` |
| gRPC coordinator | Both nodes can reach FL coordinator | `...` | `PASS/FAIL` |

Evidence commands:

```bash
curl http://<host>:4000/health
curl http://<host>:4000/api/dashboard/bootstrap
```

```bash
docker compose exec mqtt mosquitto_sub -h localhost -p 1883 -t 'arduino/+/+' -v
```

---

## 6. Node Connectivity Validation

| Check | `unoq-01` Camera Node | `unoq-02` Mock Node | Notes |
|---|---|---|---|
| Online status published | `PASS/FAIL` | `PASS/FAIL` | `...` |
| Metrics payload valid | `PASS/FAIL` | `PASS/FAIL` | `...` |
| Classification payload valid | `PASS/FAIL` | `PASS/FAIL` | `...` |
| Event/log stream active | `PASS/FAIL` | `PASS/FAIL` | `...` |
| Visible in frontend | `PASS/FAIL` | `PASS/FAIL` | `...` |
| Persisted in PostgreSQL | `PASS/FAIL` | `PASS/FAIL` | `...` |

Database verification:

```bash
docker compose exec db psql -U trashuq -d dashboard -c \
"select topic, payload, created_at from mqtt_messages order by created_at desc limit 20;"
```

---

## 7. Federated Learning Round Validation

The FL experiment records the interaction between edge clients and the gRPC coordinator. Each round tracks client participation, update submission, aggregation and model version progression.

| Round | Active Clients | Joined Clients | Updates Received | Aggregation | Model Version Before | Model Version After | Duration (s) | Status |
|---:|---:|---:|---:|---|---|---|---:|---|
| 1 | `...` | `...` | `...` | `YES/NO` | `...` | `...` | `...` | `PASS/FAIL` |
| 2 | `...` | `...` | `...` | `YES/NO` | `...` | `...` | `...` | `PASS/FAIL` |
| 3 | `...` | `...` | `...` | `YES/NO` | `...` | `...` | `...` | `PASS/FAIL` |
| 4 | `...` | `...` | `...` | `YES/NO` | `...` | `...` | `...` | `PASS/FAIL` |
| 5 | `...` | `...` | `...` | `YES/NO` | `...` | `...` | `...` | `PASS/FAIL` |

### Per-client update details

| Round | Node | `Join` | `GetGlobalModel` | `SubmitUpdate` | Samples | Local Loss | Local Accuracy | Response Version |
|---:|---|---|---|---|---:|---:|---:|---|
| 1 | `unoq-01` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `...` | `...` | `...` | `...` |
| 1 | `unoq-02` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `...` | `...` | `...` | `...` |
| 2 | `unoq-01` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `...` | `...` | `...` | `...` |
| 2 | `unoq-02` | `PASS/FAIL` | `PASS/FAIL` | `PASS/FAIL` | `...` | `...` | `...` | `...` |

### Round-level summary

| Metric | Value | Computation |
|---|---:|---|
| Total rounds executed | `...` | `last_round - first_round + 1` |
| Successful aggregations | `...` | Count of successful aggregation rounds |
| Aggregation success rate (%) | `...` | `(successful / total_rounds) * 100` |
| Mean round duration (s) | `...` | Mean of round durations |
| Mean participating clients per round | `...` | Mean active clients |
| Mean updates per round | `...` | Mean received updates |
| Mean local accuracy (`unoq-01`) | `...` | Mean local accuracy for camera node |
| Mean local accuracy (`unoq-02`) | `...` | Mean local accuracy for mock node |

---

## 8. Runtime Performance Metrics

| Metric | `unoq-01` Camera | `unoq-02` Mock | Notes |
|---|---:|---:|---|
| Mean inference latency (ms) | `...` | `...` | `...` |
| P95 inference latency (ms) | `...` | `...` | `...` |
| Throughput (FPS or msg/s) | `...` | `...` | `...` |
| Mean MQTT publish delay (ms) | `...` | `...` | `...` |
| Dashboard refresh lag (s) | `...` | `...` | `...` |
| Total messages/samples | `...` | `...` | `...` |
| Mean confidence | `...` | `...` | `...` |
| Invalid payload rate (%) | `...` | `...` | `...` |
| Dropped message rate (%) | `...` | `...` | `...` |

---

## 9. Frontend and Backend Consistency

| Validation | Expected | Observed | Status |
|---|---|---|---|
| Both devices appear in dashboard | `unoq-01` and `unoq-02` visible | `...` | `PASS/FAIL` |
| Status values match MQTT payload | CPU, RAM and heartbeat consistent | `...` | `PASS/FAIL` |
| Metrics panel updates | Accuracy, loss and round values update | `...` | `PASS/FAIL` |
| Classification stream receives both nodes | Events from both device IDs | `...` | `PASS/FAIL` |
| Backend bootstrap includes both devices | Both devices present in `/bootstrap` | `...` | `PASS/FAIL` |

---

## 10. Evidence Snippets

The following evidence should be collected and stored with the experiment results:

1. `GET /health` output.
2. `GET /api/dashboard/bootstrap` output snippet with both devices.
3. One `classification` payload from each node.
4. One `metrics` payload from each node.
5. At least one FL RPC response per node with round/model version.
6. One screenshot or text evidence showing both devices in the frontend dashboard.
7. One PostgreSQL query result showing recent MQTT messages from both nodes.

```text
# Paste raw logs, MQTT payloads, curl outputs and DB query results here.
```

---

## 11. Paper-Ready Findings

After filling the tables, summarize the validation using 5–8 concise findings:

- The deployed TrashUQ stack successfully ingested MQTT telemetry from both `unoq-01` and `unoq-02`.
- The frontend dashboard displayed both edge clients and reflected their live status, metrics and classification streams.
- MQTT messages were persisted in PostgreSQL through the `mqtt_messages` table.
- The FL coordinator accepted client interactions and exposed round/model version information.
- The mixed setup validated both real camera-based inference and controlled synthetic input under the same communication contract.
- Runtime performance was measured through latency, throughput, confidence and delivery reliability.
- Backend bootstrap data and frontend state remained consistent during the experiment.
- `...`

---

## 12. Limitations

The following limitations should be reported if they apply to the final execution:

- The mock node uses controlled synthetic/preloaded input and does not represent real camera variability.
- Camera-based results depend on lighting, camera position and object visibility.
- Network latency may vary depending on deployment conditions.
- If the model is classification-only, bounding boxes are not available and should be reported as `bbox: null`.
- Performance values are specific to the tested hardware and deployment environment.
- `...`

---

## 13. Summary

This mixed two-node validation demonstrates that TrashUQ can operate as a real edge-to-cloud monitoring platform. The experiment validates the complete path from Arduino/edge clients to MQTT ingestion, backend persistence, dashboard visualization and FL coordination. By combining one real camera node with one controlled mock node, the test confirms that the platform supports heterogeneous edge participation while maintaining a unified data contract and a consistent dashboard view.

The results from this validation can be used directly in the short paper to support claims about system integration, multi-client telemetry, FL round tracking and operational readiness.
