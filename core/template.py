import sys
from pathlib import Path

import cv2
import numpy as np

if getattr(sys, "frozen", False):
    _ext = Path(sys.executable).parent / "assets"
    ASSETS = _ext if _ext.exists() else Path(sys._MEIPASS) / "assets"
else:
    ASSETS = Path(__file__).resolve().parents[1] / "assets"


class Button:
    def __init__(
        self,
        name: str,
        template_path: str,
        search_area: tuple | None = None,
        threshold: float = 0.8,
        use_edges: bool = False,
    ):
        self.name = name
        self.template_path = template_path
        self.search_area = search_area
        self.threshold = threshold
        self.use_edges = use_edges
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


def _edges(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.Canny(gray, 50, 150).astype(np.float32)


def _crop_roi(
    screen: np.ndarray,
    search_area: tuple[int, int, int, int] | None,
) -> tuple[np.ndarray, int, int]:
    """Crop screen to search_area; return (roi, offset_x, offset_y)."""
    if search_area:
        x1, y1, x2, y2 = search_area
        return screen[y1:y2, x1:x2], x1, y1
    return screen, 0, 0


def _match_res(roi: np.ndarray, tmpl: np.ndarray, use_edges: bool) -> np.ndarray:
    if use_edges:
        return cv2.matchTemplate(_edges(roi), tmpl, cv2.TM_CCOEFF_NORMED)
    return cv2.matchTemplate(roi, tmpl, cv2.TM_CCOEFF_NORMED)


def match(screen: np.ndarray, button: Button) -> tuple[int, int] | None:
    roi, ox, oy = _crop_roi(screen, button.search_area)
    tmpl = _edges(button.template) if button.use_edges else button.template
    res = _match_res(roi, tmpl, button.use_edges)
    _, score, _, loc = cv2.minMaxLoc(res)
    if score < button.threshold:
        return None
    h, w = button.template.shape[:2]
    return ox + loc[0] + w // 2, oy + loc[1] + h // 2


def appear(screen: np.ndarray, button: Button) -> bool:
    return match(screen, button) is not None
