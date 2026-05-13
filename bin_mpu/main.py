"""Entry point — run with: python -m bin_mpu.main --bin-class paper"""
import argparse
import logging
import sys
import threading
from pathlib import Path

import uvicorn

from .config import Config
from .labeling_server import create_app
from .monitor import create_router
from .pipeline import Pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="TrashNet bin MPU daemon")
    parser.add_argument(
        "--bin-class",
        choices=["paper", "cardboard", "glass"],
        required=True,
        help="Material this bin accepts (model also knows 'plastic' = always wrong-bin)",
    )
    parser.add_argument("--device-id", default=None, help="Stable bin id, defaults to <bin-class>-bin-01")
    parser.add_argument("--model", type=Path, default=Path("models/trash_classifier.tflite"))
    parser.add_argument("--serial-port", default="/dev/ttyUSB0")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--http-port", type=int, default=8080)
    parser.add_argument("--mqtt-host", default="bepes-server")
    parser.add_argument("--no-mqtt", action="store_true", help="Disable MQTT telemetry")
    parser.add_argument("--fl", action="store_true", help="Enable on-device fine-tuning + FL client")
    parser.add_argument("--fl-host", default="bepes-server")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )

    cfg = Config(
        bin_class=args.bin_class,
        device_id=args.device_id or f"{args.bin_class}-bin-01",
        model_path=args.model,
        serial_port=args.serial_port,
        camera_index=args.camera_index,
        http_port=args.http_port,
        mqtt_enabled=not args.no_mqtt,
        mqtt_host=args.mqtt_host,
        fl_enabled=args.fl,
        fl_host=args.fl_host,
    )

    pipeline = Pipeline(cfg)
    pipeline.start()

    if cfg.fl_enabled:
        from .finetuner import FineTuner
        from .fl_client import FLClient
        finetuner = FineTuner(cfg)
        fl_client = FLClient(cfg, finetuner, pipeline._telemetry)
        fl_client.start()
        pipeline.set_finetune_hook(fl_client.on_user_label)

    app = create_app(pipeline.get_pending, pipeline.submit_label, cfg.labels)
    app.include_router(create_router())
    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=cfg.http_port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()

    pipeline.run_forever()


if __name__ == "__main__":
    main()
