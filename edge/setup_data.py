"""
Set up datasets after cloning the repo.

Run once after:
    git clone --recurse-submodules <repo-url>
    python setup_data.py
"""
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
TRASHNET_ZIP = ROOT / "model" / "trashnet" / "data" / "dataset-resized.zip"
TRASHNET_OUT = ROOT / "model" / "trashnet" / "data" / "dataset-resized"


def ensure_submodules() -> None:
    print("Initialising submodules …")
    subprocess.run(
        ["git", "submodule", "update", "--init", "--recursive"],
        cwd=ROOT,
        check=True,
    )
    print("  OK")


def extract_trashnet() -> None:
    if TRASHNET_OUT.exists() and any(TRASHNET_OUT.iterdir()):
        print(f"TrashNet already extracted at {TRASHNET_OUT}, skipping.")
        return
    if not TRASHNET_ZIP.exists():
        print(f"ERROR: zip not found at {TRASHNET_ZIP}", file=sys.stderr)
        print("Make sure the submodule was initialised correctly.", file=sys.stderr)
        sys.exit(1)
    print(f"Extracting {TRASHNET_ZIP} …")
    with zipfile.ZipFile(TRASHNET_ZIP) as zf:
        zf.extractall(TRASHNET_OUT.parent)
    print(f"  Extracted to {TRASHNET_OUT}")


def check_trashbox() -> None:
    trashbox = ROOT / "model" / "TrashBox" / "TrashBox_train_set"
    classes = ["cardboard", "glass", "paper", "plastic"]
    missing = [c for c in classes if not (trashbox / c).exists()]
    if missing:
        print(f"WARNING: TrashBox missing classes: {missing}", file=sys.stderr)
        print("Re-run: git submodule update --init --recursive", file=sys.stderr)
    else:
        counts = {c: len(list((trashbox / c).iterdir())) for c in classes}
        print("TrashBox OK —", " | ".join(f"{c}: {n}" for c, n in counts.items()))


def main() -> None:
    ensure_submodules()
    extract_trashnet()
    check_trashbox()
    print("\nAll data ready. You can now run: python model/train.py")


if __name__ == "__main__":
    main()
