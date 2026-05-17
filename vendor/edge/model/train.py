"""
Transfer-learning training pipeline — MobileNetV2 → 4-class trash classifier.

Two-phase training:
  Phase 1: freeze MobileNetV2 base, train classification head only.
  Phase 2: unfreeze top layers of base and fine-tune end-to-end at low LR.

The resulting SavedModel is written to output/saved_model/.
Run export.py afterwards to convert to TFLite.
"""
import argparse

import tensorflow as tf

from config import (
    CLASSES,
    FINETUNE_EPOCHS,
    FINETUNE_LR,
    FINETUNE_UNFREEZE_FROM,
    HEAD_EPOCHS,
    HEAD_LR,
    IMG_SIZE,
    OUTPUT_DIR,
    TEST_SPLIT,
    VAL_SPLIT,
)
from dataset import load_datasets


def build_model(num_classes: int) -> tf.keras.Model:
    base = tf.keras.applications.MobileNetV2(
        input_shape=(IMG_SIZE, IMG_SIZE, 3),
        include_top=False,
        weights="imagenet",
    )
    base.trainable = False

    inputs = tf.keras.Input(shape=(IMG_SIZE, IMG_SIZE, 3))
    x = base(inputs, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    x = tf.keras.layers.Dense(128, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.2)(x)
    outputs = tf.keras.layers.Dense(num_classes, activation="softmax", name="predictions")(x)

    return tf.keras.Model(inputs, outputs)


def compile_model(model: tf.keras.Model, lr: float) -> None:
    model.compile(
        optimizer=tf.keras.optimizers.Adam(lr),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )


def train(args: argparse.Namespace) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ckpt_path = str(OUTPUT_DIR / "best_model.keras")

    print("\n=== Loading datasets ===")
    train_ds, val_ds, test_ds = load_datasets(VAL_SPLIT, TEST_SPLIT)

    print("\n=== Phase 1: training head (base frozen) ===")
    model = build_model(len(CLASSES))
    compile_model(model, HEAD_LR)
    model.summary(line_length=100)

    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            ckpt_path, save_best_only=True, monitor="val_accuracy", verbose=1
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy", patience=4, restore_best_weights=True
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=2, min_lr=1e-7, verbose=1
        ),
    ]

    model.fit(
        train_ds,
        epochs=HEAD_EPOCHS,
        validation_data=val_ds,
        callbacks=callbacks,
    )

    if not args.head_only:
        print(f"\n=== Phase 2: fine-tuning from layer {FINETUNE_UNFREEZE_FROM} ===")
        # Reload best checkpoint before fine-tuning
        model = tf.keras.models.load_model(ckpt_path)
        base = model.layers[1]  # MobileNetV2 is layer index 1
        base.trainable = True
        for layer in base.layers[:FINETUNE_UNFREEZE_FROM]:
            layer.trainable = False

        compile_model(model, FINETUNE_LR)
        model.fit(
            train_ds,
            epochs=FINETUNE_EPOCHS,
            validation_data=val_ds,
            callbacks=callbacks,
        )

    print("\n=== Evaluation on test set ===")
    model = tf.keras.models.load_model(ckpt_path)
    loss, acc = model.evaluate(test_ds)
    print(f"Test loss: {loss:.4f}  |  Test accuracy: {acc:.4f}")

    saved_model_path = str(OUTPUT_DIR / "saved_model")
    print(f"\nSaving SavedModel → {saved_model_path}")
    model.export(saved_model_path)
    print("Done. Run `python export.py` to convert to TFLite.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train trash classifier")
    parser.add_argument(
        "--head-only",
        action="store_true",
        help="Run Phase 1 only (skip fine-tuning). Faster for quick checks.",
    )
    train(parser.parse_args())
