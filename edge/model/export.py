"""
Convert the trained SavedModel to TFLite.

Produces two artefacts in output/:
  trash_classifier.tflite          — float32, suitable for on-device fine-tuning (FL)
  trash_classifier_quant.tflite    — int8 quantized, smallest/fastest for inference-only

The float32 model is what the MPU bins load for Phase 1 inference and eventual FL fine-tuning.
The quantized model is optional — useful if you need faster inference without FL.
"""
import numpy as np
import tensorflow as tf

from config import CLASSES, IMG_SIZE, OUTPUT_DIR, TRASHBOX_DIR, TRASHNET_DIR


def _representative_dataset():
    """Yield a handful of real images for int8 calibration."""
    count = 0
    for cls in CLASSES:
        for root in (TRASHNET_DIR, TRASHBOX_DIR):
            folder = root / cls
            if not folder.exists():
                continue
            for img_path in list(folder.iterdir())[:10]:
                if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                    continue
                raw = tf.io.read_file(str(img_path))
                img = tf.image.decode_image(raw, channels=3, expand_animations=False)
                img = tf.image.resize(img, [IMG_SIZE, IMG_SIZE])
                img = tf.keras.applications.mobilenet_v2.preprocess_input(img)
                yield [img[tf.newaxis, ...]]  # shape: (1, 224, 224, 3)
                count += 1
                if count >= 100:
                    return


def export_float32(saved_model_path: str, output_path: str) -> None:
    converter = tf.lite.TFLiteConverter.from_saved_model(saved_model_path)
    tflite_model = converter.convert()
    with open(output_path, "wb") as f:
        f.write(tflite_model)
    size_kb = len(tflite_model) / 1024
    print(f"  float32 → {output_path}  ({size_kb:.0f} KB)")


def export_int8(saved_model_path: str, output_path: str) -> None:
    converter = tf.lite.TFLiteConverter.from_saved_model(saved_model_path)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = _representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.float32   # keep float I/O for easy integration
    converter.inference_output_type = tf.float32
    tflite_model = converter.convert()
    with open(output_path, "wb") as f:
        f.write(tflite_model)
    size_kb = len(tflite_model) / 1024
    print(f"  int8 quant → {output_path}  ({size_kb:.0f} KB)")


def smoke_test(tflite_path: str) -> None:
    """Run one random input through the model to verify it loads."""
    interp = tf.lite.Interpreter(model_path=tflite_path)
    interp.allocate_tensors()
    inp = interp.get_input_details()[0]
    out = interp.get_output_details()[0]
    dummy = np.random.uniform(-1, 1, inp["shape"]).astype(np.float32)
    interp.set_tensor(inp["index"], dummy)
    interp.invoke()
    probs = interp.get_tensor(out["index"])[0]
    pred = CLASSES[int(np.argmax(probs))]
    print(f"  smoke test OK — dummy input → '{pred}' ({probs.max():.3f})")


def main() -> None:
    saved_model_path = str(OUTPUT_DIR / "saved_model")
    float32_path = str(OUTPUT_DIR / "trash_classifier.tflite")
    quant_path = str(OUTPUT_DIR / "trash_classifier_quant.tflite")

    print(f"Loading SavedModel from {saved_model_path} …")

    print("\nExporting float32 (for inference + FL fine-tuning) …")
    export_float32(saved_model_path, float32_path)
    smoke_test(float32_path)

    print("\nExporting int8 quantized (inference-only, smallest size) …")
    export_int8(saved_model_path, quant_path)
    smoke_test(quant_path)

    print(f"\nClasses order: {CLASSES}")
    print("Copy trash_classifier.tflite to the bin MPU under models/")


if __name__ == "__main__":
    main()
