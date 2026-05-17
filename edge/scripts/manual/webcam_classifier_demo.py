"""
Webcam test for the trash classifier TFLite model.

Uses the same 5-frame majority-vote logic as the bin MPU pipeline.
Runs on Mac with tensorflow (not tflite-runtime) — swap the import on the MPU.

Usage:
    uv run python scripts/manual/webcam_classifier_demo.py
    uv run python scripts/manual/webcam_classifier_demo.py --model models/trash_classifier_quant.tflite
    uv run python scripts/manual/webcam_classifier_demo.py --camera 1   # if built-in cam is index 0
"""
import argparse
import collections
import time
from pathlib import Path

import cv2
import numpy as np

# On Mac we use the full TF lite interpreter.
# On the MPU (tflite-runtime) swap this import:
#   from tflite_runtime.interpreter import Interpreter
import tensorflow as tf

CLASSES = ["cardboard", "glass", "paper", "plastic"]
IMG_SIZE = 224
VOTE_FRAMES = 5          # frames captured per inference cycle
CAPTURE_INTERVAL = 0.2   # seconds between frames (matches MPU spec)
CONFIDENCE_THRESHOLD = 0.8

CLASS_COLORS = {
    "cardboard": (0, 165, 255),   # orange
    "glass":     (255, 200, 0),   # cyan-ish
    "paper":     (255, 255, 255), # white
    "plastic":   (0, 255, 120),   # green
}


def load_interpreter(model_path: str) -> tf.lite.Interpreter:
    interp = tf.lite.Interpreter(model_path=model_path)
    interp.allocate_tensors()
    return interp


def preprocess(frame: np.ndarray) -> np.ndarray:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (IMG_SIZE, IMG_SIZE))
    tensor = resized.astype(np.float32)
    # MobileNetV2 preprocess: scale to [-1, 1]
    tensor = (tensor / 127.5) - 1.0
    return np.expand_dims(tensor, axis=0)


def predict(interp: tf.lite.Interpreter, frame: np.ndarray) -> tuple[str, float]:
    inp = interp.get_input_details()[0]
    out = interp.get_output_details()[0]
    interp.set_tensor(inp["index"], preprocess(frame))
    interp.invoke()
    probs = interp.get_tensor(out["index"])[0]
    idx = int(np.argmax(probs))
    return CLASSES[idx], float(probs[idx])


def majority_vote(votes: list[str]) -> str:
    return collections.Counter(votes).most_common(1)[0][0]


def draw_overlay(
    frame: np.ndarray,
    label: str,
    confidence: float,
    capturing: bool,
    progress: int,
) -> np.ndarray:
    h, w = frame.shape[:2]
    overlay = frame.copy()

    # Capture zone rectangle
    margin = 60
    color = (0, 255, 0) if capturing else (100, 100, 100)
    cv2.rectangle(overlay, (margin, margin), (w - margin, h - margin), color, 2)

    if capturing:
        bar_w = int((w - 2 * margin) * (progress / VOTE_FRAMES))
        cv2.rectangle(overlay, (margin, h - margin - 12),
                      (margin + bar_w, h - margin), (0, 255, 0), -1)

    if label:
        cls_color = CLASS_COLORS.get(label, (255, 255, 255))
        cv2.rectangle(overlay, (0, h - 60), (w, h), (30, 30, 30), -1)
        text = f"{label.upper()}  {confidence:.0%}"
        cv2.putText(overlay, text, (16, h - 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, cls_color, 2)

    cv2.putText(overlay, "SPACE: classify   Q: quit", (10, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

    return overlay


def run(model_path: str, camera_index: int) -> None:
    print(f"Loading model: {model_path}")
    interp = load_interpreter(model_path)

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera {camera_index}")

    print("Camera open. Press SPACE to classify, Q to quit.")

    label = ""
    confidence = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

        if key == ord(" "):
            # Capture VOTE_FRAMES frames and take majority vote
            votes: list[str] = []
            confs: list[float] = []
            for i in range(VOTE_FRAMES):
                ret, frame = cap.read()
                if not ret:
                    break
                pred, conf = predict(interp, frame)
                votes.append(pred)
                confs.append(conf)
                display = draw_overlay(frame, "", 0.0, capturing=True, progress=i + 1)
                cv2.imshow("TrashNet classifier", display)
                cv2.waitKey(1)
                time.sleep(CAPTURE_INTERVAL)

            label = majority_vote(votes)
            confidence = float(np.mean([c for v, c in zip(votes, confs) if v == label]))
            print(f"→ {label.upper()}  ({confidence:.1%} avg confidence)  votes={votes}")

        display = draw_overlay(frame, label, confidence, capturing=False, progress=0)
        cv2.imshow("TrashNet classifier", display)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="models/trash_classifier.tflite")
    parser.add_argument("--camera", type=int, default=0)
    args = parser.parse_args()

    if not Path(args.model).exists():
        raise FileNotFoundError(f"Model not found: {args.model}")

    run(args.model, args.camera)
