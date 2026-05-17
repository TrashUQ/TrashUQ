#!/usr/bin/env python3
import argparse
import json
import random
import time

import paho.mqtt.client as mqtt


def build_device_payload(device_id: str) -> dict:
    return {
        "cpu": random.randint(5, 95),
        "ram": random.randint(10, 90),
        "temp": f"{random.uniform(25.0, 55.0):.1f}C",
        "heartbeat": "online",
        "mode": random.choice(["train", "idle", "inference"]),
        "status": random.choice(["ok", "warning"]),
        "device_id": device_id,
    }


def publish_json(client: mqtt.Client, topic: str, payload: dict) -> None:
    client.publish(topic, json.dumps(payload), qos=0, retain=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="MQTT mock publisher for TrashUQ")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--topic-root", default="arduino")
    parser.add_argument("--devices", type=int, default=3)
    parser.add_argument("--loops", type=int, default=10)
    parser.add_argument("--sleep", type=float, default=1.0)
    args = parser.parse_args()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(args.host, args.port, 60)
    client.loop_start()

    for i in range(args.loops):
        for d in range(1, args.devices + 1):
            device_id = f"uno-{d}"
            base = f"{args.topic_root}/{device_id}"

            publish_json(client, f"{base}/status", build_device_payload(device_id))

            publish_json(
                client,
                f"{base}/metrics",
                {
                    "globalAccuracy": round(random.uniform(0.65, 0.98), 4),
                    "globalLoss": round(random.uniform(0.1, 1.2), 4),
                    "avgCpu": random.uniform(10, 90),
                    "avgRam": random.uniform(15, 85),
                    "onlineClients": args.devices,
                },
            )

            publish_json(client, f"{base}/event", {"msg": f"event {i} from {device_id}"})
            publish_json(client, f"{base}/classification", {"class": random.choice(["plastic", "paper", "glass"])})
            publish_json(client, f"{base}/help", {"help": random.choice(["none", "bin_full", "sensor_error"])})
            publish_json(client, f"{base}/logs", {"log": f"loop {i} device {device_id}"})

        time.sleep(args.sleep)

    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
