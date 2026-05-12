# TrashUQ

## Run all services with Podman

1. Copy env file:

```bash
cp .env.example .env
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
- `POST /api/mqtt/ingest`

## Federated Learning over gRPC

Proto file: `backend/app/fl.proto`

RPC methods:
- `Join`
- `GetGlobalModel`
- `SubmitUpdate`
