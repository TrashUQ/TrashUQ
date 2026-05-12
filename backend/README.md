# Backend (FastAPI + PostgreSQL)

FastAPI service for dashboard bootstrap and MQTT ingestion.

Endpoints:
- `GET /health`
- `GET /api/dashboard/bootstrap`
- `POST /api/mqtt/ingest`

gRPC service:
- `FederatedLearningService` on port `50051`
- RPCs: `Join`, `GetGlobalModel`, `SubmitUpdate`

Federated Learning env vars:
- `FL_MODEL_SIZE` (default: `16`)
- `FL_MIN_CLIENTS_PER_ROUND` (default: `2`)
- `GRPC_HOST` (default: `0.0.0.0`)
- `GRPC_PORT` (default: `50051`)

This service is intended to run from the root stack compose file.
