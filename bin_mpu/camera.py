"""Camera capture — burst of N frames for ensemble inference."""
import logging
import time

import cv2
import numpy as np

from .config import Config

logger = logging.getLogger(__name__)


class Camera:
    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._cap: cv2.VideoCapture | None = None
        self._fake = cfg.fake_camera
        self._rng = np.random.default_rng(0)

    def open(self) -> None:
        if self._fake:
            logger.warning(
                "FAKE CAMERA enabled — generating synthetic %dx%d frames",
                self._cfg.capture_width, self._cfg.capture_height,
            )
            return
        cap = cv2.VideoCapture(self._cfg.camera_index, cv2.CAP_V4L2)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._cfg.capture_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._cfg.capture_height)
        cap.set(cv2.CAP_PROP_FPS, self._cfg.capture_fps)
        # Disable auto-exposure — controlled illumination means we want consistency
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # 1 = manual on V4L2
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open camera index {self._cfg.camera_index}")
        self._cap = cap
        logger.info("Camera opened: %dx%d", self._cfg.capture_width, self._cfg.capture_height)

    def close(self) -> None:
        if self._cap:
            self._cap.release()

    def _fake_frame(self) -> np.ndarray:
        return self._rng.integers(
            0, 256, (self._cfg.capture_height, self._cfg.capture_width, 3), dtype=np.uint8
        )

    def capture_burst(self) -> list[np.ndarray]:
        """Capture burst_frames frames at burst_interval_s intervals.

        Returns list of BGR frames. Raises RuntimeError if any frame fails.
        """
        if self._fake:
            frames = []
            for i in range(self._cfg.burst_frames):
                if i > 0:
                    time.sleep(self._cfg.burst_interval_s)
                frames.append(self._fake_frame())
            return frames

        if not self._cap or not self._cap.isOpened():
            raise RuntimeError("Camera not open")

        frames: list[np.ndarray] = []
        for i in range(self._cfg.burst_frames):
            if i > 0:
                time.sleep(self._cfg.burst_interval_s)
            ok, frame = self._cap.read()
            if not ok or frame is None:
                raise RuntimeError(f"Camera read failed on frame {i}")
            frames.append(frame)
            logger.debug("Captured frame %d/%d", i + 1, self._cfg.burst_frames)

        return frames

    def capture_single(self) -> np.ndarray:
        frames = self.capture_burst()
        return frames[0]

    def __enter__(self) -> "Camera":
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
