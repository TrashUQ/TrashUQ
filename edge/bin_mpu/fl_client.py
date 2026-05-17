"""
Federated-learning gRPC client.

Lifecycle:
  start()              → Join coordinator, fetch initial global weights
  schedule_round()     → called from the pipeline whenever a new user label arrives.
                         When `fl_trigger_user_samples` is reached, run a fine-tune
                         round in a background thread.
  stop()               → close gRPC channel

Server contract is defined in `fl.proto` (shared with the TrashUQ backend).
"""
from __future__ import annotations

import logging
import threading

import grpc

from . import fl_pb2, fl_pb2_grpc
from .config import Config
from .finetuner import FineTuner
from .mqtt_telemetry import MqttTelemetry

logger = logging.getLogger(__name__)


class FLClient:
    def __init__(
        self,
        cfg: Config,
        finetuner: FineTuner,
        telemetry: MqttTelemetry | None = None,
    ) -> None:
        self._cfg = cfg
        self._finetuner = finetuner
        self._telemetry = telemetry
        self._channel: grpc.Channel | None = None
        self._stub: fl_pb2_grpc.FederatedLearningServiceStub | None = None
        self._current_round = 1
        self._model_version = 0
        self._busy = threading.Lock()
        self._samples_since_last_round = 0
        self._samples_lock = threading.Lock()

    def start(self) -> None:
        target = f"{self._cfg.fl_host}:{self._cfg.fl_port}"
        logger.info("FL client → %s (client_id=%s)", target, self._cfg.device_id)
        self._channel = grpc.insecure_channel(target)
        self._stub = fl_pb2_grpc.FederatedLearningServiceStub(self._channel)
        try:
            resp = self._stub.Join(fl_pb2.JoinRequest(client_id=self._cfg.device_id), timeout=10.0)
            if resp.ok:
                self._current_round = resp.round
                self._model_version = resp.model_version
                logger.info(
                    "FL join: round=%d version=%d global_weights=%d",
                    resp.round, resp.model_version, len(resp.global_weights),
                )
                if resp.global_weights:
                    self._finetuner.apply_global_weights(list(resp.global_weights))
            else:
                logger.warning("FL join refused: %s", resp.message)
        except grpc.RpcError as exc:
            logger.warning("FL join failed (will retry on next round): %s", exc.code() if hasattr(exc, "code") else exc)

    def stop(self) -> None:
        if self._channel is not None:
            self._channel.close()

    def on_user_label(self) -> None:
        """Called by the pipeline each time a user label is submitted."""
        with self._samples_lock:
            self._samples_since_last_round += 1
            if self._samples_since_last_round < self._cfg.fl_trigger_user_samples:
                return
            self._samples_since_last_round = 0
        threading.Thread(target=self._run_round_safe, daemon=True).start()

    def _run_round_safe(self) -> None:
        if not self._busy.acquire(blocking=False):
            logger.info("FL round already in progress, skipping")
            return
        try:
            self._run_round()
        except Exception:
            logger.exception("FL round failed")
        finally:
            self._busy.release()

    def _run_round(self) -> None:
        if self._stub is None:
            logger.warning("FL stub not ready, skipping round")
            return

        # Re-fetch latest global weights before training
        try:
            resp = self._stub.GetGlobalModel(
                fl_pb2.GetGlobalModelRequest(client_id=self._cfg.device_id), timeout=10.0
            )
            self._current_round = resp.round
            self._model_version = resp.model_version
            if resp.global_weights:
                self._finetuner.apply_global_weights(list(resp.global_weights))
        except grpc.RpcError as exc:
            logger.warning("GetGlobalModel failed: %s", exc)
            return

        # Train locally
        result = self._finetuner.run_round()
        if result is None:
            return

        if self._telemetry is not None:
            self._telemetry.publish_event(
                "fl_round_local_done",
                round=self._current_round,
                num_samples=result["num_samples"],
                local_loss=result["local_loss"],
                local_accuracy=result["local_accuracy"],
            )
            # Feeds the dashboard's loss/accuracy charts
            self._telemetry.publish_metrics(
                local_loss=result["local_loss"],
                local_accuracy=result["local_accuracy"],
                online_clients=1,
                round_number=self._current_round,
                model_version=self._model_version,
            )

        # Submit
        try:
            sub = self._stub.SubmitUpdate(
                fl_pb2.SubmitUpdateRequest(
                    client_id=self._cfg.device_id,
                    round=self._current_round,
                    num_samples=result["num_samples"],
                    local_weights=result["local_weights"],
                    local_loss=result["local_loss"],
                    local_accuracy=result["local_accuracy"],
                ),
                timeout=30.0,
            )
            logger.info(
                "FL submit: ok=%s aggregated=%s round=%d version=%d msg=%s",
                sub.ok, sub.round_aggregated, sub.current_round, sub.model_version, sub.message,
            )
            self._current_round = sub.current_round
            self._model_version = sub.model_version
            if self._telemetry is not None:
                self._telemetry.publish_event(
                    "fl_round_submitted",
                    round=sub.current_round,
                    model_version=sub.model_version,
                    aggregated=bool(sub.round_aggregated),
                )
        except grpc.RpcError as exc:
            logger.warning("SubmitUpdate failed: %s", exc)
