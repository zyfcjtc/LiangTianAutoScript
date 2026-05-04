from pathlib import Path

import cv2
import numpy as np

ASSETS = Path(__file__).resolve().parents[1] / "assets"


class Button:
    def __init__(
        self,
        name: str,
        template_path: str,
        search_area: tuple | None = None,
        threshold: float = 0.8,
    ):
        self.name = name
        self.template_path = template_path
        self.search_area = search_area
        self.threshold = threshold
        self._template: np.ndarray | None = None

    @property
    def template(self) -> np.ndarray:
        if self._template is None:
            path = ASSETS / self.template_path
            img = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if img is None:
                raise FileNotFoundError(f"Asset not found: {path}")
            self._template = img
        return self._template


def match(screen: np.ndarray, button: Button) -> tuple[int, int] | None:
    if button.search_area:
        x1, y1, x2, y2 = button.search_area
        roi = screen[y1:y2, x1:x2]
        ox, oy = x1, y1
    else:
        roi = screen
        ox, oy = 0, 0

    res = cv2.matchTemplate(roi, button.template, cv2.TM_CCOEFF_NORMED)
    _, score, _, loc = cv2.minMaxLoc(res)
    if score < button.threshold:
        return None
    h, w = button.template.shape[:2]
    return ox + loc[0] + w // 2, oy + loc[1] + h // 2


def appear(screen: np.ndarray, button: Button) -> bool:
    return match(screen, button) is not None
