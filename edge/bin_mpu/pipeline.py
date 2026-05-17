"""
Capture & inference pipeline.

Flow (per spec):
  IDLE
    └── PIR_TRIG → CAPTURING
            ├── 5-frame burst → majority vote
            ├── conf >= threshold AND class == bin_class  → open lid, log,        → IDLE
            ├── conf >= threshold AND class != bin_class  → log "wrong bin",      → IDLE
            └── conf <  threshold                          → save image, ask UI   → WAITING_LABEL
                                                                   └── user label  → IDLE
"""
import logging
import threading
import time
from enum import Enum, auto

from .camera import Camera
from .classifier import Classifier
from .config import Config
from .monitor import broadcaster, push_frame, set_trigger_callback
from .mqtt_telemetry import MqttTelemetry
from .sample_store import SampleStore
from .serial_protocol import MCULink

logger = logging.getLogger(__name__)


class BinState(Enum):
    IDLE = auto()
    CAPTURING = auto()
    WAITING_LABEL = auto()


class Pipeline:
    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._camera = Camera(cfg)
        self._classifier = Classifier(cfg.model_path, cfg.labels)
        self._store = SampleStore(cfg.db_path, cfg.image_dir)
        self._mcu = MCULink(cfg)
        self._telemetry: MqttTelemetry | None = MqttTelemetry(cfg) if cfg.mqtt_enabled else None
        self._state = BinState.IDLE
        self._state_lock = threading.Lock()
        self._pending_item: dict | None = None
        self._label_timer: threading.Timer | None = None
        self._finetune_hook = None  # optional Callable[[], None] — set by FL client

    def set_finetune_hook(self, hook) -> None:
        """Pipeline calls this each time a user label is submitted, so the FL
        client can decide whether enough new samples have accumulated to retrain."""
        self._finetune_hook = hook

    def start(self) -> None:
        self._camera.open()
        self._mcu.connect()
        self._mcu.on_event(self._handle_mcu_event)
        set_trigger_callback(lambda: self._handle_mcu_event("PIR_TRIG"))
        if self._telemetry is not None:
            self._telemetry.start()
        # Ensure lid starts closed
        self._mcu.lid_close()
        threading.Thread(target=self._preview_loop, daemon=True).start()
        logger.info(
            "Pipeline started: bin=%s device=%s ui=:%d mqtt=%s fl=%s",
            self._cfg.bin_class,
            self._cfg.device_id,
            self._cfg.http_port,
            self._cfg.mqtt_enabled,
            self._cfg.fl_enabled,
        )

    def stop(self) -> None:
        self._camera.close()
        self._mcu.led_off()
        self._mcu.lid_close()
        self._mcu.disconnect()
        self._store.close()
        if self._telemetry is not None:
            self._telemetry.stop()
        if self._label_timer is not None:
            self._label_timer.cancel()

    def get_pending(self) -> dict | None:
        with self._state_lock:
            return dict(self._pending_item) if self._pending_item is not None else None

    def submit_label(self, sample_id: str, label: str) -> None:
        with self._state_lock:
            if self._state != BinState.WAITING_LABEL:
                logger.warning("submit_label called outside WAITING_LABEL state")
                return
            if self._pending_item is None or self._pending_item["id"] != sample_id:
                logger.warning("submit_label: id mismatch, ignoring")
                return
            if self._label_timer is not None:
                self._label_timer.cancel()
                self._label_timer = None
            self._pending_item = None
            self._state = BinState.IDLE
        # "others" = item doesn't fit any class — kept for the record but
        # tagged so the fine-tuner ignores it (label_src != 'user').
        is_trainable = label in self._cfg.labels
        self._store.relabel(sample_id, label, "user" if is_trainable else "user_other")
        logger.info("User labeled %s as '%s'", sample_id, label)

        if self._telemetry is not None:
            self._telemetry.publish_event(
                "label_received", sample_id=sample_id, label=label, bin_class=self._cfg.bin_class
            )

        # If this label matches the bin, also open the lid as the reward action
        if label == self._cfg.bin_class:
            threading.Thread(target=self._open_then_close_lid, daemon=True).start()

        # Notify FL client only for real training labels
        if is_trainable and self._finetune_hook is not None:
            try:
                self._finetune_hook()
            except Exception:
                logger.exception("Finetune hook failed")

        broadcaster.emit({"type": "state", "state": "IDLE"})

    def inject_labeled_sample(self, frame, label: str) -> str:
        """Bypass capture+UI: persist a pre-labeled frame as a user sample and
        notify the FL hook. Used by the offline label feeder for validation runs.
        """
        if label not in self._cfg.labels:
            raise ValueError(f"label must be one of {self._cfg.labels}, got {label!r}")
        sample_id = self._store.save(frame, label, "user", confidence=1.0)
        if self._telemetry is not None:
            self._telemetry.publish_event(
                "label_received",
                sample_id=sample_id,
                label=label,
                bin_class=self._cfg.bin_class,
                source="inject",
            )
        if self._finetune_hook is not None:
            try:
                self._finetune_hook()
            except Exception:
                logger.exception("Finetune hook failed (inject)")
        return sample_id

    def _preview_loop(self) -> None:
        """Continuously push frames to the monitor MJPEG stream."""
        while True:
            try:
                frame = self._camera.capture_single()
                push_frame(frame)
            except Exception:
                time.sleep(0.1)

    def _handle_mcu_event(self, event: str) -> None:
        if event == "PIR_TRIG":
            with self._state_lock:
                if self._state != BinState.IDLE:
                    return
                self._state = BinState.CAPTURING
            broadcaster.emit({"type": "state", "state": "CAPTURING"})
            threading.Thread(target=self._capture_cycle, daemon=True).start()

    def _open_then_close_lid(self) -> None:
        """Open the lid for `lid_open_duration_s` seconds, then close it."""
        try:
            self._mcu.lid_open()
            if self._telemetry is not None:
                self._telemetry.publish_event("lid_open", duration_s=self._cfg.lid_open_duration_s)
            time.sleep(self._cfg.lid_open_duration_s)
        finally:
            self._mcu.lid_close()
            if self._telemetry is not None:
                self._telemetry.publish_event("lid_close")

    def _capture_cycle(self) -> None:
        try:
            self._mcu.led_on()
            time.sleep(0.05)  # LEDs need ~50ms to reach full brightness

            frames = self._camera.capture_burst()
            for i, frame in enumerate(frames):
                label, conf = self._classifier.predict_frame(frame)
                broadcaster.emit({"type": "vote", "n": i + 1, "label": label, "confidence": conf})
            pred = self._classifier.predict_burst(frames)
            logger.info("Prediction: label=%s conf=%.2f votes=%s", pred.label, pred.confidence, pred.votes)
            broadcaster.emit({
                "type": "result", "label": pred.label,
                "confidence": pred.confidence, "votes": pred.votes,
            })

            best_frame = frames[0]
            self._mcu.led_off()

            if pred.confidence >= self._cfg.confidence_threshold:
                # High confidence
                self._store.save(best_frame, pred.label, "model", pred.confidence)
                if self._telemetry is not None:
                    self._telemetry.publish_classification(pred.label, pred.confidence, pred.votes)

                if pred.label == self._cfg.bin_class:
                    logger.info("Correct bin — opening lid")
                    threading.Thread(target=self._open_then_close_lid, daemon=True).start()
                else:
                    logger.info("Wrong bin: item is '%s', this is '%s' bin",
                                pred.label, self._cfg.bin_class)
                    if self._telemetry is not None:
                        self._telemetry.publish_event(
                            "wrong_bin", item=pred.label, bin_class=self._cfg.bin_class
                        )

                with self._state_lock:
                    self._state = BinState.IDLE
                broadcaster.emit({"type": "state", "state": "IDLE"})

            else:
                # Low confidence → ask the human
                sample_id = self._store.save(
                    best_frame, pred.label, "model_uncertain", pred.confidence
                )
                image_path = str(self._cfg.image_dir / f"{sample_id}.jpg")
                with self._state_lock:
                    self._pending_item = {
                        "id": sample_id,
                        "image_path": image_path,
                        "model_guess": pred.label,
                        "confidence": pred.confidence,
                    }
                    self._state = BinState.WAITING_LABEL
                self._label_timer = threading.Timer(
                    self._cfg.label_timeout_s, self._on_label_timeout
                )
                self._label_timer.start()
                broadcaster.emit({"type": "state", "state": "WAITING_LABEL"})
                if self._telemetry is not None:
                    self._telemetry.publish_help_request(sample_id, pred.label, pred.confidence)
                logger.info("Low confidence (%.2f), awaiting human label", pred.confidence)

        except Exception:
            logger.exception("Capture cycle failed")
            self._mcu.led_off()
            with self._state_lock:
                self._state = BinState.IDLE

    def _on_label_timeout(self) -> None:
        with self._state_lock:
            if self._state == BinState.WAITING_LABEL:
                logger.warning("Label timeout after %.0fs, returning to IDLE", self._cfg.label_timeout_s)
                self._pending_item = None
                self._label_timer = None
                self._state = BinState.IDLE
        broadcaster.emit({"type": "state", "state": "IDLE"})

    def run_forever(self) -> None:
        logger.info("Waiting for PIR trigger...")
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("Shutting down")
        finally:
            self.stop()
