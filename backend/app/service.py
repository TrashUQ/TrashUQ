import json
import time
from datetime import UTC, datetime
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


def normalize_accuracy(value: Any) -> float | None:
    number = parse_numeric(value)
    if number is None:
        return None
    return number * 100 if 0 <= number <= 1 else number


def first_numeric(payload: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        number = parse_numeric(payload.get(key))
        if number is not None:
            return number
    return None


def first_string(payload: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def recorded_at_iso(recorded_at: int) -> str:
    return datetime.fromtimestamp(recorded_at / 1000, tz=UTC).isoformat().replace("+00:00", "Z")


def normalize_status_payload(device_id: str, payload: Any, recorded_at: int) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    cpu = first_numeric(payload, ["cpu", "cpu_percent", "avgCpu", "avg_cpu"])
    ram = first_numeric(payload, ["ram", "ram_percent", "avgRam", "avg_ram"])
    temperature = payload.get("temp", payload.get("temperature_c"))
    online = payload.get("online")
    status = first_string(payload, ["status"])
    if status is None and isinstance(online, bool):
        status = "Online" if online else "Offline"
    elif status is not None:
        status = "Online" if status.lower() == "online" else "Offline" if status.lower() == "offline" else status

    mode = first_string(payload, ["mode", "state"]) or "Unknown"
    heartbeat = first_string(payload, ["heartbeat"]) or "No signal"
    if isinstance(temperature, (int, float)):
        temp = f"{temperature:.1f} C"
    elif isinstance(temperature, str) and temperature:
        temp = temperature
    else:
        temp = "-"

    return {
        "id": device_id,
        "device_id": device_id,
        "cpu": clamp_percent(cpu) if cpu is not None else 0,
        "ram": clamp_percent(ram) if ram is not None else 0,
        "temp": temp,
        "temperature_c": parse_numeric(payload.get("temperature_c")),
        "heartbeat": heartbeat,
        "mode": mode,
        "state": first_string(payload, ["state"]) or mode,
        "status": status or "Unknown",
        "online": bool(online) if isinstance(online, bool) else status == "Online",
        "modelVersion": first_string(payload, ["model_version", "modelVersion"]),
        "lastSeen": payload.get("ts") if isinstance(payload.get("ts"), str) else recorded_at_iso(recorded_at),
        "recordedAt": recorded_at,
    }


def normalize_metric_payload(device_id: str | None, payload: Any, recorded_at: int) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    resolved_device_id = first_string(payload, ["device_id", "client_id"]) or device_id
    round_number = first_numeric(payload, ["round", "currentRound", "current_round"])
    global_accuracy = normalize_accuracy(payload.get("globalAccuracy", payload.get("global_accuracy", payload.get("accuracy"))))

    return {
        "device_id": resolved_device_id,
        "round": round(round_number) if round_number is not None else None,
        "globalAccuracy": global_accuracy,
        "globalLoss": first_numeric(payload, ["globalLoss", "global_loss", "loss"]),
        "localLoss": first_numeric(payload, ["localLoss", "local_loss"]),
        "localAccuracy": normalize_accuracy(payload.get("localAccuracy", payload.get("local_accuracy"))),
        "samplesTrained": first_numeric(payload, ["samplesTrained", "samples_trained", "num_samples"]),
        "drift": first_numeric(payload, ["drift", "clientDrift", "client_drift"]),
        "fps": first_numeric(payload, ["fps"]),
        "inferenceMs": first_numeric(payload, ["inference_ms", "inferenceMs"]),
        "cpu": first_numeric(payload, ["cpu", "cpu_percent", "avgCpu", "avg_cpu"]),
        "ram": first_numeric(payload, ["ram", "ram_percent", "avgRam", "avg_ram"]),
        "mode": first_string(payload, ["mode"]),
        "ts": payload.get("ts") if isinstance(payload.get("ts"), str) else recorded_at_iso(recorded_at),
        "recordedAt": recorded_at,
    }


def normalize_message(topic: str, kind: str, device_id: str | None, payload_text: str, recorded_at: int) -> dict[str, Any]:
    parsed = parse_json(payload_text)
    message = parsed if isinstance(parsed, dict) else {"message": payload_text}
    resolved_device_id = first_string(message, ["device_id", "client_id"]) if isinstance(message, dict) else None
    return {
        "topic": topic,
        "kind": kind,
        "device_id": resolved_device_id or device_id,
        "payload": message,
        "text": payload_text,
        "ts": message.get("ts") if isinstance(message, dict) and isinstance(message.get("ts"), str) else recorded_at_iso(recorded_at),
        "recordedAt": recorded_at,
    }


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
                INSERT INTO mqtt_messages(topic, kind, device_id, payload_text, payload, payload_json, recorded_at, created_at)
                VALUES (
                  :topic,
                  :kind,
                  :device_id,
                  :payload_text,
                  :payload_text,
                  CAST(:payload_json AS JSONB),
                  :recorded_at,
                  to_timestamp(:recorded_at / 1000.0)
                )
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


def get_recent_messages_by_kinds(kinds: list[str], limit: int = 100) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT topic, kind, device_id, payload_text, recorded_at
        FROM mqtt_messages
        WHERE kind = ANY(:kinds)
        ORDER BY recorded_at DESC, id DESC
        LIMIT :limit
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(query, {"kinds": kinds, "limit": limit}).fetchall()
    return [normalize_message(row[0], row[1], row[2], row[3], row[4]) for row in rows]


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

    status_messages = get_recent_messages_by_kinds(["status"], 200)
    metrics_messages = get_recent_messages_by_kinds(["metrics"], 200)
    structured_events = get_recent_messages_by_kinds(["event"], 50)
    structured_logs = get_recent_messages_by_kinds(["logs"], 50)
    structured_classifications = get_recent_messages_by_kinds(["classification"], 50)
    structured_help_requests = get_recent_messages_by_kinds(["help"], 50)

    event_stream = get_recent_stream_by_kinds(["event", "logs"], 16)
    classifications = get_recent_stream_by_kinds(["classification"], 16)
    help_requests = get_recent_stream_by_kinds(["help"], 16)

    devices_by_id: dict[str, dict[str, Any]] = {
        row[0]: {
            "id": row[0],
            "device_id": row[0],
            "cpu": row[1] if row[1] is not None else 0,
            "ram": row[2] if row[2] is not None else 0,
            "temp": row[3] if row[3] is not None else "-",
            "heartbeat": row[4] if row[4] is not None else "No signal",
            "mode": row[5] if row[5] is not None else "Unknown",
            "state": row[5] if row[5] is not None else "Unknown",
            "status": row[6] if row[6] is not None else "Unknown",
            "online": row[6] == "Online",
            "modelVersion": None,
            "lastSeen": None,
            "recordedAt": None,
        }
        for row in devices_rows
    }

    for message in reversed(status_messages):
        device_id = message.get("device_id")
        normalized = normalize_status_payload(
            str(device_id) if device_id else "",
            message.get("payload"),
            int(message["recordedAt"]),
        )
        if normalized and normalized["id"]:
            devices_by_id[normalized["id"]] = {**devices_by_id.get(normalized["id"], {}), **normalized}

    metric_history = [
        normalized
        for normalized in (
            normalize_metric_payload(message.get("device_id"), message.get("payload"), int(message["recordedAt"]))
            for message in reversed(metrics_messages)
        )
        if normalized is not None
    ]
    latest_metric = metric_history[-1] if metric_history else None
    fl_snapshot = coordinator.snapshot()

    devices = sorted(
        [
            {
                **device,
                "latestClassification": None,
                "latestConfidence": None,
            }
            for device in devices_by_id.values()
        ],
        key=lambda device: device["id"],
    )

    latest_classification_by_device: dict[str, dict[str, Any]] = {}
    for message in reversed(structured_classifications):
        device_id = message.get("device_id")
        payload = message.get("payload")
        if isinstance(device_id, str) and isinstance(payload, dict):
            latest_classification_by_device[device_id] = {
                "label": payload.get("label"),
                "confidence": parse_numeric(payload.get("confidence")),
                "ts": message.get("ts"),
            }

    devices = [
        {
            **device,
            "latestClassification": latest_classification_by_device.get(device["id"], {}).get("label"),
            "latestConfidence": latest_classification_by_device.get(device["id"], {}).get("confidence"),
        }
        for device in devices
    ]

    return {
        "devices": devices,
        "metrics": {
            "globalAccuracy": latest_metric.get("globalAccuracy") if latest_metric and latest_metric.get("globalAccuracy") is not None else metrics_row[0] if metrics_row else None,
            "globalLoss": latest_metric.get("globalLoss") if latest_metric and latest_metric.get("globalLoss") is not None else metrics_row[1] if metrics_row else None,
        },
        "metricHistory": metric_history,
        "events": structured_events,
        "logs": structured_logs,
        "classificationEvents": structured_classifications,
        "helpRequestEvents": structured_help_requests,
        "fl": {
            "currentRound": fl_snapshot["current_round"],
            "trainingState": "running" if any(device.get("online") for device in devices) else "idle",
            "globalAccuracy": latest_metric.get("globalAccuracy") if latest_metric else None,
            "globalLoss": latest_metric.get("globalLoss") if latest_metric else None,
            "activeClients": sum(1 for device in devices if device.get("online")),
            "samplesTrained": latest_metric.get("samplesTrained") if latest_metric else None,
            "modelVersion": fl_snapshot["model_version"],
            "pendingUpdates": fl_snapshot["pending_updates"],
            "minClientsPerRound": fl_snapshot["min_clients_per_round"],
            "modelSize": fl_snapshot["model_size"],
        },
        "federated": fl_snapshot,
        "eventStream": event_stream,
        "classifications": classifications,
        "helpRequests": help_requests,
    }
