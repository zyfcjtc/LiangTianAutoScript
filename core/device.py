import random
import time

import cv2
import numpy as np
from adbutils import adb

from core.logger import logger

CLICK_JITTER_PX = 4
SLEEP_JITTER_RATIO = 0.15


class Device:
    def __init__(self, serial: str = "127.0.0.1:16384"):
        self.serial = serial
        adb.connect(serial)
        self.d = adb.device(serial=serial)
        model = self.d.shell("getprop ro.product.model").strip()
        logger.info(f"Connected: {serial} ({model})")

    def screenshot(self) -> np.ndarray:
        pil = self.d.screenshot()
        return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

    def click(self, x: int, y: int) -> None:
        jx = x + random.randint(-CLICK_JITTER_PX, CLICK_JITTER_PX)
        jy = y + random.randint(-CLICK_JITTER_PX, CLICK_JITTER_PX)
        self.d.shell(f"input tap {jx} {jy}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        self.d.shell(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")

    def sleep(self, sec: float) -> None:
        factor = 1.0 + random.uniform(-SLEEP_JITTER_RATIO, SLEEP_JITTER_RATIO)
        time.sleep(max(0.05, sec * factor))
