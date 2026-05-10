"""
建木营固定坐标标定工具
进入建木营后在每个 pass 截图，用鼠标点击收集按钮，自动记录坐标。
用法：python -m dev_tools.calibrate_jianmuying
操作：每张图弹出窗口，点击所有收集按钮后按 Enter 进入下一 pass，按 Q 退出。
"""

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.device import Device
from core.ocr import find_text
from core.template import match
from tasks.jianmuying import (
    ENTER_SLEEP,
    PATHFIND,
    PRE_SWIPE_SLEEP,
    RESET_SWIPE,
    RESET_SWIPES,
    SWIPE_DURATION_MS,
    SWIPE_PASSES,
    SWIPE_SLEEP,
)

SERIAL = "127.0.0.1:16512"

clicks_this_pass: list[tuple[int, int]] = []
all_passes: list[list[tuple[int, int]]] = []


def _on_click(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        clicks_this_pass.append((x, y))
        img = param["img"]
        cv2.circle(img, (x, y), 18, (0, 0, 255), 3)
        cv2.putText(img, str(len(clicks_this_pass)), (x - 8, y + 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.imshow("标定 — 点击收集按钮，Enter=下一pass，Q=退出", img)


def record_pass(screen: np.ndarray, pass_idx: int) -> list[tuple[int, int]]:
    global clicks_this_pass
    clicks_this_pass = []
    img = screen.copy()
    title = "标定 — 点击收集按钮，Enter=下一pass，Q=退出"
    cv2.namedWindow(title)
    cv2.setMouseCallback(title, _on_click, {"img": img})
    cv2.putText(img, f"Pass {pass_idx} — 点击所有收集按钮后按 Enter", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 0), 2)
    cv2.imshow(title, img)
    while True:
        key = cv2.waitKey(0) & 0xFF
        if key == 13:   # Enter
            break
        if key == ord('q'):
            cv2.destroyAllWindows()
            sys.exit(0)
    cv2.destroyAllWindows()
    return list(clicks_this_pass)


def main():
    dev = Device(SERIAL)

    print("[nav] 寻路")
    pt = match(dev.screenshot(), PATHFIND)
    if pt is None:
        print("寻路按钮未找到，请确认在主界面")
        return
    dev.click(*pt)
    dev.sleep(0.8)

    print("[nav] 建木营")
    screen = dev.screenshot()
    pt = find_text(screen, "建木营", search_area=(200, 450, 570, 850))
    if pt is None:
        print("建木营入口未找到")
        return
    dev.click(*pt)
    dev.sleep(ENTER_SLEEP)

    print(f"[reset] 复位 x{RESET_SWIPES}")
    for _ in range(RESET_SWIPES):
        dev.swipe(*RESET_SWIPE, SWIPE_DURATION_MS)
        dev.sleep(SWIPE_SLEEP)

    for i, swipe in enumerate(SWIPE_PASSES):
        if swipe is not None:
            dev.sleep(PRE_SWIPE_SLEEP)
            dev.swipe(*swipe, SWIPE_DURATION_MS)
            dev.sleep(SWIPE_SLEEP)

        screen = dev.screenshot()
        out = Path(__file__).parent / f"calib_pass{i}.png"
        cv2.imwrite(str(out), screen)
        print(f"Pass {i} 截图已保存: {out.name}")

        pts = record_pass(screen, i)
        all_passes.append(pts)
        print(f"  记录 {len(pts)} 个点: {pts}")

    print("\n\n=== 复制以下内容到 jianmuying.py ===\n")
    print("FIXED_CLICKS: list[list[tuple[int, int]]] = [")
    for i, pts in enumerate(all_passes):
        print(f"    {pts},  # pass {i}")
    print("]")


if __name__ == "__main__":
    main()
