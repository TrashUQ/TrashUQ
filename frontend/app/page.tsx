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

const accuracyData = [
  { round: "R1", global: 72, local: 78 },
  { round: "R2", global: 76, local: 80 },
  { round: "R3", global: 81, local: 83 },
  { round: "R4", global: 85, local: 86 },
  { round: "R5", global: 88, local: 89 },
  { round: "R6", global: 91, local: 90 },
];

const lossData = [
  { round: "R1", loss: 1.8 },
  { round: "R2", loss: 1.2 },
  { round: "R3", loss: 0.9 },
  { round: "R4", loss: 0.65 },
  { round: "R5", loss: 0.43 },
  { round: "R6", loss: 0.32 },
];

const roundTimes = [
  { round: "R1", seconds: 172 },
  { round: "R2", seconds: 156 },
  { round: "R3", seconds: 149 },
  { round: "R4", seconds: 141 },
  { round: "R5", seconds: 124 },
  { round: "R6", seconds: 138 },
];

const disagreementData = [
  { round: 84, local: 3.1, fedavg: 0 },
  { round: 85, local: 4.7, fedavg: 0 },
  { round: 86, local: 2.6, fedavg: 0 },
  { round: 87, local: 2.4, fedavg: 0 },
  { round: 88, local: 4.6, fedavg: 0 },
  { round: 89, local: 5.2, fedavg: 0 },
  { round: 90, local: 3.5, fedavg: 0 },
  { round: 91, local: 3.0, fedavg: 0 },
  { round: 92, local: 5.1, fedavg: 0 },
  { round: 93, local: 6.4, fedavg: 0 },
  { round: 94, local: 4.7, fedavg: 0 },
  { round: 95, local: 3.9, fedavg: 0 },
  { round: 96, local: 3.7, fedavg: 0 },
  { round: 97, local: 4.6, fedavg: 0 },
];

const samplesPerDevice = [
  { name: "UNO-Q1", samples: 420 },
  { name: "UNO-Q2", samples: 389 },
  { name: "UNO-Q3", samples: 214 },
];

const classDistribution = [
  { name: "Plastic", value: 468, color: "#98971a" },
  { name: "Metal", value: 321, color: "#d79921" },
  { name: "Paper", value: 187, color: "#458588" },
  { name: "Glass", value: 121, color: "#d65d0e" },
  { name: "Organic", value: 74, color: "#ff4fd8" },
];

const deviceQuality = [
  { device: "UNO-Q1", clean: 94, noisy: 4, rejected: 2 },
  { device: "UNO-Q2", clean: 90, noisy: 7, rejected: 3 },
  { device: "UNO-Q3", clean: 88, noisy: 8, rejected: 4 },
];

const confusion = [
  { name: "TP", value: 420, color: "#83a598" },
  { name: "TN", value: 380, color: "#98971a" },
  { name: "FP", value: 36, color: "#d79921" },
  { name: "FN", value: 28, color: "#cc241d" },
];

const models = [
  ["v1.0.6", "Round 6", "Acc 91.2%", "F1 0.90"],
  ["v1.0.5", "Round 5", "Acc 89.4%", "F1 0.88"],
  ["v1.0.4", "Round 4", "Acc 86.9%", "F1 0.85"],
];

const communicationTrend = [
  { round: "R1", mb: 3.9 },
  { round: "R2", mb: 3.4 },
  { round: "R3", mb: 3.0 },
  { round: "R4", mb: 2.8 },
  { round: "R5", mb: 2.5 },
  { round: "R6", mb: 2.4 },
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
}

type DeviceStatusPatch = Partial<DeviceStatus>;

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

function parseDeviceStatusPatch(payload: unknown): { patch: DeviceStatusPatch; issues: string[] } {
  if (!isPlainObject(payload)) {
    return { patch: {}, issues: ["payload is not an object"] };
  }

  const patch: DeviceStatusPatch = {};
  const issues: string[] = [];

  if ("cpu" in payload) {
    const cpu = toNumber(payload.cpu);
    if (cpu === null) issues.push("cpu must be numeric");
    else patch.cpu = clampPercent(cpu);
  }

  if ("ram" in payload) {
    const ram = toNumber(payload.ram);
    if (ram === null) issues.push("ram must be numeric");
    else patch.ram = clampPercent(ram);
  }

  if ("temp" in payload) {
    if (typeof payload.temp === "string") patch.temp = payload.temp;
    else issues.push("temp must be string");
  }

  if ("heartbeat" in payload) {
    if (typeof payload.heartbeat === "string") patch.heartbeat = payload.heartbeat;
    else issues.push("heartbeat must be string");
  }

  if ("mode" in payload) {
    if (typeof payload.mode === "string") patch.mode = payload.mode;
    else issues.push("mode must be string");
  }

  if ("status" in payload) {
    if (typeof payload.status === "string") patch.status = payload.status;
    else issues.push("status must be string");
  }

  return { patch, issues };
}

function parseMetricsPatch(payload: unknown): { accuracy?: string; loss?: string; issues: string[] } {
  if (!isPlainObject(payload)) {
    return { issues: ["payload is not an object"] };
  }

  const issues: string[] = [];
  let accuracy: string | undefined;
  let loss: string | undefined;

  if ("globalAccuracy" in payload || "global_accuracy" in payload || "accuracy" in payload) {
    const nextAccuracy = formatPercent(payload.globalAccuracy ?? payload.global_accuracy ?? payload.accuracy);
    if (nextAccuracy) accuracy = nextAccuracy;
    else issues.push("globalAccuracy must be numeric");
  }

  if ("globalLoss" in payload || "global_loss" in payload || "loss" in payload) {
    const nextLoss = toNumber(payload.globalLoss ?? payload.global_loss ?? payload.loss);
    if (nextLoss !== null) loss = nextLoss.toFixed(2);
    else issues.push("globalLoss must be numeric");
  }

  return { accuracy, loss, issues };
}

type DashboardDevice = DeviceStatus;

interface DashboardBootstrapPayload {
  devices: DashboardDevice[];
  metrics: {
    globalAccuracy: number | null;
    globalLoss: number | null;
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
  const [globalAccuracy, setGlobalAccuracy] = useState("--");
  const [globalLoss, setGlobalLoss] = useState("--");
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

      if (snapshot.metrics.globalAccuracy !== null) {
        setGlobalAccuracy(`${snapshot.metrics.globalAccuracy.toFixed(1)}%`);
      }

      if (snapshot.metrics.globalLoss !== null) {
        setGlobalLoss(snapshot.metrics.globalLoss.toFixed(2));
      }
      if (snapshot.federated) {
        setFederatedRound(snapshot.federated.current_round);
        setFederatedModelVersion(snapshot.federated.model_version);
        setFederatedPendingUpdates(snapshot.federated.pending_updates);
        setFederatedMinClients(snapshot.federated.min_clients_per_round);
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
          const { accuracy, loss, issues } = parseMetricsPatch(parsedPayload);

          if (issues.length > 0) {
            setEventStreamState((current) => clampHistory([`Invalid metrics payload: ${issues.join(", ")}`, ...current]));
          }

          if (accuracy) setGlobalAccuracy(accuracy);
          if (loss) setGlobalLoss(loss);

          if (!accuracy && !loss) {
            setEventStreamState((current) => clampHistory([`Metrics payload ignored: no valid fields`, ...current]));
          }
          return;
        }

        if (topicLower.endsWith("/classification")) {
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
  const trainingDevices = devicesState.filter((device) => String(device.mode).toLowerCase() === "training").length;
  const avgCpuLoad = totalDevices
    ? Math.round(devicesState.reduce((sum, device) => sum + (typeof device.cpu === "number" ? device.cpu : 0), 0) / totalDevices)
    : 0;
  const avgRamLoad = totalDevices
    ? Math.round(devicesState.reduce((sum, device) => sum + (typeof device.ram === "number" ? device.ram : 0), 0) / totalDevices)
    : 0;
  const trainingStateLabel = mqttConnected ? (trainingDevices > 0 ? "Running" : "Idle") : "Disconnected";
  const lastMessageLabel = lastMqttMessageAt ? new Date(lastMqttMessageAt).toLocaleTimeString() : "--";

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
              <span>samples trained <b className="text-orange-300">1,168</b></span>
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard title="Active Devices" value={`${onlineDevices} / ${totalDevices}`} />
            <StatCard title="Current Round" value={`R${federatedRound}`} />
            <StatCard title="Global Accuracy" value={globalAccuracy} />
            <StatCard title="Training State" value={trainingStateLabel} />
          </div>

          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 px-3 py-2 text-sm text-slate-300">Model version: <span className="text-amber-300">v{federatedModelVersion}</span></div>
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
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={lossData}>
                    <CartesianGrid className="chart-grid" strokeDasharray="3 3" />
                    <XAxis className="chart-axis" dataKey="round" />
                    <YAxis className="chart-axis" domain={[0, 2]} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Area type="monotone" dataKey="loss" stroke={chartColors.mustard} fill={chartColors.mustard} fillOpacity={0.2} />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card className="border-slate-800/80 bg-slate-900/60">
              <CardHeader>
                <CardTitle>Client Drift vs Aggregated Global Model</CardTitle>
              </CardHeader>
              <CardContent className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={disagreementData}>
                    <CartesianGrid className="chart-grid" strokeDasharray="3 3" />
                    <XAxis className="chart-axis" dataKey="round" />
                    <YAxis className="chart-axis" />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Line type="monotone" dataKey="local" stroke={chartColors.orange} strokeWidth={2.5} dot={{ r: 2 }} />
                    <Line type="monotone" dataKey="fedavg" stroke={chartColors.neonGreen} strokeWidth={2.3} dot={{ r: 2 }} />
                  </LineChart>
                </ResponsiveContainer>
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
                  <div key={device.id} className="grid grid-cols-5 rounded-md border border-slate-700/70 bg-slate-900/50 px-3 py-2 text-slate-200">
                    <span className="font-medium">{device.id}</span>
                    <span className={device.status === "Online" ? "text-lime-300" : "text-rose-300"}>{device.status}</span>
                    <span>CPU {device.cpu}%</span>
                    <span>RAM {device.ram}%</span>
                    <span className="text-amber-300">{device.mode}</span>
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
            <StatCard title="Round Time" value="2m 18s" />
          </div>
          <div className="grid gap-4 xl:grid-cols-2">
          <Card className="border-slate-800/80 bg-slate-900/60">
            <CardHeader>
              <CardTitle>Round Tracker</CardTitle>
              <CardDescription>Participants, weights, training time and aggregation state</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 p-3">Round 6: 2/3 clients, 2 weights, 2m 18s, FedAvg done</div>
              <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 p-3">Round 5: 3/3 clients, 3 weights, 2m 04s, FedAvg done</div>
              <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 p-3">Round 4: 3/3 clients, 3 weights, 2m 21s, FedAvg done</div>
            </CardContent>
          </Card>
          <Card className="border-slate-800/80 bg-slate-900/60">
            <CardHeader>
              <CardTitle>Training Time by Round</CardTitle>
            </CardHeader>
            <CardContent className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={roundTimes}>
                  <CartesianGrid className="chart-grid" strokeDasharray="3 3" />
                  <XAxis className="chart-axis" dataKey="round" />
                  <YAxis className="chart-axis" />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="seconds" fill={chartColors.olive} radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
          </div>
          <div className="grid gap-4 xl:grid-cols-3">
            <Card className="border-slate-800/80 bg-slate-900/60 xl:col-span-2">
              <CardHeader><CardTitle>Round Pipeline Status</CardTitle></CardHeader>
              <CardContent className="grid gap-3 md:grid-cols-4 text-sm">
                {["Local Train", "Upload Weights", "Aggregate", "Broadcast"].map((step, i) => (
                  <div key={step} className="rounded-lg border border-slate-700/70 bg-slate-900/50 p-3">
                    <p className="text-slate-200">{step}</p>
                    <p className={i < 3 ? "text-lime-300" : "text-amber-300"}>{i < 3 ? "Completed" : "In Progress"}</p>
                  </div>
                ))}
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
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={accuracyData}>
                    <CartesianGrid className="chart-grid" strokeDasharray="3 3" />
                    <XAxis className="chart-axis" dataKey="round" />
                    <YAxis className="chart-axis" />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Area type="monotone" dataKey="global" stroke={chartColors.tealSoft} fill={chartColors.tealSoft} fillOpacity={0.2} />
                    <Area type="monotone" dataKey="local" stroke={chartColors.mustard} fill={chartColors.mustard} fillOpacity={0.2} />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card className="border-slate-800/80 bg-slate-900/60">
              <CardHeader><CardTitle>Loss Trend</CardTitle></CardHeader>
              <CardContent className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={lossData}>
                    <CartesianGrid className="chart-grid" strokeDasharray="3 3" />
                    <XAxis className="chart-axis" dataKey="round" />
                    <YAxis className="chart-axis" />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Bar dataKey="loss" fill={chartColors.orange} radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
          <div className="grid gap-4 xl:grid-cols-3">
            <Card className="border-slate-800/80 bg-slate-900/60">
              <CardHeader><CardTitle>F1 Score</CardTitle></CardHeader>
              <CardContent><Progress value={90} /></CardContent>
            </Card>
            <Card className="border-slate-800/80 bg-slate-900/60 xl:col-span-2">
              <CardHeader><CardTitle>Confusion Matrix Snapshot</CardTitle></CardHeader>
              <CardContent className="grid h-64 gap-4 xl:grid-cols-[1fr_220px]">
                <div className="h-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={confusion} dataKey="value" nameKey="name" outerRadius={88}>
                        {confusion.map((e) => <Cell key={e.name} fill={e.color} />)}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 p-3 text-sm">
                  <p className="mb-2 text-xs uppercase tracking-wide text-slate-400">Legend</p>
                  <div className="space-y-2">
                    {confusion.map((e) => (
                      <div key={e.name} className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="h-3 w-3 rounded-full" style={{ backgroundColor: e.color }} />
                          <span className="text-slate-200">{e.name}</span>
                        </div>
                        <span className="text-slate-400">{e.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
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
          <div className="grid gap-4 xl:grid-cols-4">
            <StatCard title="Bytes Sent (R6)" value="2.4 MB" />
            <StatCard title="Reduction vs Centralized" value="78%" />
            <StatCard title="Weights vs Images" value="1 : 14.6" />
            <StatCard title="Compression Ratio" value="4.2x" />
          </div>
          <div className="grid gap-4 xl:grid-cols-3">
            <Card className="border-slate-800/80 bg-slate-900/60 xl:col-span-2">
              <CardHeader><CardTitle>Communication Cost by Round</CardTitle></CardHeader>
              <CardContent className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={communicationTrend}>
                    <CartesianGrid className="chart-grid" strokeDasharray="3 3" />
                    <XAxis className="chart-axis" dataKey="round" />
                    <YAxis className="chart-axis" />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Line type="monotone" dataKey="mb" stroke={chartColors.cyan} strokeWidth={2.5} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card className="border-slate-800/80 bg-slate-900/60">
              <CardHeader><CardTitle>Privacy Mode</CardTitle></CardHeader>
              <CardContent className="space-y-3 text-sm">
                <Badge variant="warning">Secure Aggregation + Differential Privacy</Badge>
                <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 p-3">
                  <p>Noise multiplier: <span className="text-amber-300">0.8</span></p>
                  <p>Clip norm: <span className="text-amber-300">1.2</span></p>
                  <p>Epsilon budget: <span className="text-amber-300">3.6</span></p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      );
    }

    if (activeTab === "Data Quality") {
      return (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <StatCard title="Total Labeled Samples" value="1,171" />
            <StatCard title="Balanced Classes" value="4 / 5" />
            <StatCard title="Noisy Labels" value="6.4%" />
            <StatCard title="Rejected Frames" value="2.9%" />
          </div>
          <div className="grid gap-4 xl:grid-cols-3">
            <Card className="border-slate-800/80 bg-slate-900/60 xl:col-span-2">
              <CardHeader>
                <CardTitle>Samples per Device</CardTitle>
                <CardDescription>contribution by each Arduino UNO Q client</CardDescription>
              </CardHeader>
              <CardContent className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={samplesPerDevice}>
                    <CartesianGrid className="chart-grid" strokeDasharray="3 3" />
                    <XAxis className="chart-axis" dataKey="name" />
                    <YAxis className="chart-axis" />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Bar dataKey="samples" fill={chartColors.olive} radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card className="border-slate-800/80 bg-slate-900/60 xl:row-span-2">
              <CardHeader><CardTitle>Label Quality Snapshot</CardTitle></CardHeader>
              <CardContent className="space-y-3 text-sm">
                <p className="text-slate-300">Consistent labels: <span className="text-lime-300">90.7%</span></p>
                <p className="text-slate-300">Ambiguous labels: <span className="text-amber-300">6.4%</span></p>
                <p className="text-slate-300">Rejected samples: <span className="text-orange-300">2.9%</span></p>
                <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 p-3">
                  Dataset is healthier now; main gap is `Organic`, which remains underrepresented.
                </div>
                <div className="pt-1">
                  <p className="mb-2 text-xs uppercase tracking-wide text-slate-400">Device Label Audit</p>
                  <div className="space-y-2">
                    {deviceQuality.map((d) => (
                      <div key={d.device} className="rounded-lg border border-slate-700/70 bg-slate-900/50 p-2">
                        <p className="font-medium text-slate-200">{d.device}</p>
                        <p>Clean: <span className="text-lime-300">{d.clean}%</span></p>
                        <p>Noisy: <span className="text-amber-300">{d.noisy}%</span></p>
                        <p>Rejected: <span className="text-orange-300">{d.rejected}%</span></p>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="border-slate-800/80 bg-slate-900/60 xl:col-span-2">
              <CardHeader>
                <CardTitle>Class Distribution</CardTitle>
                <CardDescription>training-set balance across waste categories</CardDescription>
              </CardHeader>
              <CardContent className="grid h-72 gap-4 xl:grid-cols-[1fr_220px]">
                <div className="h-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={classDistribution} dataKey="value" nameKey="name" outerRadius={95}>
                      {classDistribution.map((c) => (
                        <Cell key={c.name} fill={c.color} />
                      ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 p-3 text-sm">
                  <p className="mb-2 text-xs uppercase tracking-wide text-slate-400">Legend</p>
                  <div className="space-y-2">
                    {classDistribution.map((c) => (
                      <div key={c.name} className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="h-3 w-3 rounded-full" style={{ backgroundColor: c.color }} />
                          <span className="text-slate-200">{c.name}</span>
                        </div>
                        <span className="text-slate-400">{c.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      );
    }

    if (activeTab === "Model Registry") {
      return (
        <div className="space-y-4">
          <GrpcManagedNotice scope="Model versions, deployment status and export metadata should be sourced from gRPC." />
          <div className="grid gap-4 xl:grid-cols-3">
          <Card className="border-slate-800/80 bg-slate-900/60 xl:col-span-2">
            <CardHeader>
              <CardTitle>Model Registry</CardTitle>
              <CardDescription>Global model history with version per round and metrics</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {models.map((m) => (
                <div key={m[0]} className="flex items-center justify-between rounded-lg border border-slate-700/70 bg-slate-900/50 p-2">
                  <div>
                    <p className="font-medium">{m[0]}</p>
                    <p className="text-muted-foreground">{m[1]} • {m[2]} • {m[3]}</p>
                  </div>
                  <button className="flex items-center gap-1 rounded-md border border-slate-600 px-2 py-1 text-xs hover:bg-secondary">
                    <Download className="h-3.5 w-3.5" /> Download
                  </button>
                </div>
              ))}
            </CardContent>
          </Card>
          <Card className="border-slate-800/80 bg-slate-900/60">
            <CardHeader><CardTitle>Deployment Status</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-sm">
              <p>Current serving model: <span className="text-amber-300">v1.0.6</span></p>
              <p>Rollback candidate: <span className="text-slate-300">v1.0.5</span></p>
              <p>Checksum: <span className="text-lime-300">a8f1...e2b9</span></p>
              <p>Last export: <span className="text-slate-300">2026-05-06 11:29</span></p>
            </CardContent>
          </Card>
        </div>
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
              <div className="flex items-center gap-2 rounded-lg border border-rose-700/50 bg-rose-950/35 p-2 text-rose-300">
                <AlertTriangle className="h-4 w-4" /> UNO-Q4 dropped during Round 6 at 11:21:13
              </div>
              <div className="flex items-center gap-2 rounded-lg border border-amber-600/40 bg-amber-950/35 p-2 text-amber-300">
                <Activity className="h-4 w-4" /> Upload retry triggered for UNO-Q3 weights package
              </div>
              <div className="flex items-center gap-2 rounded-lg border border-cyan-700/40 bg-cyan-950/30 p-2 text-amber-300">
                <Server className="h-4 w-4" /> Aggregation completed with 3/4 participants
              </div>
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
  }, [activeTab, avgCpuLoad, avgRamLoad, classificationsState, eventStreamState, federatedMinClients, federatedModelVersion, federatedPendingUpdates, federatedRound, globalAccuracy, globalLoss, helpRequestsState, lastMessageLabel, mqttConnected, onlineDevices, totalDevices, trainingStateLabel, devicesState]);

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
