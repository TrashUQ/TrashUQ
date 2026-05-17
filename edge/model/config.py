"""Shared configuration for dataset paths, classes, and hyperparameters."""
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
MODEL_DIR = Path(__file__).parent
TRASHNET_DIR = MODEL_DIR / "trashnet" / "data" / "dataset-resized"
TRASHBOX_DIR = MODEL_DIR / "TrashBox" / "TrashBox_train_set"
OUTPUT_DIR = MODEL_DIR / "output"

# ── Classes ────────────────────────────────────────────────────────────────────
CLASSES = ["cardboard", "glass", "paper", "plastic"]

# ── Image ──────────────────────────────────────────────────────────────────────
IMG_SIZE = 224  # MobileNetV2 expects 224×224

# ── Training ───────────────────────────────────────────────────────────────────
BATCH_SIZE = 16       # CPU-friendly
SEED = 42

# Phase 1: head-only training (base frozen)
HEAD_EPOCHS = 10
HEAD_LR = 1e-3

# Phase 2: fine-tune top layers of MobileNetV2
FINETUNE_EPOCHS = 15
FINETUNE_LR = 1e-5
FINETUNE_UNFREEZE_FROM = 100  # layer index (MobileNetV2 has ~155 layers)

# ── Split ──────────────────────────────────────────────────────────────────────
VAL_SPLIT = 0.15
TEST_SPLIT = 0.15
