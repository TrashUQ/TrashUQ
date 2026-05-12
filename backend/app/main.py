from fastapi import FastAPI, HTTPException

from app.db import ensure_schema
from app.schemas import IngestMqttRequest
from app.service import get_dashboard_bootstrap, ingest_mqtt_message

app = FastAPI(title="FederatedCans Backend", version="1.0.0")


@app.on_event("startup")
def startup_event() -> None:
    ensure_schema()


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/api/dashboard/bootstrap")
def dashboard_bootstrap() -> dict:
    try:
        return {"ok": True, "data": get_dashboard_bootstrap()}
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={"ok": False, "error": "failed to load dashboard bootstrap", "details": str(error)},
        )


@app.post("/api/mqtt/ingest")
def mqtt_ingest(body: IngestMqttRequest) -> dict[str, bool]:
    if not body.topic or not body.payload:
        raise HTTPException(status_code=400, detail={"ok": False, "error": "topic and payload are required"})

    try:
        ingest_mqtt_message(topic=body.topic, payload=body.payload, timestamp=body.timestamp)
        return {"ok": True}
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={"ok": False, "error": "failed to ingest mqtt message", "details": str(error)},
        )
