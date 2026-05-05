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


def _prepare(img: np.ndarray, use_edges: bool) -> tuple[np.ndarray, np.ndarray]:
    """Return (roi_for_matching, template_for_matching)."""
    if use_edges:
        return img, _edges(img)
    return img, img


def _match_res(roi: np.ndarray, tmpl: np.ndarray, use_edges: bool) -> np.ndarray:
    if use_edges:
        roi_e = _edges(roi)
        return cv2.matchTemplate(roi_e, tmpl, cv2.TM_CCOEFF_NORMED)
    return cv2.matchTemplate(roi, tmpl, cv2.TM_CCOEFF_NORMED)


def match(screen: np.ndarray, button: Button) -> tuple[int, int] | None:
    if button.search_area:
        x1, y1, x2, y2 = button.search_area
        roi = screen[y1:y2, x1:x2]
        ox, oy = x1, y1
    else:
        roi = screen
        ox, oy = 0, 0

    tmpl = _edges(button.template) if button.use_edges else button.template
    res = _match_res(roi, tmpl, button.use_edges)
    _, score, _, loc = cv2.minMaxLoc(res)
    if score < button.threshold:
        return None
    h, w = button.template.shape[:2]
    return ox + loc[0] + w // 2, oy + loc[1] + h // 2


def appear(screen: np.ndarray, button: Button) -> bool:
    return match(screen, button) is not None


def match_all(
    screen: np.ndarray,
    button: Button,
    min_distance: int = 30,
) -> list[tuple[int, int]]:
    """Return screen-space centers of all occurrences of button template."""
    if button.search_area:
        x1, y1, x2, y2 = button.search_area
        roi = screen[y1:y2, x1:x2]
        ox, oy = x1, y1
    else:
        roi = screen
        ox, oy = 0, 0

    tmpl = _edges(button.template) if button.use_edges else button.template
    res = _match_res(roi, tmpl, button.use_edges)
    h, w = button.template.shape[:2]
    locations: list[tuple[int, int]] = []
    tmp = res.copy()

    while True:
        _, max_val, _, max_loc = cv2.minMaxLoc(tmp)
        if max_val < button.threshold:
            break
        mx, my = max_loc
        locations.append((ox + mx + w // 2, oy + my + h // 2))
        y_lo = max(0, my - min_distance)
        y_hi = min(tmp.shape[0], my + min_distance + 1)
        x_lo = max(0, mx - min_distance)
        x_hi = min(tmp.shape[1], mx + min_distance + 1)
        tmp[y_lo:y_hi, x_lo:x_hi] = -1.0

    return locations
