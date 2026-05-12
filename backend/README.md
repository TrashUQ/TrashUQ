# Backend (FastAPI + PostgreSQL)

FastAPI service for dashboard bootstrap, gRPC FL coordinator and direct MQTT broker ingestion.

Endpoints:
- `GET /health`
- `GET /api/dashboard/bootstrap`

gRPC service:
- `FederatedLearningService` on port `50051`
- RPCs: `Join`, `GetGlobalModel`, `SubmitUpdate`

Federated Learning env vars:
- `FL_MODEL_SIZE` (default: `16`)
- `FL_MIN_CLIENTS_PER_ROUND` (default: `2`)
- `GRPC_HOST` (default: `0.0.0.0`)
- `GRPC_PORT` (default: `50051`)

This service is intended to run from the root stack compose file.

MQTT ingestion:
- Backend subscribes directly to broker topic `${MQTT_TOPIC_ROOT}/+/#`
- No frontend-to-backend MQTT ingest endpoint is required
