"""
MQTT publish/receive roundtrip benchmark.

Subscribes to its own topic and measures publish-to-receive latency through the
broker. Useful for sanity-checking the bin → bepes-server link and gauging
how fast a `classification` or `help` event reaches the backend's ingest loop.

Usage:
  python -m benchmarks.bench_mqtt --host bepes-server --iterations 200
"""
from __future__ import annotations

import argparse
import json
import threading
import time
from pathlib import Path

import paho.mqtt.client as mqtt

from ._common import banner, stats_of, write_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--topic", default="arduino/bench-bin-01/classification")
    parser.add_argument("--username", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--qos", type=int, default=0)
    parser.add_argument("--report", default="benchmarks/results/mqtt.json")
    args = parser.parse_args()

    banner(f"MQTT roundtrip → {args.host}:{args.port} topic={args.topic} qos={args.qos}")

    arrivals: dict[int, float] = {}
    arrived = threading.Event()
    expected_seq = -1

    def on_connect(client, _u, _f, rc, _p):
        print(f"  on_connect rc={rc}")
        client.subscribe(args.topic, qos=args.qos)

    def on_message(_c, _u, msg):
        nonlocal expected_seq
        try:
            payload = json.loads(msg.payload)
            seq = int(payload["seq"])
            arrivals[seq] = time.perf_counter()
            if seq == expected_seq:
                arrived.set()
        except Exception:
            pass

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="bench-mqtt-01")
    if args.username:
        client.username_pw_set(args.username, args.password)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(args.host, args.port, 30)
    except Exception as exc:
        raise SystemExit(f"FATAL: MQTT connect failed: {exc}")
    client.loop_start()

    # Wait until subscribed (give broker a moment)
    time.sleep(0.5)

    print(f"Publishing {args.iterations} messages…")
    samples_ms: list[float] = []
    for seq in range(args.iterations):
        expected_seq = seq
        arrived.clear()
        payload = json.dumps({"seq": seq, "ts_ms": int(time.time() * 1000)})
        t0 = time.perf_counter()
        client.publish(args.topic, payload, qos=args.qos)
        if not arrived.wait(timeout=5.0):
            print(f"  WARN: seq={seq} not received within 5s")
            continue
        rt = (time.perf_counter() - t0) * 1000
        samples_ms.append(rt)

    s = stats_of(f"mqtt publish→receive qos={args.qos}", samples_ms)
    banner("Results")
    print(s.pretty())
    print(f"\nDelivered: {len(samples_ms)}/{args.iterations}")

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    write_report(args.report, [s], meta={
        "host": args.host, "port": args.port, "qos": args.qos,
        "delivered": len(samples_ms), "attempted": args.iterations,
    })
    print(f"\n→ Saved report: {args.report}")

    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
