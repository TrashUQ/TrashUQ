from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import settings


engine: Engine = create_engine(settings.database_url, pool_pre_ping=True)


def ensure_schema() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS mqtt_messages (
                  id BIGSERIAL PRIMARY KEY,
                  topic TEXT NOT NULL,
                  kind TEXT NOT NULL,
                  device_id TEXT,
                  payload_text TEXT NOT NULL,
                  payload_json JSONB,
                  recorded_at BIGINT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS device_status_latest (
                  device_id TEXT PRIMARY KEY,
                  cpu INTEGER,
                  ram INTEGER,
                  temp TEXT,
                  heartbeat TEXT,
                  mode TEXT,
                  status TEXT,
                  updated_at BIGINT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS device_status_history (
                  id BIGSERIAL PRIMARY KEY,
                  device_id TEXT NOT NULL,
                  cpu INTEGER,
                  ram INTEGER,
                  temp TEXT,
                  heartbeat TEXT,
                  mode TEXT,
                  status TEXT,
                  recorded_at BIGINT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS coordinator_metrics (
                  id BIGSERIAL PRIMARY KEY,
                  global_accuracy DOUBLE PRECISION,
                  global_loss DOUBLE PRECISION,
                  avg_cpu DOUBLE PRECISION,
                  avg_ram DOUBLE PRECISION,
                  online_clients INTEGER,
                  recorded_at BIGINT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_mqtt_messages_kind_recorded_at
                  ON mqtt_messages(kind, recorded_at DESC);
                CREATE INDEX IF NOT EXISTS idx_mqtt_messages_device_recorded_at
                  ON mqtt_messages(device_id, recorded_at DESC);
                CREATE INDEX IF NOT EXISTS idx_status_history_device_recorded_at
                  ON device_status_history(device_id, recorded_at DESC);
                CREATE INDEX IF NOT EXISTS idx_metrics_recorded_at
                  ON coordinator_metrics(recorded_at DESC);
                """
            )
        )
