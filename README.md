# TrashUQ

## Run all services with Podman

1. Copy env file:

```bash
cp backend/.env.example backend/.env
```

2. Start stack:

```bash
podman compose up --build
```

Services:
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:4000`
- Backend gRPC (FL): `localhost:50051`
- PostgreSQL: `localhost:5432`
- MQTT broker: `localhost:1883`
- MQTT WebSocket: `ws://localhost:9001/mqtt`

## MQTT topics

Topic root is `arduino` by default (`NEXT_PUBLIC_MQTT_TOPIC_ROOT`).

Expected topics:
- `arduino/<device-id>/status`
- `arduino/<device-id>/metrics`
- `arduino/<device-id>/event`
- `arduino/<device-id>/classification`
- `arduino/<device-id>/help`
- `arduino/<device-id>/logs`

Backend API endpoints:
- `GET /health`
- `GET /api/dashboard/bootstrap`

## Runtime data flow

- Arduino clients publish MQTT directly to Mosquitto.
- Backend subscribes to broker topics (`arduino/+/#`) and persists messages to PostgreSQL.
- Frontend loads initial state from `GET /api/dashboard/bootstrap` and listens to MQTT for live updates.
- Federated Learning coordination runs on backend gRPC (`:50051`).

## Federated Learning over gRPC

Proto file: `backend/app/fl.proto`

RPC methods:
- `Join`
- `GetGlobalModel`
- `SubmitUpdate`
