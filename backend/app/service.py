import json
import time
from typing import Any

from sqlalchemy import text

from app.db import engine
from app.fl_coordinator import coordinator


def clamp_percent(value: float) -> int:
    if value < 0:
        return 0
    if value > 100:
        return 100
    return round(value)


def parse_numeric(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def parse_json(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def get_kind(topic: str) -> str:
    lower = topic.lower()
    if lower.endswith("/status"):
        return "status"
    if lower.endswith("/metrics"):
        return "metrics"
    if lower.endswith("/event"):
        return "event"
    if lower.endswith("/classification"):
        return "classification"
    if lower.endswith("/help"):
        return "help"
    if lower.endswith("/logs"):
        return "logs"
    return "other"


def get_device_id(topic: str) -> str | None:
    parts = topic.split("/")
    if len(parts) < 3:
        return None
    return parts[-2] or None


def parse_status_patch(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    patch: dict[str, Any] = {}

    cpu = parse_numeric(payload.get("cpu"))
    ram = parse_numeric(payload.get("ram"))
    if cpu is not None:
        patch["cpu"] = clamp_percent(cpu)
    if ram is not None:
        patch["ram"] = clamp_percent(ram)

    for key in ["temp", "heartbeat", "mode", "status"]:
        value = payload.get(key)
        if isinstance(value, str):
            patch[key] = value

    return patch


def parse_metrics_patch(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    patch: dict[str, Any] = {}

    mapping = {
        "global_accuracy": ["globalAccuracy", "global_accuracy", "accuracy"],
        "global_loss": ["globalLoss", "global_loss", "loss"],
        "avg_cpu": ["avgCpu", "avg_cpu"],
        "avg_ram": ["avgRam", "avg_ram"],
        "online_clients": ["onlineClients", "online_clients"],
    }

    for target, keys in mapping.items():
        number = None
        for key in keys:
            number = parse_numeric(payload.get(key))
            if number is not None:
                break
        if number is not None:
            patch[target] = max(0, round(number)) if target == "online_clients" else number

    return patch


def ingest_mqtt_message(topic: str, payload: str, timestamp: int | None = None) -> None:
    kind = get_kind(topic)
    device_id = get_device_id(topic)
    ts = int(timestamp) if isinstance(timestamp, int) else int(time.time() * 1000)
    parsed = parse_json(payload)
    payload_json = parsed if isinstance(parsed, dict) else None

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO mqtt_messages(topic, kind, device_id, payload_text, payload_json, recorded_at)
                VALUES (:topic, :kind, :device_id, :payload_text, CAST(:payload_json AS JSONB), :recorded_at)
                """
            ),
            {
                "topic": topic,
                "kind": kind,
                "device_id": device_id,
                "payload_text": payload,
                "payload_json": json.dumps(payload_json) if payload_json is not None else None,
                "recorded_at": ts,
            },
        )

        if kind == "status" and device_id:
            patch = parse_status_patch(parsed)
            if patch:
                conn.execute(
                    text(
                        """
                        INSERT INTO device_status_latest(device_id, cpu, ram, temp, heartbeat, mode, status, updated_at)
                        VALUES (:device_id, :cpu, :ram, :temp, :heartbeat, :mode, :status, :updated_at)
                        ON CONFLICT(device_id) DO UPDATE SET
                          cpu = COALESCE(EXCLUDED.cpu, device_status_latest.cpu),
                          ram = COALESCE(EXCLUDED.ram, device_status_latest.ram),
                          temp = COALESCE(EXCLUDED.temp, device_status_latest.temp),
                          heartbeat = COALESCE(EXCLUDED.heartbeat, device_status_latest.heartbeat),
                          mode = COALESCE(EXCLUDED.mode, device_status_latest.mode),
                          status = COALESCE(EXCLUDED.status, device_status_latest.status),
                          updated_at = EXCLUDED.updated_at
                        """
                    ),
                    {
                        "device_id": device_id,
                        "cpu": patch.get("cpu"),
                        "ram": patch.get("ram"),
                        "temp": patch.get("temp"),
                        "heartbeat": patch.get("heartbeat"),
                        "mode": patch.get("mode"),
                        "status": patch.get("status"),
                        "updated_at": ts,
                    },
                )

                conn.execute(
                    text(
                        """
                        INSERT INTO device_status_history(device_id, cpu, ram, temp, heartbeat, mode, status, recorded_at)
                        VALUES (:device_id, :cpu, :ram, :temp, :heartbeat, :mode, :status, :recorded_at)
                        """
                    ),
                    {
                        "device_id": device_id,
                        "cpu": patch.get("cpu"),
                        "ram": patch.get("ram"),
                        "temp": patch.get("temp"),
                        "heartbeat": patch.get("heartbeat"),
                        "mode": patch.get("mode"),
                        "status": patch.get("status"),
                        "recorded_at": ts,
                    },
                )

        if kind == "metrics":
            patch = parse_metrics_patch(parsed)
            if patch:
                conn.execute(
                    text(
                        """
                        INSERT INTO coordinator_metrics(global_accuracy, global_loss, avg_cpu, avg_ram, online_clients, recorded_at)
                        VALUES (:global_accuracy, :global_loss, :avg_cpu, :avg_ram, :online_clients, :recorded_at)
                        """
                    ),
                    {
                        "global_accuracy": patch.get("global_accuracy"),
                        "global_loss": patch.get("global_loss"),
                        "avg_cpu": patch.get("avg_cpu"),
                        "avg_ram": patch.get("avg_ram"),
                        "online_clients": patch.get("online_clients"),
                        "recorded_at": ts,
                    },
                )


def get_recent_stream_by_kinds(kinds: list[str], limit: int = 16) -> list[str]:
    query = text(
        """
        SELECT payload_text
        FROM mqtt_messages
        WHERE kind = ANY(:kinds)
        ORDER BY recorded_at DESC, id DESC
        LIMIT :limit
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(query, {"kinds": kinds, "limit": limit}).fetchall()
    return [row[0] for row in rows]


def get_dashboard_bootstrap() -> dict[str, Any]:
    with engine.connect() as conn:
        devices_rows = conn.execute(
            text(
                """
                SELECT device_id, cpu, ram, temp, heartbeat, mode, status
                FROM device_status_latest
                ORDER BY device_id ASC
                """
            )
        ).fetchall()

        metrics_row = conn.execute(
            text(
                """
                SELECT global_accuracy, global_loss
                FROM coordinator_metrics
                ORDER BY recorded_at DESC, id DESC
                LIMIT 1
                """
            )
        ).fetchone()

    event_stream = get_recent_stream_by_kinds(["event", "logs"], 16)
    classifications = get_recent_stream_by_kinds(["classification"], 16)
    help_requests = get_recent_stream_by_kinds(["help"], 16)

    devices = [
        {
            "id": row[0],
            "cpu": row[1] if row[1] is not None else 0,
            "ram": row[2] if row[2] is not None else 0,
            "temp": row[3] if row[3] is not None else "-",
            "heartbeat": row[4] if row[4] is not None else "No signal",
            "mode": row[5] if row[5] is not None else "Unknown",
            "status": row[6] if row[6] is not None else "Unknown",
        }
        for row in devices_rows
    ]

    return {
        "devices": devices,
        "metrics": {
            "globalAccuracy": metrics_row[0] if metrics_row else None,
            "globalLoss": metrics_row[1] if metrics_row else None,
        },
        "federated": coordinator.snapshot(),
        "eventStream": event_stream,
        "classifications": classifications,
        "helpRequests": help_requests,
    }
