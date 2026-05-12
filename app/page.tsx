"use client";

import { useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Brain,
  Camera,
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

type TabKey =
  | "Overview"
  | "Live Devices"
  | "Federated Rounds"
  | "Model Performance"
  | "Network & Privacy"
  | "Image Gallery"
  | "Data Quality"
  | "Model Registry"
  | "Alerts & Logs";

const navItems: { name: TabKey; icon: React.ComponentType<{ className?: string }> }[] = [
  { name: "Overview", icon: Gauge },
  { name: "Live Devices", icon: Server },
  { name: "Federated Rounds", icon: Timer },
  { name: "Model Performance", icon: Brain },
  { name: "Network & Privacy", icon: Shield },
  { name: "Image Gallery", icon: Camera },
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

const devices = [
  { id: "UNO-Q1", cpu: 62, ram: 71, temp: "54°C", heartbeat: "42 ms", mode: "Training", status: "Online" },
  { id: "UNO-Q2", cpu: 47, ram: 55, temp: "49°C", heartbeat: "39 ms", mode: "Idle", status: "Online" },
  { id: "UNO-Q3", cpu: 0, ram: 0, temp: "-", heartbeat: "No signal", mode: "Disconnected", status: "Offline" },
];

const models = [
  ["v1.0.6", "Round 6", "Acc 91.2%", "F1 0.90"],
  ["v1.0.5", "Round 5", "Acc 89.4%", "F1 0.88"],
  ["v1.0.4", "Round 4", "Acc 86.9%", "F1 0.85"],
];

const gallery = [
  ["Can_001.jpg", "Metal Can", "98%", "ok"],
  ["Can_042.jpg", "Plastic", "84%", "debug"],
  ["Can_057.jpg", "Metal Can", "65%", "error"],
  ["Can_093.jpg", "Plastic", "92%", "ok"],
  ["Can_117.jpg", "Metal Can", "89%", "ok"],
  ["Can_141.jpg", "Plastic", "71%", "debug"],
];

const eventStream = [
  "16:31:18 UNO-Q3 · local epoch done · loss 0.103",
  "16:30:59 UNO-Q2 · local epoch done · loss 0.349",
  "16:30:16 UNO-Q1 · local epoch done · loss 0.494",
  "16:30:03 Coordinator · received update from UNO-Q1",
  "16:29:50 Coordinator · received update from UNO-Q2",
  "16:29:38 Coordinator · received update from UNO-Q3",
  "16:29:23 Coordinator · FedAvg aggregation completed",
  "16:29:13 Coordinator · global model v1.0.6 published",
  "16:28:57 UNO-Q1 · download global model v1.0.6",
  "16:28:44 UNO-Q2 · download global model v1.0.6",
  "16:28:30 UNO-Q3 · download global model v1.0.6",
  "16:28:16 Round 6 · participants 3/3 · duration 2m18s",
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

export default function Page() {
  const [activeTab, setActiveTab] = useState<TabKey>("Overview");

  const content = useMemo(() => {
    if (activeTab === "Overview") {
      return (
        <div className="space-y-4">
          <Card className="border-slate-800/80 bg-slate-900/60">
            <CardContent className="flex flex-wrap items-center gap-3 p-4 text-sm text-slate-300">
              <span className="text-xl font-semibold text-slate-100">Federated Live</span>
              <span className="text-slate-400">client-server federated learning on Arduino UNO Q</span>
              <Badge className="bg-yellow-400 text-slate-900">TRAIN</Badge>
              <span>round <b className="text-amber-300">6</b></span>
              <span>active clients <b className="text-lime-300">3/3</b></span>
              <span>samples trained <b className="text-orange-300">1,168</b></span>
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard title="Active Devices" value="2 / 3" />
            <StatCard title="Current Round" value="Round 6" />
            <StatCard title="Global Accuracy" value="91.2%" />
            <StatCard title="Training State" value="Running" />
          </div>

          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 px-3 py-2 text-sm text-slate-300">Round duration: <span className="text-amber-300">2m 18s</span></div>
            <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 px-3 py-2 text-sm text-slate-300">Received updates: <span className="text-lime-300">2 / 3</span></div>
            <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 px-3 py-2 text-sm text-slate-300">Global loss: <span className="text-amber-300">0.32</span></div>
            <div className="rounded-lg border border-slate-700/70 bg-slate-900/50 px-3 py-2 text-sm text-slate-300">Next round ETA: <span className="text-orange-300">00:41</span></div>
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
                <CardTitle>Round 6 Client Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {[
                  { id: "UNO-Q1", status: "Completed", samples: 420, loss: 0.29, upload: "OK" },
                  { id: "UNO-Q2", status: "Completed", samples: 389, loss: 0.35, upload: "OK" },
                  { id: "UNO-Q3", status: "Offline", samples: 0, loss: "-", upload: "Missing" },
                ].map((row) => (
                  <div key={row.id} className="grid grid-cols-5 rounded-md border border-slate-700/70 bg-slate-900/50 px-3 py-2 text-slate-200">
                    <span className="font-medium">{row.id}</span>
                    <span className={row.status === "Completed" ? "text-lime-300" : "text-rose-300"}>{row.status}</span>
                    <span>{row.samples} samples</span>
                    <span>loss {row.loss}</span>
                    <span className={row.upload === "OK" ? "text-amber-300" : "text-amber-300"}>{row.upload}</span>
                  </div>
                ))}
                <div className="rounded-md border border-slate-700/70 bg-slate-900/50 px-3 py-2 text-xs text-slate-400">
                  Coordinator note: aggregation executed with 2 client updates due to UNO-Q3 timeout.
                </div>
              </CardContent>
            </Card>
            <EventStreamCard />
          </div>
        </div>
      );
    }

    if (activeTab === "Live Devices") {
      return (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <StatCard title="Online Clients" value="2 / 3" />
            <StatCard title="Avg CPU Load" value="36.3%" />
            <StatCard title="Avg RAM Load" value="42.0%" />
          </div>
          <div className="grid gap-4 xl:grid-cols-3">
            <Card className="border-slate-800/80 bg-slate-900/60 xl:col-span-2">
              <CardHeader>
                <CardTitle>Live Devices</CardTitle>
                <CardDescription>Real-time status for each Arduino UNO Q</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 xl:grid-cols-2">
                {devices.map((d) => (
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
                          { name: "Healthy", value: 2, color: "#4ade80" },
                          { name: "Offline", value: 1, color: "#fb7185" },
                        ]}
                        dataKey="value"
                        nameKey="name"
                        outerRadius={70}
                      >
                        <Cell fill={chartColors.neonGreen} />
                        <Cell fill={chartColors.rose} />
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
          <div className="grid gap-4 md:grid-cols-4">
            <StatCard title="Current Round" value="R6" />
            <StatCard title="Participants" value="2 / 3" />
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
            <EventStreamCard />
          </div>
        </div>
      );
    }

    if (activeTab === "Model Performance") {
      return (
        <div className="space-y-4">
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

    if (activeTab === "Image Gallery") {
      return (
        <div className="grid gap-4 xl:grid-cols-3">
          <Card className="border-slate-800/80 bg-slate-900/60 xl:col-span-2">
            <CardHeader>
              <CardTitle>Image Gallery</CardTitle>
              <CardDescription>Controlled visual samples, predictions and debug states</CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
              {gallery.map((img) => (
                <div key={img[0]} className="rounded-lg border border-slate-700/70 bg-slate-900/50 p-2 text-xs">
                  <div className="mb-2 flex h-20 items-center justify-center rounded bg-slate-800">Thumbnail</div>
                  <p className="font-medium">{img[0]}</p>
                  <p>Pred: {img[1]}</p>
                  <p>Confidence: {img[2]}</p>
                  <Badge variant={img[3] === "ok" ? "success" : img[3] === "debug" ? "warning" : "destructive"}>{img[3]}</Badge>
                </div>
              ))}
            </CardContent>
          </Card>
          <Card className="border-slate-800/80 bg-slate-900/60">
            <CardHeader><CardTitle>Gallery Stats</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-sm">
              <p>Total thumbnails: <span className="text-amber-300">120</span></p>
              <p>Low confidence (&lt; 80%): <span className="text-amber-300">17</span></p>
              <p>Misclassified: <span className="text-rose-300">9</span></p>
              <p>Debug flagged: <span className="text-orange-300">14</span></p>
            </CardContent>
          </Card>
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
      );
    }

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
        <EventStreamCard />
      </div>
    );
  }, [activeTab]);

  return (
    <main className="min-h-screen bg-[#080b16] text-slate-200">
      <aside className="fixed left-0 top-0 z-40 h-screen w-[290px] border-r border-slate-800/80 bg-[#070a14]/95 p-6">
        <div className="mb-8 flex items-center gap-3">
          <div className="rounded-lg bg-amber-400/20 p-2 text-amber-300">
            <Network className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm text-slate-400">FL Monitoring</p>
            <h1 className="text-[2.1rem] font-semibold tracking-tight text-slate-100">FederatedCans</h1>
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
            <p>© {new Date().getFullYear()} FederatedCans. All rights reserved.</p>
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

function EventStreamCard() {
  return (
    <Card className="border-slate-800/80 bg-slate-900/60">
      <CardHeader>
        <CardTitle>Event Stream</CardTitle>
        <CardDescription>Live events from devices and coordinator during training rounds</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-80 space-y-1 overflow-y-auto rounded-md border border-slate-700/70 bg-slate-950/70 p-2 font-mono text-xs text-slate-300">
          {eventStream.map((line) => (
            <p key={line} className="border-b border-slate-800/70 py-1 last:border-0">
              {line}
            </p>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
