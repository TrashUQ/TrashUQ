"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Brain,
  Download,
  Gauge,
  Layers,
  Network,
  Server,
  Shield,
  Timer,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { MqttService, type MqttMessage } from "@/lib/mqtt";

type TabKey =
  | "Overview"
  | "Live Devices"
  | "Federated Rounds"
  | "Model Performance"
  | "Network & Privacy"
  | "Data Quality"
  | "Model Registry"
  | "Alerts & Logs";

const navItems: { name: TabKey; icon: React.ComponentType<{ className?: string }> }[] = [
  { name: "Overview", icon: Gauge },
  { name: "Live Devices", icon: Server },
  { name: "Federated Rounds", icon: Timer },
  { name: "Model Performance", icon: Brain },
  { name: "Network & Privacy", icon: Shield },
  { name: "Data Quality", icon: BarChart3 },
  { name: "Model Registry", icon: Layers },
  { name: "Alerts & Logs", icon: AlertTriangle },
];

const chartColors = {
  mustard: "#d79921",
  olive: "#98971a",
  cyan: "#458588",
  orange: "#d65d0e",
  tealSoft: "#83a598",
  redSoft: "#cc241d",
  neonPink: "#ff4fd8",
  neonGreen: "#7dff7a",
  neonBlue: "#5ee9ff",
  rose: "#fb7185",
};

const tooltipStyle = {
  backgroundColor: "#0b1022",
  border: "1px solid #27324f",
  color: "#dbeafe",
};

interface DeviceStatus {
  id: string;
  cpu: number;
  ram: number;
  temp: string;
  heartbeat: string;
  mode: string;
  status: string;
  online?: boolean;
  modelVersion?: string | null;
  lastSeen?: string | null;
  latestClassification?: string | null;
  latestConfidence?: number | null;
}

type DeviceStatusPatch = Partial<DeviceStatus>;

interface DashboardMetric {
  device_id?: string | null;
  round?: number | null;
  globalAccuracy?: number | null;
  globalLoss?: number | null;
  localLoss?: number | null;
  localAccuracy?: number | null;
  samplesTrained?: number | null;
  drift?: number | null;
  fps?: number | null;
  inferenceMs?: number | null;
  cpu?: number | null;
  ram?: number | null;
  mode?: string | null;
  ts?: string | null;
  recordedAt?: number | null;
}

function safeParseJSON(value: string) {
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

function getPayloadText(payload: unknown) {
  if (typeof payload === "string") return payload;
  if (payload === null) return "null";
  return JSON.stringify(payload);
}

function clampHistory<T>(items: T[], max = 16) {
  return items.slice(-max);
}

function toNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number.parseFloat(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function formatPercent(value: unknown): string | null {
  const numeric = toNumber(value);
  if (numeric === null) return null;
  return `${numeric.toFixed(1)}%`;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function clampPercent(value: number): number {
  if (value < 0) return 0;
  if (value > 100) return 100;
  return Math.round(value);
}

function normalizePercentValue(value: unknown): number | null {
  const numeric = toNumber(value);
  if (numeric === null) return null;
  return numeric >= 0 && numeric <= 1 ? numeric * 100 : numeric;
}

function getString(payload: Record<string, unknown>, keys: string[]): string | null {
  for (const key of keys) {
    const value = payload[key];
    if (typeof value === "string" && value.length > 0) return value;
  }
  return null;
}

function getNumber(payload: Record<string, unknown>, keys: string[]): number | null {
  for (const key of keys) {
    const value = toNumber(payload[key]);
    if (value !== null) return value;
  }
  return null;
}

function formatMetricPercent(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(1)}%` : "--";
}

function formatMetricNumber(value: number | null | undefined, digits = 2): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "--";
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "--";
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) return value;
  return new Date(parsed).toLocaleTimeString();
}

function normalizeStatusLabel(value: unknown, online: unknown): string | undefined {
  if (typeof value === "string" && value.length > 0) {
    if (value.toLowerCase() === "online") return "Online";
    if (value.toLowerCase() === "offline") return "Offline";
    return value;
  }
  if (typeof online === "boolean") return online ? "Online" : "Offline";
  return undefined;
}

function parseDeviceStatusPatch(payload: unknown): { patch: DeviceStatusPatch; issues: string[] } {
  if (!isPlainObject(payload)) {
    return { patch: {}, issues: ["payload is not an object"] };
  }

  const patch: DeviceStatusPatch = {};
  const issues: string[] = [];

  const cpu = getNumber(payload, ["cpu", "cpu_percent", "avgCpu", "avg_cpu"]);
  if (cpu !== null) {
    patch.cpu = clampPercent(cpu);
  }

  const ram = getNumber(payload, ["ram", "ram_percent", "avgRam", "avg_ram"]);
  if (ram !== null) {
    patch.ram = clampPercent(ram);
  }

  if ("temp" in payload || "temperature_c" in payload) {
    const temperature = payload.temp ?? payload.temperature_c;
    if (typeof temperature === "string") patch.temp = temperature;
    else if (typeof temperature === "number") patch.temp = `${temperature.toFixed(1)} C`;
    else if (temperature === null) patch.temp = "-";
    else issues.push("temp must be string, number, or null");
  }

  if ("heartbeat" in payload) {
    if (typeof payload.heartbeat === "string") patch.heartbeat = payload.heartbeat;
    else issues.push("heartbeat must be string");
  }

  const mode = getString(payload, ["mode", "state"]);
  if (mode) {
    patch.mode = mode;
  }

  const status = normalizeStatusLabel(payload.status, payload.online);
  if (status) {
    patch.status = status;
    patch.online = status === "Online";
  }

  const modelVersion = getString(payload, ["model_version", "modelVersion"]);
  if (modelVersion) {
    patch.modelVersion = modelVersion;
  }

  const lastSeen = getString(payload, ["ts", "lastSeen"]);
  if (lastSeen) {
    patch.lastSeen = lastSeen;
  }

  return { patch, issues };
}

function parseMetricPayload(payload: unknown, fallbackDeviceId?: string): { metric?: DashboardMetric; issues: string[] } {
  if (!isPlainObject(payload)) {
    return { issues: ["payload is not an object"] };
  }

  const issues: string[] = [];
  const roundNumber = getNumber(payload, ["round", "currentRound", "current_round"]);
  const metric: DashboardMetric = {
    device_id: getString(payload, ["device_id", "client_id"]) ?? fallbackDeviceId ?? null,
    round: roundNumber !== null ? Math.round(roundNumber) : null,
    globalAccuracy: normalizePercentValue(payload.globalAccuracy ?? payload.global_accuracy ?? payload.accuracy),
    globalLoss: getNumber(payload, ["globalLoss", "global_loss", "loss"]),
    localLoss: getNumber(payload, ["localLoss", "local_loss"]),
    localAccuracy: normalizePercentValue(payload.localAccuracy ?? payload.local_accuracy),
    samplesTrained: getNumber(payload, ["samplesTrained", "samples_trained", "num_samples"]),
    drift: getNumber(payload, ["drift", "clientDrift", "client_drift"]),
    fps: getNumber(payload, ["fps"]),
    inferenceMs: getNumber(payload, ["inference_ms", "inferenceMs"]),
    cpu: getNumber(payload, ["cpu", "cpu_percent", "avgCpu", "avg_cpu"]),
    ram: getNumber(payload, ["ram", "ram_percent", "avgRam", "avg_ram"]),
    mode: getString(payload, ["mode"]),
    ts: getString(payload, ["ts"]),
    recordedAt: Date.now(),
  };

  if (
    metric.globalAccuracy === null &&
    metric.globalLoss === null &&
    metric.localLoss === null &&
    metric.drift === null &&
    metric.cpu === null &&
    metric.ram === null
  ) {
    issues.push("metrics payload has no chartable numeric fields");
  }

  return { metric, issues };
}

type DashboardDevice = DeviceStatus;

interface DashboardBootstrapPayload {
  devices: DashboardDevice[];
  metrics: {
    globalAccuracy: number | null;
    globalLoss: number | null;
  };
  metricHistory?: DashboardMetric[];
  fl?: {
    currentRound: number | null;
    trainingState: string;
    globalAccuracy: number | null;
    globalLoss: number | null;
    activeClients: number;
    samplesTrained: number | null;
    modelVersion: number | null;
    pendingUpdates: number;
    minClientsPerRound: number;
    modelSize: number;
  };
  federated?: {
    current_round: number;
    model_version: number;
    online_clients: number;
    pending_updates: number;
    min_clients_per_round: number;
    model_size: number;
  };
  eventStream: string[];
  classifications: string[];
  helpRequests: string[];
}

async function loadDashboardBootstrap(): Promise<DashboardBootstrapPayload | null> {
  try {
    const response = await fetch("/api/dashboard/bootstrap", { cache: "no-store" });
    if (!response.ok) return null;
    const payload = await response.json();
    if (!payload?.ok || !payload?.data) return null;
    return payload.data as DashboardBootstrapPayload;
  } catch {
    return null;
  }
}

export default function Page() {
  const [activeTab, setActiveTab] = useState<TabKey>("Overview");
  const [devicesState, setDevicesState] = useState<DeviceStatus[]>([]);
  const [eventStreamState, setEventStreamState] = useState<string[]>([]);
  const [classificationsState, setClassificationsState] = useState<string[]>([]);
  const [helpRequestsState, setHelpRequestsState] = useState<string[]>([]);
  const [metricHistory, setMetricHistory] = useState<DashboardMetric[]>([]);
  const [globalAccuracy, setGlobalAccuracy] = useState("--");
  const [globalLoss, setGlobalLoss] = useState("--");
  const [samplesTrained, setSamplesTrained] = useState("--");
  const [federatedRound, setFederatedRound] = useState<number>(1);
  const [federatedModelVersion, setFederatedModelVersion] = useState<number>(1);
  const [federatedPendingUpdates, setFederatedPendingUpdates] = useState<number>(0);
  const [federatedMinClients, setFederatedMinClients] = useState<number>(2);
  const [mqttConnected, setMqttConnected] = useState(false);
  const [lastMqttMessageAt, setLastMqttMessageAt] = useState<number | null>(null);
  const mqttServiceRef = useRef<MqttService | null>(null);

  useEffect(() => {
    let isMounted = true;
    const brokerUrl = process.env.NEXT_PUBLIC_MQTT_BROKER_URL ?? "ws://localhost:9001/mqtt";
    const topicRoot = process.env.NEXT_PUBLIC_MQTT_TOPIC_ROOT ?? "arduino";
    const username = process.env.NEXT_PUBLIC_MQTT_USERNAME;
    const password = process.env.NEXT_PUBLIC_MQTT_PASSWORD;

    const applySnapshot = (snapshot: DashboardBootstrapPayload | null) => {
      if (!isMounted || !snapshot) return;

      if (snapshot.devices.length > 0) {
        setDevicesState(snapshot.devices);
      }

      if (snapshot.eventStream.length > 0) {
        setEventStreamState(clampHistory(snapshot.eventStream, 16));
      }

      if (snapshot.classifications.length > 0) {
        setClassificationsState(clampHistory(snapshot.classifications, 16));
      }

      if (snapshot.helpRequests.length > 0) {
        setHelpRequestsState(clampHistory(snapshot.helpRequests, 16));
      }

      if (snapshot.metricHistory) {
        setMetricHistory(snapshot.metricHistory.slice(-100));
      }

      const latestAccuracy = snapshot.fl?.globalAccuracy ?? snapshot.metrics.globalAccuracy;
      const latestLoss = snapshot.fl?.globalLoss ?? snapshot.metrics.globalLoss;
      if (latestAccuracy !== null && latestAccuracy !== undefined) {
        setGlobalAccuracy(formatMetricPercent(latestAccuracy));
      }

      if (latestLoss !== null && latestLoss !== undefined) {
        setGlobalLoss(formatMetricNumber(latestLoss));
      }

      if (snapshot.fl?.samplesTrained !== null && snapshot.fl?.samplesTrained !== undefined) {
        setSamplesTrained(String(Math.round(snapshot.fl.samplesTrained)));
      }
      if (snapshot.federated) {
        setFederatedRound(snapshot.federated.current_round);
        setFederatedModelVersion(snapshot.federated.model_version);
        setFederatedPendingUpdates(snapshot.federated.pending_updates);
        setFederatedMinClients(snapshot.federated.min_clients_per_round);
      }
      if (snapshot.fl?.currentRound) {
        setFederatedRound(snapshot.fl.currentRound);
      }
      if (snapshot.fl?.modelVersion) {
        setFederatedModelVersion(snapshot.fl.modelVersion);
      }
    };

    void loadDashboardBootstrap().then(applySnapshot);
    const pollId = setInterval(() => {
      void loadDashboardBootstrap().then(applySnapshot);
    }, 4000);

    const mqttService = new MqttService({
      brokerUrl,
      topicRoot,
      username: username && username.length > 0 ? username : undefined,
      password: password && password.length > 0 ? password : undefined,
      onConnect: () => {
        if (!isMounted) return;
        setMqttConnected(true);
        setLastMqttMessageAt(Date.now());
        setEventStreamState((current) => clampHistory([`MQTT connected to ${brokerUrl}`, ...current]));
      },
      onError: (error) => {
        if (!isMounted) return;
        setMqttConnected(false);
        setEventStreamState((current) => clampHistory([`MQTT error: ${String(error)}`, ...current]));
      },
      onMessage: (message: MqttMessage) => {
        if (!isMounted) return;
        setLastMqttMessageAt(Date.now());
        const { topic, payload } = message;
        const parsedPayload = safeParseJSON(payload);
        const topicLower = topic.toLowerCase();

        if (topicLower.endsWith("/event")) {
          setEventStreamState((current) => clampHistory([getPayloadText(parsedPayload), ...current]));
          return;
        }

        if (topicLower.endsWith("/status")) {
          const segments = topic.split("/");
          const deviceId = segments[segments.length - 2] ?? "unknown";
          const { patch, issues } = parseDeviceStatusPatch(parsedPayload);

          if (issues.length > 0) {
            setEventStreamState((current) => clampHistory([`Invalid status payload (${deviceId}): ${issues.join(", ")}`, ...current]));
          }

          if (Object.keys(patch).length > 0) {
            setDevicesState((current) => {
              const existing = current.find((device) => device.id === deviceId);
              if (existing) {
                return current.map((device) => device.id === deviceId ? { ...device, ...patch } : device);
              }
              return [
                ...current,
                {
                  id: deviceId,
                  cpu: 0,
                  ram: 0,
                  temp: "-",
                  heartbeat: "No signal",
                  mode: "Unknown",
                  status: "Unknown",
                  ...patch,
                },
              ];
            });
          } else {
            setEventStreamState((current) => clampHistory([`Status payload ignored (${deviceId}): no valid fields`, ...current]));
          }
          return;
        }

        if (topicLower.endsWith("/metrics")) {
          const segments = topic.split("/");
          const deviceId = segments[segments.length - 2] ?? "unknown";
          const { metric, issues } = parseMetricPayload(parsedPayload, deviceId);

          if (issues.length > 0) {
            setEventStreamState((current) => clampHistory([`Invalid metrics payload: ${issues.join(", ")}`, ...current]));
          }

          if (metric) {
            setMetricHistory((current) => clampHistory([...current, metric], 100));
            if (metric.globalAccuracy !== null && metric.globalAccuracy !== undefined) {
              setGlobalAccuracy(formatMetricPercent(metric.globalAccuracy));
            }
            if (metric.globalLoss !== null && metric.globalLoss !== undefined) {
              setGlobalLoss(formatMetricNumber(metric.globalLoss));
            }
            if (metric.round) {
              setFederatedRound(metric.round);
            }
            if (metric.samplesTrained !== null && metric.samplesTrained !== undefined) {
              setSamplesTrained(String(Math.round(metric.samplesTrained)));
            }
            if (metric.device_id && (metric.cpu !== null || metric.ram !== null || metric.mode)) {
              setDevicesState((current) => current.map((device) => device.id === metric.device_id ? {
                ...device,
                cpu: metric.cpu !== null && metric.cpu !== undefined ? clampPercent(metric.cpu) : device.cpu,
                ram: metric.ram !== null && metric.ram !== undefined ? clampPercent(metric.ram) : device.ram,
                mode: metric.mode ?? device.mode,
                lastSeen: metric.ts ?? device.lastSeen,
              } : device));
            }
          }

          if (!metric || issues.length > 0) {
            setEventStreamState((current) => clampHistory([`Metrics payload ignored: no valid fields`, ...current]));
          }
          return;
        }

        if (topicLower.endsWith("/classification")) {
          const segments = topic.split("/");
          const deviceId = segments[segments.length - 2] ?? "unknown";
          if (isPlainObject(parsedPayload)) {
            const label = typeof parsedPayload.label === "string" ? parsedPayload.label : null;
            const confidence = toNumber(parsedPayload.confidence);
            setDevicesState((current) => current.map((device) => device.id === deviceId ? {
              ...device,
              latestClassification: label ?? device.latestClassification,
              latestConfidence: confidence ?? device.latestConfidence,
              lastSeen: typeof parsedPayload.ts === "string" ? parsedPayload.ts : device.lastSeen,
            } : device));
          }
          setClassificationsState((current) => clampHistory([getPayloadText(parsedPayload), ...current]));
          return;
        }

        if (topicLower.endsWith("/help")) {
          setHelpRequestsState((current) => clampHistory([getPayloadText(parsedPayload), ...current]));
          return;
        }

        if (topicLower.endsWith("/logs")) {
          setEventStreamState((current) => clampHistory([getPayloadText(parsedPayload), ...current]));
          return;
        }

        // Log other messages
        setEventStreamState((current) => clampHistory([`MQTT ${topic}: ${getPayloadText(parsedPayload)}`, ...current]));
      },
    });

    mqttServiceRef.current = mqttService;
    mqttService.connect().catch((error) => {
      setMqttConnected(false);
      setEventStreamState((current) => clampHistory([`MQTT startup failed: ${String(error)}`, ...current]));
    });

    return () => {
      isMounted = false;
      setMqttConnected(false);
      clearInterval(pollId);
      mqttService.disconnect();
    };
  }, []);

  const totalDevices = devicesState.length;
  const onlineDevices = devicesState.filter((device) => device.status === "Online").length;
  const trainingDevices = devicesState.filter((device) => ["training", "running", "simulation"].includes(String(device.mode).toLowerCase())).length;
  const avgCpuLoad = totalDevices
    ? Math.round(devicesState.reduce((sum, device) => sum + (typeof device.cpu === "number" ? device.cpu : 0), 0) / totalDevices)
    : 0;
  const avgRamLoad = totalDevices
    ? Math.round(devicesState.reduce((sum, device) => sum + (typeof device.ram === "number" ? device.ram : 0), 0) / totalDevices)
    : 0;
  const trainingStateLabel = mqttConnected ? (trainingDevices > 0 ? "Running" : "Idle") : "Disconnected";
  const lastMessageLabel = lastMqttMessageAt ? new Date(lastMqttMessageAt).toLocaleTimeString() : "--";
  const latestModelVersion = devicesState.find((device) => device.modelVersion)?.modelVersion ?? `v${federatedModelVersion}`;
  const lossChartData = metricHistory
    .filter((metric) => metric.localLoss !== null || metric.globalLoss !== null)
    .map((metric, index) => ({
      label: metric.round ? `R${metric.round}` : formatTimestamp(metric.ts) || `#${index + 1}`,
      localLoss: metric.localLoss,
      globalLoss: metric.globalLoss,
      device: metric.device_id ?? "unknown",
    }));
  const driftChartData = metricHistory
    .filter((metric) => metric.drift !== null && metric.drift !== undefined)
    .map((metric, index) => ({
      label: metric.round ? `R${metric.round}` : formatTimestamp(metric.ts) || `#${index + 1}`,
      drift: metric.drift,
      device: metric.device_id ?? "unknown",
    }));
  const accuracyChartData = metricHistory
    .filter((metric) => metric.globalAccuracy !== null || metric.localAccuracy !== null)
    .map((metric, index) => ({
      label: metric.round ? `R${metric.round}` : formatTimestamp(metric.ts) || `#${index + 1}`,
      globalAccuracy: metric.globalAccuracy,
      localAccuracy: metric.localAccuracy,
    }));
  const roundSummary = Array.from(
    metricHistory.reduce((byRound, metric) => {
      if (!metric.round) return byRound;
      const current = byRound.get(metric.round) ?? { round: metric.round, devices: new Set<string>(), samples: 0 };
      if (metric.device_id) current.devices.add(metric.device_id);
      if (metric.samplesTrained) current.samples = Math.max(current.samples, metric.samplesTrained);
      byRound.set(metric.round, current);
      return byRound;
    }, new Map<number, { round: number; devices: Set<string>; samples: number }>())
  ).map(([, value]) => ({
    round: value.round,
    participants: value.devices.size,
    samples: value.samples,
  }));

  const content = useMemo(() => {
    if (activeTab === "Overview") {
      return (
        <div className="space-y-4">
          <Card className="border-slate-800/80 bg-slate-900/60">
            <CardContent className="flex flex-wrap items-center gap-3 p-4 text-sm text-slate-300">
              <span className="text-xl font-semibold text-slate-100">Federated Live</span>
              <span className="text-slate-400">client-server federated learning on Arduino UNO Q</span>
              <Badge className={mqttConnected ? "bg-lime-400 text-slate-900" : "bg-rose-400 text-slate-900"}>
                {mqttConnected ? "MQTT ONLINE" : "MQTT OFFLINE"}
              </Badge>
              <span>round <b className="text-amber-300">R{federatedRound}</b></span>
              <span>active clients <b className="text-lime-300">{onlineDevices}/{totalDevices}</b></span>
              <span>samples trained <b className="text-orange-300">{samplesTrained}</b></span>
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard title="Active Devices" value={`${onlineDevices} / ${totalDevices}`} />
            <StatCard title="Current Round" value={`R${federatedRound}`} />
            <StatCard title="Global Accuracy" value={globalAccuracy} />
            <StatCard title="Training State" value={trainingStateLabel} />
          </div>

          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 px-3 py-2 text-sm text-slate-300">Model version: <span className="text-amber-300">{latestModelVersion}</span></div>
            <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 px-3 py-2 text-sm text-slate-300">Avg CPU: <span className="text-lime-300">{avgCpuLoad}%</span></div>
            <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 px-3 py-2 text-sm text-slate-300">Avg RAM: <span className="text-amber-300">{avgRamLoad}%</span></div>
            <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 px-3 py-2 text-sm text-slate-300">Global loss: <span className="text-orange-300">{globalLoss}</span> · Last MQTT: <span className="text-lime-300">{lastMessageLabel}</span></div>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="border-slate-800/80 bg-slate-900/60 xl:mt-10">
              <CardHeader>
                <CardTitle>Local Training Loss · Per Client · Per Round</CardTitle>
              </CardHeader>
              <CardContent className="h-72">
                {lossChartData.length === 0 ? (
                  <WaitingState message="Waiting for FL metric data with localLoss/globalLoss." />
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={lossChartData}>
                      <CartesianGrid className="chart-grid" strokeDasharray="3 3" />
                      <XAxis className="chart-axis" dataKey="label" />
                      <YAxis className="chart-axis" />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Area type="monotone" dataKey="localLoss" name="Local loss" stroke={chartColors.mustard} fill={chartColors.mustard} fillOpacity={0.2} connectNulls />
                      <Area type="monotone" dataKey="globalLoss" name="Global loss" stroke={chartColors.cyan} fill={chartColors.cyan} fillOpacity={0.12} connectNulls />
                    </AreaChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>

            <Card className="border-slate-800/80 bg-slate-900/60">
              <CardHeader>
                <CardTitle>Client Drift vs Aggregated Global Model</CardTitle>
              </CardHeader>
              <CardContent className="h-72">
                {driftChartData.length === 0 ? (
                  <WaitingState message="Waiting for client drift data." />
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={driftChartData}>
                      <CartesianGrid className="chart-grid" strokeDasharray="3 3" />
                      <XAxis className="chart-axis" dataKey="label" />
                      <YAxis className="chart-axis" />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Line type="monotone" dataKey="drift" name="Client drift" stroke={chartColors.orange} strokeWidth={2.5} dot={{ r: 2 }} />
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="border-slate-800/80 bg-slate-900/60">
              <CardHeader>
                <CardTitle>Live Client Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {devicesState.length === 0 ? (
                  <div className="rounded-md border border-slate-700/70 bg-slate-900/50 px-3 py-2 text-slate-400">
                    No real edge devices have reported status yet.
                  </div>
                ) : devicesState.map((device) => (
                  <div key={device.id} className="grid grid-cols-6 rounded-md border border-slate-700/70 bg-slate-900/50 px-3 py-2 text-slate-200">
                    <span className="font-medium">{device.id}</span>
                    <span className={device.status === "Online" ? "text-lime-300" : "text-rose-300"}>{device.status}</span>
                    <span>CPU {device.cpu}%</span>
                    <span>RAM {device.ram}%</span>
                    <span className="text-amber-300">{device.mode}</span>
                    <span>{device.latestClassification ?? "--"} {device.latestConfidence ? `(${(device.latestConfidence * 100).toFixed(0)}%)` : ""}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
            <EventStreamCard eventStream={eventStreamState} />
          </div>
        </div>
      );
    }

    if (activeTab === "Live Devices") {
      return (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <StatCard title="Online Clients" value={onlineDevices.toString()} />
            <StatCard title="Avg CPU Load" value={`${avgCpuLoad}%`} />
            <StatCard title="Avg RAM Load" value={`${avgRamLoad}%`} />
          </div>
          <div className="grid gap-4 xl:grid-cols-3">
            <Card className="border-slate-800/80 bg-slate-900/60 xl:col-span-2">
              <CardHeader>
                <CardTitle>Live Devices</CardTitle>
                <CardDescription>Real-time status for each Arduino UNO Q</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 xl:grid-cols-2">
                {devicesState.length === 0 ? (
                  <div className="rounded-xl border border-slate-700/70 bg-slate-900/50 p-4 text-sm text-slate-400">
                    No real edge devices have reported status yet. Run the edge simulator to populate this view.
                  </div>
                ) : devicesState.map((d) => (
                  <div key={d.id} className="rounded-xl border border-slate-700/70 bg-slate-900/50 p-4">
                    <div className="mb-3 flex items-center justify-between">
                      <p className="font-semibold">{d.id}</p>
                      <Badge variant={d.status === "Online" ? "success" : "destructive"}>{d.status}</Badge>
                    </div>
                    <div className="space-y-2 text-sm">
                      <p>CPU: {d.cpu}%</p>
                      <Progress value={d.cpu} />
                      <p>RAM: {d.ram}%</p>
                      <Progress value={d.ram} />
                      <p>Temp: {d.temp}</p>
                      <p>Heartbeat: {d.heartbeat}</p>
                      <p>Mode: {d.mode}</p>
                      <p>Latest classification: {d.latestClassification ?? "--"}</p>
                      <p>Confidence: {d.latestConfidence !== null && d.latestConfidence !== undefined ? `${(d.latestConfidence * 100).toFixed(1)}%` : "--"}</p>
                      <p>Last update: {formatTimestamp(d.lastSeen)}</p>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
            <Card className="border-slate-800/80 bg-slate-900/60">
              <CardHeader>
                <CardTitle>Device Health Mix</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="h-44">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={[
                          { name: "Healthy", value: onlineDevices, color: "#4ade80" },
                          { name: "Offline", value: totalDevices - onlineDevices, color: "#fb7185" },
                        ]}
                        dataKey="value"
                        nameKey="name"
                        outerRadius={70}
                      >
                        <Cell fill="#4ade80" />
                        <Cell fill="#fb7185" />
                      </Pie>
                      <Tooltip contentStyle={tooltipStyle} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 p-3 text-sm text-slate-300">
                  Thermal alert threshold: <b className="text-amber-300">65°C</b><br />
                  Packet timeout: <b className="text-amber-300">1200 ms</b>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      );
    }

    if (activeTab === "Federated Rounds") {
      return (
        <div className="space-y-4">
          <GrpcManagedNotice scope="Federated rounds lifecycle, participant counts and aggregation state come from gRPC." />
          <div className="grid gap-4 md:grid-cols-4">
            <StatCard title="Current Round" value={`R${federatedRound}`} />
            <StatCard title="Participants" value={`${federatedPendingUpdates} / ${federatedMinClients}`} />
            <StatCard title="Aggregation" value="FedAvg" />
            <StatCard title="Samples Trained" value={samplesTrained} />
          </div>
          <div className="grid gap-4 xl:grid-cols-2">
          <Card className="border-slate-800/80 bg-slate-900/60">
            <CardHeader>
              <CardTitle>Round Tracker</CardTitle>
              <CardDescription>Rounds observed from real MQTT metric payloads</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {roundSummary.length === 0 ? (
                <WaitingState message="Waiting for metric payloads with round/sample fields." compact />
              ) : roundSummary.map((round) => (
                <div key={round.round} className="rounded-lg border border-slate-700/70 bg-slate-900/50 p-3">
                  Round {round.round}: {round.participants} participant{round.participants === 1 ? "" : "s"} · samples {round.samples || "--"}
                </div>
              ))}
            </CardContent>
          </Card>
          <Card className="border-slate-800/80 bg-slate-900/60">
            <CardHeader>
              <CardTitle>Loss by Round</CardTitle>
            </CardHeader>
            <CardContent className="h-72">
              {lossChartData.length === 0 ? (
                <WaitingState message="Waiting for real loss metrics." />
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={lossChartData}>
                    <CartesianGrid className="chart-grid" strokeDasharray="3 3" />
                    <XAxis className="chart-axis" dataKey="label" />
                    <YAxis className="chart-axis" />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Bar dataKey="localLoss" name="Local loss" fill={chartColors.olive} radius={[6, 6, 0, 0]} />
                    <Bar dataKey="globalLoss" name="Global loss" fill={chartColors.cyan} radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
          </div>
          <div className="grid gap-4 xl:grid-cols-3">
            <Card className="border-slate-800/80 bg-slate-900/60 xl:col-span-2">
              <CardHeader><CardTitle>Coordinator State</CardTitle></CardHeader>
              <CardContent className="grid gap-3 md:grid-cols-4 text-sm">
                <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 p-3"><p className="text-slate-200">Round</p><p className="text-amber-300">R{federatedRound}</p></div>
                <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 p-3"><p className="text-slate-200">Pending updates</p><p className="text-amber-300">{federatedPendingUpdates}</p></div>
                <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 p-3"><p className="text-slate-200">Min clients</p><p className="text-amber-300">{federatedMinClients}</p></div>
                <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 p-3"><p className="text-slate-200">Model</p><p className="text-amber-300">{latestModelVersion}</p></div>
              </CardContent>
            </Card>
            <EventStreamCard eventStream={eventStreamState} />
          </div>
        </div>
      );
    }

    if (activeTab === "Model Performance") {
      return (
        <div className="space-y-4">
          <GrpcManagedNotice scope="Model performance curves and confusion snapshots should be sourced from gRPC metrics." />
          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="border-slate-800/80 bg-slate-900/60">
              <CardHeader><CardTitle>Accuracy Evolution</CardTitle></CardHeader>
              <CardContent className="h-72">
                {accuracyChartData.length === 0 ? (
                  <WaitingState message="Waiting for accuracy metrics from MQTT." />
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={accuracyChartData}>
                      <CartesianGrid className="chart-grid" strokeDasharray="3 3" />
                      <XAxis className="chart-axis" dataKey="label" />
                      <YAxis className="chart-axis" />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Area type="monotone" dataKey="globalAccuracy" name="Global accuracy" stroke={chartColors.tealSoft} fill={chartColors.tealSoft} fillOpacity={0.2} connectNulls />
                      <Area type="monotone" dataKey="localAccuracy" name="Local accuracy" stroke={chartColors.mustard} fill={chartColors.mustard} fillOpacity={0.2} connectNulls />
                    </AreaChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
            <Card className="border-slate-800/80 bg-slate-900/60">
              <CardHeader><CardTitle>Loss Trend</CardTitle></CardHeader>
              <CardContent className="h-72">
                {lossChartData.length === 0 ? (
                  <WaitingState message="Waiting for loss metrics from MQTT." />
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={lossChartData}>
                      <CartesianGrid className="chart-grid" strokeDasharray="3 3" />
                      <XAxis className="chart-axis" dataKey="label" />
                      <YAxis className="chart-axis" />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Bar dataKey="localLoss" name="Local loss" fill={chartColors.orange} radius={[6, 6, 0, 0]} />
                      <Bar dataKey="globalLoss" name="Global loss" fill={chartColors.cyan} radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
          </div>
          <div className="grid gap-4 xl:grid-cols-3">
            <Card className="border-slate-800/80 bg-slate-900/60">
              <CardHeader><CardTitle>Global Accuracy</CardTitle></CardHeader>
              <CardContent className="space-y-2">
                <p className="text-3xl font-semibold text-slate-100">{globalAccuracy}</p>
                <p className="text-sm text-slate-400">Latest value from MQTT metrics.</p>
              </CardContent>
            </Card>
            <Card className="border-slate-800/80 bg-slate-900/60 xl:col-span-2">
              <CardHeader><CardTitle>Classification Stream</CardTitle></CardHeader>
              <CardContent className="h-64">
                {classificationsState.length === 0 ? (
                  <WaitingState message="Waiting for classification payloads." />
                ) : (
                  <div className="h-full space-y-1 overflow-y-auto rounded-md border border-slate-700/70 bg-slate-950/70 p-2 font-mono text-xs text-slate-300">
                    {classificationsState.map((line, index) => (
                      <p key={`model-classification-${index}-${line}`} className="border-b border-slate-800/70 py-1 last:border-0">{line}</p>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      );
    }

    if (activeTab === "Network & Privacy") {
      return (
        <div className="space-y-4">
          <GrpcManagedNotice scope="Federated communication/privacy KPIs should be sourced from gRPC coordinator reports." />
          <UnavailablePanel
            title="Network & Privacy Metrics"
            message="No real communication-cost or privacy-budget telemetry is exposed by the backend yet."
          />
        </div>
      );
    }

    if (activeTab === "Data Quality") {
      return (
        <div className="space-y-4">
          <UnavailablePanel
            title="Data Quality"
            message="No real labeled-dataset quality metrics are exposed yet. Classification MQTT payloads are available in Alerts & Logs."
          />
        </div>
      );
    }

    if (activeTab === "Model Registry") {
      return (
        <div className="space-y-4">
          <GrpcManagedNotice scope="Model versions, deployment status and export metadata should be sourced from gRPC." />
          <UnavailablePanel
            title="Model Registry"
            message="The backend exposes the current coordinator model version, but no real model artifact registry is implemented yet."
          />
        </div>
      );
    }

    if (activeTab === "Alerts & Logs") {
      return (
        <div className="grid gap-4 xl:grid-cols-2">
          <Card className="border-slate-800/80 bg-slate-900/60">
            <CardHeader>
              <CardTitle>Alerts & Logs</CardTitle>
              <CardDescription>Errors, dropped clients, failed uploads and incomplete rounds</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {helpRequestsState.length === 0 ? (
                <WaitingState message="No help or escalation requests have been received." compact />
              ) : helpRequestsState.map((line, index) => (
                <div key={`alert-${index}-${line}`} className="flex items-center gap-2 rounded-lg border border-amber-600/40 bg-amber-950/35 p-2 text-amber-300">
                  <AlertTriangle className="h-4 w-4" /> {line}
                </div>
              ))}
            </CardContent>
          </Card>
          <EventStreamCard eventStream={eventStreamState} />
          <Card className="border-slate-800/80 bg-slate-900/60">
            <CardHeader>
              <CardTitle>Live Classifications</CardTitle>
              <CardDescription>Latest classification payloads from MQTT topic</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-64 space-y-1 overflow-y-auto rounded-md border border-slate-700/70 bg-slate-950/70 p-2 font-mono text-xs text-slate-300">
                {classificationsState.length === 0 ? (
                  <p className="py-1 text-slate-500">No classifications received yet.</p>
                ) : (
                  classificationsState.map((line, index) => (
                    <p key={`classification-${index}-${line}`} className="border-b border-slate-800/70 py-1 last:border-0">
                      {line}
                    </p>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
          <Card className="border-slate-800/80 bg-slate-900/60">
            <CardHeader>
              <CardTitle>Help Requests</CardTitle>
              <CardDescription>Latest help/escalation payloads from MQTT topic</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-64 space-y-1 overflow-y-auto rounded-md border border-slate-700/70 bg-slate-950/70 p-2 font-mono text-xs text-slate-300">
                {helpRequestsState.length === 0 ? (
                  <p className="py-1 text-slate-500">No help requests received yet.</p>
                ) : (
                  helpRequestsState.map((line, index) => (
                    <p
                      key={`help-${index}-${line}`}
                      className={`border-b py-1 last:border-0 ${
                        /urgent|error|critical|sos/i.test(line)
                          ? "border-rose-700/70 text-rose-300"
                          : "border-slate-800/70"
                      }`}
                    >
                      {line}
                    </p>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }
  }, [accuracyChartData, activeTab, avgCpuLoad, avgRamLoad, classificationsState, devicesState, driftChartData, eventStreamState, federatedMinClients, federatedModelVersion, federatedPendingUpdates, federatedRound, globalAccuracy, globalLoss, helpRequestsState, lastMessageLabel, latestModelVersion, lossChartData, mqttConnected, onlineDevices, roundSummary, samplesTrained, totalDevices, trainingStateLabel]);

  return (
    <main className="min-h-screen bg-[#080b16] text-slate-200">
      <aside className="fixed left-0 top-0 z-40 h-screen w-[290px] border-r border-slate-800/80 bg-[#070a14]/95 p-6">
        <div className="mb-8 flex items-center gap-3">
          <div className="rounded-lg bg-amber-400/20 p-2 text-amber-300">
            <Network className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm text-slate-400">FL Monitoring</p>
            <h1 className="text-[2.1rem] font-semibold tracking-tight text-slate-100">TrashUQ</h1>
          </div>
        </div>

        <nav className="space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = item.name === activeTab;
            return (
              <button
                key={item.name}
                onClick={() => setActiveTab(item.name)}
                className={`flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-[1.05rem] transition ${
                  active
                    ? "bg-amber-300/90 text-stone-900"
                    : "text-slate-300 hover:bg-slate-800/60"
                }`}
              >
                <Icon className="h-4 w-4" />
                {item.name}
              </button>
            );
          })}
        </nav>
      </aside>

      <section className="p-5 md:p-7 lg:ml-[290px]">
        <div className="mx-auto max-w-[1600px] space-y-6">
          {content}
          <footer className="rounded-lg border border-slate-800/80 bg-slate-900/40 px-4 py-3 text-xs text-slate-400">
            <p>© {new Date().getFullYear()} TrashUQ. All rights reserved.</p>
            <p className="mt-1">Federated learning dashboard for Arduino UNO Q recycling intelligence.</p>
          </footer>
        </div>
      </section>
    </main>
  );
}

function StatCard({ title, value }: { title: string; value: string }) {
  return (
    <Card className="border-slate-800/80 bg-slate-900/60">
      <CardHeader>
        <CardDescription>{title}</CardDescription>
        <CardTitle className="text-2xl text-amber-300">{value}</CardTitle>
      </CardHeader>
    </Card>
  );
}

function GrpcManagedNotice({ scope }: { scope: string }) {
  return (
    <Card className="border-cyan-800/70 bg-cyan-950/20">
      <CardContent className="flex items-center justify-between gap-3 p-3 text-sm text-cyan-100">
        <div>
          <p className="font-medium text-cyan-200">Managed by gRPC</p>
          <p className="text-cyan-100/80">{scope}</p>
        </div>
        <Badge className="bg-cyan-300/90 text-slate-900">gRPC Source</Badge>
      </CardContent>
    </Card>
  );
}

function WaitingState({ message, compact = false }: { message: string; compact?: boolean }) {
  return (
    <div className={`flex h-full items-center justify-center rounded-md border border-slate-700/70 bg-slate-950/50 text-center text-sm text-slate-400 ${compact ? "p-3" : "p-6"}`}>
      {message}
    </div>
  );
}

function UnavailablePanel({ title, message }: { title: string; message: string }) {
  return (
    <Card className="border-slate-800/80 bg-slate-900/60">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>Real backend source not available yet</CardDescription>
      </CardHeader>
      <CardContent>
        <WaitingState message={message} />
      </CardContent>
    </Card>
  );
}

function EventStreamCard({ eventStream = [] }: { eventStream?: string[] }) {
  return (
    <Card className="border-slate-800/80 bg-slate-900/60">
      <CardHeader>
        <CardTitle>Event Stream</CardTitle>
        <CardDescription>Live events from devices and coordinator during training rounds</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-80 space-y-1 overflow-y-auto rounded-md border border-slate-700/70 bg-slate-950/70 p-2 font-mono text-xs text-slate-300">
          {eventStream.length === 0 ? (
            <p className="py-1 text-slate-500">No real MQTT events or logs have been received yet.</p>
          ) : eventStream.map((line, index) => (
            <p key={`${index}-${line}`} className="border-b border-slate-800/70 py-1 last:border-0">
              {line}
            </p>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
