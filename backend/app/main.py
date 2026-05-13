from fastapi import FastAPI, HTTPException

from app.config import settings
from app.db import ensure_schema
from app.grpc_server import GrpcServerRuntime
from app.mqtt_runtime import MqttIngestRuntime
from app.service import get_dashboard_bootstrap, get_fl_state

app = FastAPI(title="TrashUQ Backend", version="1.0.0")
grpc_runtime: GrpcServerRuntime | None = None
mqtt_runtime: MqttIngestRuntime | None = None


@app.on_event("startup")
def startup_event() -> None:
    global grpc_runtime, mqtt_runtime
    ensure_schema()
    grpc_runtime = GrpcServerRuntime(settings.grpc_host, settings.grpc_port)
    grpc_runtime.start()
    mqtt_runtime = MqttIngestRuntime()
    mqtt_runtime.start()


@app.on_event("shutdown")
def shutdown_event() -> None:
    global grpc_runtime, mqtt_runtime
    if mqtt_runtime is not None:
        mqtt_runtime.stop()
        mqtt_runtime = None
    if grpc_runtime is not None:
        grpc_runtime.stop()
        grpc_runtime = None


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


@app.get("/api/fl/state")
def fl_state() -> dict:
    return {"ok": True, "data": get_fl_state()}
