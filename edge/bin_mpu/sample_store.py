"""SQLite-backed local sample queue."""
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS samples (
    id          TEXT PRIMARY KEY,
    captured_at TEXT NOT NULL,
    image_path  TEXT NOT NULL,
    label       TEXT NOT NULL,   -- 'paper', 'carton', 'glass'
    label_src   TEXT NOT NULL,   -- 'model', 'model_uncertain', or 'user'
    confidence  REAL,
    uploaded    INTEGER NOT NULL DEFAULT 0
)
"""


class SampleStore:
    def __init__(self, db_path: Path, image_dir: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        image_dir.mkdir(parents=True, exist_ok=True)
        self._image_dir = image_dir
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(CREATE_TABLE)
        self._conn.commit()
        logger.info("SampleStore ready at %s", db_path)

    def save(
        self,
        frame: np.ndarray,
        label: str,
        label_src: str,
        confidence: float | None = None,
    ) -> str:
        sample_id = str(uuid.uuid4())
        ts = datetime.now(timezone.utc).isoformat()
        image_path = self._image_dir / f"{sample_id}.jpg"
        cv2.imwrite(str(image_path), frame)

        self._conn.execute(
            "INSERT INTO samples (id, captured_at, image_path, label, label_src, confidence)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (sample_id, ts, str(image_path), label, label_src, confidence),
        )
        self._conn.commit()
        logger.debug("Saved sample %s label=%s src=%s", sample_id, label, label_src)
        return sample_id

    def pending(self, limit: int = 50) -> list[sqlite3.Row]:
        cur = self._conn.execute(
            "SELECT * FROM samples WHERE uploaded = 0 ORDER BY captured_at LIMIT ?",
            (limit,),
        )
        return cur.fetchall()

    def relabel(self, sample_id: str, label: str, label_src: str) -> None:
        self._conn.execute(
            "UPDATE samples SET label = ?, label_src = ? WHERE id = ?",
            (label, label_src, sample_id),
        )
        self._conn.commit()
        logger.debug("Relabeled %s → %s (%s)", sample_id, label, label_src)

    def mark_uploaded(self, sample_ids: list[str]) -> None:
        self._conn.executemany(
            "UPDATE samples SET uploaded = 1 WHERE id = ?",
            [(sid,) for sid in sample_ids],
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
