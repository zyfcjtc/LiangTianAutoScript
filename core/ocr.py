from __future__ import annotations

import numpy as np

from core.template import _crop_roi

_ocr = None


def _get_ocr():
    global _ocr
    if _ocr is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr = RapidOCR()
    return _ocr


def scan_texts(
    screen: np.ndarray,
    search_area: tuple[int, int, int, int] | None = None,
    threshold: float = 0.5,
) -> list[tuple[str, tuple[int, int]]]:
    """对区域跑一次 OCR，返回 [(识别文字, (x, y)), ...] 列表（屏幕坐标）。"""
    ocr = _get_ocr()
    roi, ox, oy = _crop_roi(screen, search_area)

    result, _ = ocr(roi)
    if not result:
        return []

    hits = []
    for bbox, detected, score in result:
        if float(score) >= threshold:
            cx = int((bbox[0][0] + bbox[2][0]) / 2) + ox
            cy = int((bbox[0][1] + bbox[2][1]) / 2) + oy
            hits.append((detected, (cx, cy)))
    return hits


def find_text(
    screen: np.ndarray,
    text: str,
    search_area: tuple[int, int, int, int] | None = None,
    threshold: float = 0.5,
) -> tuple[int, int] | None:
    """在画面中查找文字，返回屏幕坐标中心 (x, y)，找不到返回 None。"""
    for detected, pt in scan_texts(screen, search_area=search_area, threshold=threshold):
        if text in detected:
            return pt
    return None
