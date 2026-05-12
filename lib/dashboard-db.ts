import fs from "node:fs";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";

export type MqttKind = "status" | "metrics" | "event" | "classification" | "help" | "logs" | "other";

export interface IngestMqttInput {
  topic: string;
  payload: string;
  timestamp?: number;
}

interface DeviceStatusPatch {
  cpu?: number;
  ram?: number;
  temp?: string;
  heartbeat?: string;
  mode?: string;
  status?: string;
}

interface MetricsPatch {
  globalAccuracy?: number;
  globalLoss?: number;
  avgCpu?: number;
  avgRam?: number;
  onlineClients?: number;
}

type DbGlobal = typeof globalThis & {
  dashboardDb?: DatabaseSync;
  dashboardDbInitialized?: boolean;
};

const dbGlobal = globalThis as DbGlobal;

function ensureDbDir() {
  const dir = path.join(process.cwd(), "data");
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function getDb() {
  if (!dbGlobal.dashboardDb) {
    const dbDir = ensureDbDir();
    const dbPath = path.join(dbDir, "dashboard.sqlite");
    dbGlobal.dashboardDb = new DatabaseSync(dbPath);
  }

  if (!dbGlobal.dashboardDbInitialized) {
    applyMigrations(dbGlobal.dashboardDb);
    dbGlobal.dashboardDbInitialized = true;
  }

  return dbGlobal.dashboardDb;
}

function applyMigrations(db: DatabaseSync) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS schema_migrations (
      name TEXT PRIMARY KEY,
      applied_at INTEGER NOT NULL
    );
  `);

  const migrationsDir = path.join(process.cwd(), "db", "migrations");
  if (!fs.existsSync(migrationsDir)) return;

  const migrationFiles = fs
    .readdirSync(migrationsDir)
    .filter((filename) => filename.endsWith(".sql"))
    .sort((a, b) => a.localeCompare(b));

  const alreadyAppliedStmt = db.prepare(`SELECT name FROM schema_migrations WHERE name = ? LIMIT 1`);
  const insertAppliedStmt = db.prepare(`INSERT INTO schema_migrations(name, applied_at) VALUES (?, ?)`);

  migrationFiles.forEach((filename) => {
    const already = alreadyAppliedStmt.get(filename) as { name: string } | undefined;
    if (already) return;

    const sql = fs.readFileSync(path.join(migrationsDir, filename), "utf8");
    try {
      db.exec(sql);
      insertAppliedStmt.run(filename, Date.now());
    } catch (error) {
      throw new Error(`Failed applying migration ${filename}: ${String(error)}`);
    }
  });
}

function clampPercent(value: number): number {
  if (value < 0) return 0;
  if (value > 100) return 100;
  return Math.round(value);
}

function parseNumeric(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number.parseFloat(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return undefined;
}

function parseJson(value: string): unknown {
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

function getKind(topic: string): MqttKind {
  const lower = topic.toLowerCase();
  if (lower.endsWith("/status")) return "status";
  if (lower.endsWith("/metrics")) return "metrics";
  if (lower.endsWith("/event")) return "event";
  if (lower.endsWith("/classification")) return "classification";
  if (lower.endsWith("/help")) return "help";
  if (lower.endsWith("/logs")) return "logs";
  return "other";
}

function getDeviceId(topic: string): string | null {
  const parts = topic.split("/");
  if (parts.length < 3) return null;
  return parts[parts.length - 2] || null;
}

function parseStatusPatch(payload: unknown): DeviceStatusPatch {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return {};
  const row = payload as Record<string, unknown>;
  const patch: DeviceStatusPatch = {};

  const cpu = parseNumeric(row.cpu);
  const ram = parseNumeric(row.ram);

  if (cpu !== undefined) patch.cpu = clampPercent(cpu);
  if (ram !== undefined) patch.ram = clampPercent(ram);
  if (typeof row.temp === "string") patch.temp = row.temp;
  if (typeof row.heartbeat === "string") patch.heartbeat = row.heartbeat;
  if (typeof row.mode === "string") patch.mode = row.mode;
  if (typeof row.status === "string") patch.status = row.status;

  return patch;
}

function parseMetricsPatch(payload: unknown): MetricsPatch {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return {};
  const row = payload as Record<string, unknown>;
  const patch: MetricsPatch = {};

  const globalAccuracy = parseNumeric(row.globalAccuracy ?? row.global_accuracy ?? row.accuracy);
  const globalLoss = parseNumeric(row.globalLoss ?? row.global_loss ?? row.loss);
  const avgCpu = parseNumeric(row.avgCpu ?? row.avg_cpu);
  const avgRam = parseNumeric(row.avgRam ?? row.avg_ram);
  const onlineClients = parseNumeric(row.onlineClients ?? row.online_clients);

  if (globalAccuracy !== undefined) patch.globalAccuracy = globalAccuracy;
  if (globalLoss !== undefined) patch.globalLoss = globalLoss;
  if (avgCpu !== undefined) patch.avgCpu = avgCpu;
  if (avgRam !== undefined) patch.avgRam = avgRam;
  if (onlineClients !== undefined) patch.onlineClients = Math.max(0, Math.round(onlineClients));

  return patch;
}

function hasStatusValues(patch: DeviceStatusPatch) {
  return Object.keys(patch).length > 0;
}

function hasMetricsValues(patch: MetricsPatch) {
  return Object.keys(patch).length > 0;
}

export function ingestMqttMessage(input: IngestMqttInput) {
  const db = getDb();
  const kind = getKind(input.topic);
  const deviceId = getDeviceId(input.topic);
  const ts = Number.isFinite(input.timestamp) ? Math.trunc(input.timestamp as number) : Date.now();
  const parsed = parseJson(input.payload);
  const payloadJson = typeof parsed === "object" && parsed !== null ? JSON.stringify(parsed) : null;

  const insertMessage = db.prepare(`
    INSERT INTO mqtt_messages(topic, kind, device_id, payload_text, payload_json, recorded_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `);
  insertMessage.run(input.topic, kind, deviceId, input.payload, payloadJson, ts);

  if (kind === "status" && deviceId) {
    const patch = parseStatusPatch(parsed);
    if (hasStatusValues(patch)) {
      const upsertLatest = db.prepare(`
        INSERT INTO device_status_latest(device_id, cpu, ram, temp, heartbeat, mode, status, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(device_id) DO UPDATE SET
          cpu = COALESCE(excluded.cpu, device_status_latest.cpu),
          ram = COALESCE(excluded.ram, device_status_latest.ram),
          temp = COALESCE(excluded.temp, device_status_latest.temp),
          heartbeat = COALESCE(excluded.heartbeat, device_status_latest.heartbeat),
          mode = COALESCE(excluded.mode, device_status_latest.mode),
          status = COALESCE(excluded.status, device_status_latest.status),
          updated_at = excluded.updated_at
      `);
      upsertLatest.run(
        deviceId,
        patch.cpu ?? null,
        patch.ram ?? null,
        patch.temp ?? null,
        patch.heartbeat ?? null,
        patch.mode ?? null,
        patch.status ?? null,
        ts
      );

      const insertHistory = db.prepare(`
        INSERT INTO device_status_history(device_id, cpu, ram, temp, heartbeat, mode, status, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `);
      insertHistory.run(
        deviceId,
        patch.cpu ?? null,
        patch.ram ?? null,
        patch.temp ?? null,
        patch.heartbeat ?? null,
        patch.mode ?? null,
        patch.status ?? null,
        ts
      );
    }
  }

  if (kind === "metrics") {
    const patch = parseMetricsPatch(parsed);
    if (hasMetricsValues(patch)) {
      const insertMetrics = db.prepare(`
        INSERT INTO coordinator_metrics(global_accuracy, global_loss, avg_cpu, avg_ram, online_clients, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?)
      `);
      insertMetrics.run(
        patch.globalAccuracy ?? null,
        patch.globalLoss ?? null,
        patch.avgCpu ?? null,
        patch.avgRam ?? null,
        patch.onlineClients ?? null,
        ts
      );
    }
  }
}

function getRecentStreamByKinds(kinds: MqttKind[], limit = 16) {
  const db = getDb();
  const placeholders = kinds.map(() => "?").join(",");
  const stmt = db.prepare(`
    SELECT payload_text
    FROM mqtt_messages
    WHERE kind IN (${placeholders})
    ORDER BY recorded_at DESC, id DESC
    LIMIT ?
  `);
  const rows = stmt.all(...kinds, limit) as Array<{ payload_text: string }>;
  return rows.map((row) => row.payload_text);
}

export function getDashboardBootstrap() {
  const db = getDb();

  const devicesStmt = db.prepare(`
    SELECT device_id AS id, cpu, ram, temp, heartbeat, mode, status
    FROM device_status_latest
    ORDER BY device_id ASC
  `);
  const devices = devicesStmt.all() as Array<{
    id: string;
    cpu: number | null;
    ram: number | null;
    temp: string | null;
    heartbeat: string | null;
    mode: string | null;
    status: string | null;
  }>;

  const latestMetricsStmt = db.prepare(`
    SELECT global_accuracy, global_loss
    FROM coordinator_metrics
    ORDER BY recorded_at DESC, id DESC
    LIMIT 1
  `);
  const metricsRow = latestMetricsStmt.get() as { global_accuracy: number | null; global_loss: number | null } | undefined;

  const eventStream = getRecentStreamByKinds(["event", "logs"], 16);
  const classifications = getRecentStreamByKinds(["classification"], 16);
  const helpRequests = getRecentStreamByKinds(["help"], 16);

  return {
    devices: devices.map((device) => ({
      id: device.id,
      cpu: device.cpu ?? 0,
      ram: device.ram ?? 0,
      temp: device.temp ?? "-",
      heartbeat: device.heartbeat ?? "No signal",
      mode: device.mode ?? "Unknown",
      status: device.status ?? "Unknown",
    })),
    metrics: {
      globalAccuracy: metricsRow?.global_accuracy ?? null,
      globalLoss: metricsRow?.global_loss ?? null,
    },
    eventStream,
    classifications,
    helpRequests,
  };
}
