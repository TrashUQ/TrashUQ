"""
MQTT telemetry client — publishes bin events to the TrashUQ backend.

Topic layout (matches TrashUQ backend `arduino/+/#` subscription):
  arduino/<device_id>/status          periodic heartbeat (cpu/ram/mode/status)
  arduino/<device_id>/classification  every inference result
  arduino/<device_id>/help            low-confidence → human label requested
  arduino/<device_id>/event           lid_open / lid_close / label_received
  arduino/<device_id>/logs            arbitrary log lines
"""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

import paho.mqtt.client as mqtt

from .config import Config

logger = logging.getLogger(__name__)


def _read_cpu_percent() -> int | None:
    """Cheap CPU usage estimator without psutil — sample /proc/stat twice."""
    try:
        with open("/proc/stat") as f:
            parts = f.readline().split()
        idle1 = int(parts[4])
        total1 = sum(int(p) for p in parts[1:])
        time.sleep(0.1)
        with open("/proc/stat") as f:
            parts = f.readline().split()
        idle2 = int(parts[4])
        total2 = sum(int(p) for p in parts[1:])
        idle_delta = idle2 - idle1
        total_delta = total2 - total1
        if total_delta <= 0:
            return None
        return int(round(100 * (1 - idle_delta / total_delta)))
    except Exception:
        return None


def _read_ram_percent() -> int | None:
    try:
        info: dict[str, int] = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, _, rest = line.partition(":")
                info[k.strip()] = int(rest.strip().split()[0])
        total = info.get("MemTotal")
        avail = info.get("MemAvailable")
        if total and avail:
            return int(round(100 * (1 - avail / total)))
    except Exception:
        return None
    return None


class MqttTelemetry:
    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._root = f"{cfg.mqtt_topic_root}/{cfg.device_id}"
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cfg.device_id)
        if cfg.mqtt_username:
            self._client.username_pw_set(cfg.mqtt_username, cfg.mqtt_password)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._connected = threading.Event()
        self._stop = threading.Event()

    def start(self) -> None:
        try:
            self._client.connect_async(self._cfg.mqtt_host, self._cfg.mqtt_port, keepalive=60)
            self._client.loop_start()
            threading.Thread(target=self._heartbeat_loop, daemon=True).start()
            logger.info("MQTT telemetry → %s:%d topic=%s", self._cfg.mqtt_host, self._cfg.mqtt_port, self._root)
        except Exception:
            logger.exception("MQTT start failed (telemetry disabled)")

    def stop(self) -> None:
        self._stop.set()
        try:
            self.publish_status({"status": "offline"})
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:
            pass

    # ── topic helpers ────────────────────────────────────────────────────────
    def publish_status(self, patch: dict[str, Any]) -> None:
        payload = {"device_id": self._cfg.device_id, **patch}
        self._publish("status", payload)

    def publish_classification(self, label: str, confidence: float, votes: dict[str, int]) -> None:
        self._publish("classification", {
            "device_id": self._cfg.device_id,
            "bin_class": self._cfg.bin_class,
            "label": label,
            "confidence": confidence,
            "votes": votes,
            "correct_bin": label == self._cfg.bin_class,
            "timestamp": int(time.time() * 1000),
        })

    def publish_metrics(
        self,
        local_loss: float,
        local_accuracy: float,
        global_loss: float | None = None,
        global_accuracy: float | None = None,
        online_clients: int = 1,
        round_number: int | None = None,
        model_version: int | None = None,
    ) -> None:
        """Publish an FL training round's metrics for the dashboard charts."""
        # For a single-bin deployment the aggregated global == local.
        gl = global_loss if global_loss is not None else local_loss
        ga = global_accuracy if global_accuracy is not None else local_accuracy
        self._publish("metrics", {
            "device_id": self._cfg.device_id,
            "localLoss": local_loss,
            "localAccuracy": local_accuracy,
            "loss": local_loss,
            "accuracy": local_accuracy,
            "globalLoss": gl,
            "globalAccuracy": ga,
            "onlineClients": online_clients,
            "round": round_number,
            "modelVersion": model_version,
            "timestamp": int(time.time() * 1000),
        })

    def publish_help_request(self, sample_id: str, model_guess: str, confidence: float) -> None:
        self._publish("help", {
            "device_id": self._cfg.device_id,
            "sample_id": sample_id,
            "model_guess": model_guess,
            "confidence": confidence,
            "reason": "low_confidence",
            "timestamp": int(time.time() * 1000),
        })

    def publish_event(self, name: str, **fields: Any) -> None:
        self._publish("event", {
            "device_id": self._cfg.device_id,
            "name": name,
            "timestamp": int(time.time() * 1000),
            **fields,
        })

    def publish_logs(self, message: str, level: str = "info") -> None:
        self._publish("logs", {
            "device_id": self._cfg.device_id,
            "level": level,
            "message": message,
            "timestamp": int(time.time() * 1000),
        })

    # ── internals ────────────────────────────────────────────────────────────
    def _publish(self, kind: str, payload: dict[str, Any]) -> None:
        topic = f"{self._root}/{kind}"
        try:
            self._client.publish(topic, json.dumps(payload), qos=0, retain=False)
        except Exception:
            logger.debug("MQTT publish failed on %s", topic, exc_info=True)

    def _on_connect(self, _c, _u, _f, reason_code, _p) -> None:
        if reason_code == 0:
            self._connected.set()
            self.publish_status({"status": "online", "mode": "inference", "heartbeat": "ok"})
            logger.info("MQTT connected")
        else:
            logger.warning("MQTT connect failed: %s", reason_code)

    def _on_disconnect(self, _c, _u, _f, reason_code, _p) -> None:
        self._connected.clear()
        logger.warning("MQTT disconnected: %s", reason_code)

    def _heartbeat_loop(self) -> None:
        while not self._stop.wait(self._cfg.heartbeat_interval_s):
            patch: dict[str, Any] = {"status": "online", "heartbeat": "ok"}
            cpu = _read_cpu_percent()
            ram = _read_ram_percent()
            if cpu is not None:
                patch["cpu"] = cpu
            if ram is not None:
                patch["ram"] = ram
            self.publish_status(patch)
