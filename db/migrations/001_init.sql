PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS mqtt_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic TEXT NOT NULL,
  kind TEXT NOT NULL,
  device_id TEXT,
  payload_text TEXT NOT NULL,
  payload_json TEXT,
  recorded_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS device_status_latest (
  device_id TEXT PRIMARY KEY,
  cpu INTEGER,
  ram INTEGER,
  temp TEXT,
  heartbeat TEXT,
  mode TEXT,
  status TEXT,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS device_status_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id TEXT NOT NULL,
  cpu INTEGER,
  ram INTEGER,
  temp TEXT,
  heartbeat TEXT,
  mode TEXT,
  status TEXT,
  recorded_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS coordinator_metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  global_accuracy REAL,
  global_loss REAL,
  avg_cpu REAL,
  avg_ram REAL,
  online_clients INTEGER,
  recorded_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mqtt_messages_kind_recorded_at
  ON mqtt_messages(kind, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_mqtt_messages_device_recorded_at
  ON mqtt_messages(device_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_status_history_device_recorded_at
  ON device_status_history(device_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_recorded_at
  ON coordinator_metrics(recorded_at DESC);
