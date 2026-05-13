"""
MCU ↔ MPU serial protocol.

Command set (MPU → MCU):
  LED_ON
  LED_OFF

Events (MCU → MPU):
  PIR_TRIG
"""
import logging
import threading
from collections.abc import Callable

import serial

from .config import Config

logger = logging.getLogger(__name__)

CMD_LED_ON = "LED_ON"
CMD_LED_OFF = "LED_OFF"
CMD_LID_OPEN = "LID_OPEN"
CMD_LID_CLOSE = "LID_CLOSE"

EVT_PIR_TRIG = "PIR_TRIG"
EVT_LID_OPENED = "LID_OPENED"
EVT_LID_CLOSED = "LID_CLOSED"


class MCULink:
    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._ser: serial.Serial | None = None
        self._lock = threading.Lock()
        self._event_callbacks: list[Callable[[str], None]] = []

    def connect(self) -> None:
        self._ser = serial.Serial(
            self._cfg.serial_port,
            self._cfg.serial_baud,
            timeout=self._cfg.serial_timeout_s,
        )
        logger.info("MCU serial connected on %s", self._cfg.serial_port)
        t = threading.Thread(target=self._read_loop, daemon=True)
        t.start()

    def disconnect(self) -> None:
        if self._ser and self._ser.is_open:
            self._ser.close()

    def on_event(self, cb: Callable[[str], None]) -> None:
        self._event_callbacks.append(cb)

    def send(self, cmd: str) -> None:
        if not self._ser or not self._ser.is_open:
            logger.warning("Serial not open, dropping command: %s", cmd)
            return
        with self._lock:
            self._ser.write((cmd + "\n").encode())

    def led_on(self) -> None:
        self.send(CMD_LED_ON)

    def led_off(self) -> None:
        self.send(CMD_LED_OFF)

    def lid_open(self) -> None:
        self.send(CMD_LID_OPEN)

    def lid_close(self) -> None:
        self.send(CMD_LID_CLOSE)

    def _read_loop(self) -> None:
        assert self._ser is not None
        while self._ser.is_open:
            try:
                raw = self._ser.readline()
                if not raw:
                    continue
                event = raw.decode(errors="replace").strip()
                logger.debug("MCU event: %s", event)
                for cb in self._event_callbacks:
                    cb(event)
            except serial.SerialException as exc:
                logger.error("Serial read error: %s", exc)
                break
