"""Feed pre-labeled images from the TrashNet dataset into running bin daemons.

Drives federated-learning rounds without needing the iPad UI or real PIR
captures. Picks N images per class (per bin) at random from
`model/trashnet/data/dataset-resized/<class>/` and POSTs them to each bin's
`POST /api/inject` endpoint.

Usage
-----
    python tools/feed_labels.py \\
        --bin http://192.168.1.40:8080 \\
        --bin http://192.168.1.41:8080 \\
        --per-class 5

With the default `--fl-trigger-samples 2` on each daemon, 5 samples per class
× 4 classes = 20 labels per bin → ~10 FL rounds per bin.

Add `--shuffle-bins` to send different images to each bin so the FL aggregator
sees non-identical updates.
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

import httpx

CLASSES = ["cardboard", "glass", "paper", "plastic"]


def collect_images(dataset_dir: Path, per_class: int, seed: int) -> list[tuple[Path, str]]:
    rng = random.Random(seed)
    chosen: list[tuple[Path, str]] = []
    for cls in CLASSES:
        folder = dataset_dir / cls
        if not folder.is_dir():
            print(f"WARN: missing class folder {folder}", file=sys.stderr)
            continue
        files = sorted(folder.glob("*.jpg")) + sorted(folder.glob("*.png"))
        if len(files) < per_class:
            print(
                f"WARN: only {len(files)} images in {cls}, requested {per_class}",
                file=sys.stderr,
            )
        pick = rng.sample(files, min(per_class, len(files)))
        chosen.extend((p, cls) for p in pick)
    rng.shuffle(chosen)
    return chosen


def send_one(bin_url: str, image: Path, label: str, timeout: float) -> tuple[bool, str]:
    url = bin_url.rstrip("/") + "/api/inject"
    try:
        with image.open("rb") as fh:
            files = {"file": (image.name, fh, "image/jpeg")}
            data = {"label": label}
            r = httpx.post(url, files=files, data=data, timeout=timeout)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}: {r.text[:120]}"
        return True, r.json().get("sample_id", "?")
    except httpx.HTTPError as exc:
        return False, str(exc)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--bin", action="append", required=True,
                    help="Base URL of a bin daemon (repeatable), e.g. http://10.0.0.5:8080")
    ap.add_argument("--dataset", type=Path,
                    default=Path("model/trashnet/data/dataset-resized"),
                    help="Path to TrashNet dataset-resized/ directory")
    ap.add_argument("--per-class", type=int, default=5,
                    help="Images per class per bin (default 5 → 20 labels/bin)")
    ap.add_argument("--delay", type=float, default=0.5,
                    help="Seconds to sleep between POSTs (lets FL rounds breathe)")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--shuffle-bins", action="store_true",
                    help="Use a different random sample per bin (non-IID-ish)")
    args = ap.parse_args()

    if not args.dataset.is_dir():
        print(f"ERROR: dataset not found at {args.dataset}", file=sys.stderr)
        return 2

    for i, bin_url in enumerate(args.bin):
        seed = args.seed + (i if args.shuffle_bins else 0)
        samples = collect_images(args.dataset, args.per_class, seed=seed)
        print(f"\n[{bin_url}] feeding {len(samples)} labeled samples (seed={seed})")
        ok = fail = 0
        for j, (image, label) in enumerate(samples, 1):
            success, info = send_one(bin_url, image, label, args.timeout)
            tag = "OK" if success else "ERR"
            print(f"  {j:3d}/{len(samples)} {tag} {label:<9} {image.name:<20} → {info}")
            if success:
                ok += 1
            else:
                fail += 1
            if args.delay > 0:
                time.sleep(args.delay)
        print(f"[{bin_url}] done: ok={ok} fail={fail}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
