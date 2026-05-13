# Real Edge Dashboard Verification

This flow verifies real data moving through:

```text
edge simulator -> MQTT -> backend subscriber -> PostgreSQL -> backend bootstrap -> frontend dashboard
```

## Start Server

```sh
cd ~/Documents/TrashNet/TrashUQ
docker compose down
docker compose up --build
```

## Verify Backend

```sh
curl http://localhost:4000/health
curl http://localhost:4000/api/dashboard/bootstrap
curl http://localhost:4000/api/fl/state
```

## Verify Frontend Proxy

```sh
curl http://localhost:3000/api/dashboard/bootstrap
docker compose exec frontend sh -lc 'wget -qO- http://backend:4000/health || curl -s http://backend:4000/health'
docker compose logs frontend | grep "127.0.0.1:4000"
```

Expected: the first two commands work, and the grep command shows no new proxy errors.

## Verify MQTT Raw

```sh
cd ~/Documents/TrashNet/TrashUQ
docker compose exec mqtt mosquitto_sub -h localhost -p 1883 -t 'arduino/+/+' -v
```

In another terminal:

```sh
cd ~/Documents/TrashNet/edge
uv run python scripts/test_mqtt_publish.py
```

## Verify PostgreSQL Persistence

```sh
cd ~/Documents/TrashNet/TrashUQ
docker compose exec db psql -U trashuq -d dashboard -c "select topic, payload, created_at from mqtt_messages order by created_at desc limit 20;"
```

## Run Live Simulator

```sh
cd ~/Documents/TrashNet/edge
uv run python -m app.edge_simulator
```

## Verify gRPC

```sh
cd ~/Documents/TrashNet/edge
uv run python scripts/generate_grpc_client.py
uv run python scripts/test_fl_grpc.py
```

Expected: `Join` and `GetGlobalModel` succeed. `SubmitUpdate` is skipped unless real local training/update data exists.

## Open Dashboard

```text
http://localhost:3000
```

Expected dashboard behavior:

- Event Stream shows real MQTT events/logs.
- Live Client Summary shows real `unoq-01` status, CPU, RAM, latest classification, confidence, heartbeat, and last update.
- Active Devices, Avg CPU/RAM, Last MQTT, Global Accuracy/Loss, and Samples Trained update from backend/MQTT data.
- Local Training Loss and Client Drift charts use real MQTT metric history.
- Unsupported FL/model registry/data quality sections show waiting states instead of fake data.

