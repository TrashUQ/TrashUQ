"""Runtime configuration — edit per deployment."""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    # Paths
    model_path: Path = Path("models/trash_classifier.tflite")
    db_path: Path = Path("data/samples.db")
    image_dir: Path = Path("data/images")
    # Keras SavedModel used for on-device fine-tuning (only required if FL enabled)
    saved_model_path: Path = Path("model/output/saved_model")

    # Camera
    camera_index: int = 0
    capture_width: int = 1280
    capture_height: int = 720
    capture_fps: int = 30
    # 5 frames at 200ms intervals as per spec
    burst_frames: int = 5
    burst_interval_s: float = 0.2

    # Inference
    # Labels MUST match the trained model's output order (alphabetical from train.py)
    labels: list[str] = field(default_factory=lambda: ["cardboard", "glass", "paper", "plastic"])
    confidence_threshold: float = 0.8

    # Servo lid
    lid_open_duration_s: float = 3.0  # how long lid stays open on correct-bin match

    # Labeling web UI
    http_port: int = 8080
    # Seconds to wait for a human label before giving up and returning to IDLE
    label_timeout_s: float = 120.0

    # Serial (MPU ↔ MCU)
    serial_port: str = "/dev/ttyUSB0"
    serial_baud: int = 115200
    serial_timeout_s: float = 2.0

    # MQTT (telemetry to TrashUQ backend)
    mqtt_enabled: bool = True
    mqtt_host: str = "bepes-server"
    mqtt_port: int = 1883
    mqtt_topic_root: str = "arduino"  # matches TrashUQ backend Settings.mqtt_topic_root
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    heartbeat_interval_s: float = 30.0

    # Federated learning (gRPC to TrashUQ backend)
    fl_enabled: bool = False
    fl_host: str = "bepes-server"
    fl_port: int = 50051
    # Fine-tune trigger: run a fine-tune round after this many new user labels
    fl_trigger_user_samples: int = 10
    fl_epochs: int = 3
    fl_batch_size: int = 8
    fl_learning_rate: float = 1e-4

    # Which material this bin accepts (set at deploy time)
    bin_class: str = "paper"

    # Stable per-bin device id used in MQTT topics + FL client_id
    device_id: str = "paper-bin-01"
