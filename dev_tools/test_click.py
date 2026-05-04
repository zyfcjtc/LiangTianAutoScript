"""
完整闭环：主页 -> 寻路 -> 粥棚(菜单项) -> 连点 BTN_PORRIDGE 15 次

用法：
    python -m dev_tools.test_click

游戏先停在主城首页。
"""
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.device import Device
from core.template import Button, match

ROOT = Path(__file__).resolve().parents[1]
AFTER = ROOT / "dev_tools" / "click_after.png"

CLICK_TIMES = 15
CLICK_INTERVAL = 0.4


def find_and_click(device: Device, btn: Button, timeout: float = 5.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        point = match(device.screenshot(), btn)
        if point:
            device.click(*point)
            print(f"  click {btn.name} @ {point}")
            return True
        time.sleep(0.5)
    print(f"  NOT FOUND: {btn.name}")
    return False


def main() -> None:
    device = Device("127.0.0.1:16512")

    pathfind = Button(
        "main.BTN_PATHFIND",
        "main/BTN_PATHFIND.png",
        search_area=(635, 643, 717, 735),
    )
    porridge_in_menu = Button(
        "pathfind.BTN_ZHOUPENG",
        "pathfind/BTN_ZHOUPENG.png",
        search_area=(454, 198, 660, 524),
    )
    collect = Button(
        "porridge.BTN_COLLECT",
        "main/BTN_PORRIDGE.png",
        search_area=(193, 469, 284, 547),
    )

    print("[1/3] 点 寻路")
    if not find_and_click(device, pathfind):
        return
    time.sleep(0.8)

    print("[2/3] 在寻路列表里点 粥棚")
    if not find_and_click(device, porridge_in_menu):
        return

    print(f"[3/3] 等粥棚界面 -> 连点 BTN_PORRIDGE {CLICK_TIMES} 次")
    point = None
    end = time.time() + 8.0
    while time.time() < end:
        point = match(device.screenshot(), collect)
        if point:
            break
        time.sleep(0.5)
    if point is None:
        print(f"  NOT FOUND: {collect.name}")
        debug = ROOT / "dev_tools" / "click_debug_step3.png"
        cv2.imwrite(str(debug), device.screenshot())
        print(f"  saved {debug}")
        return

    for i in range(1, CLICK_TIMES + 1):
        device.click(*point)
        print(f"  [{i}/{CLICK_TIMES}] click @ {point}")
        time.sleep(CLICK_INTERVAL)

    time.sleep(1.0)
    cv2.imwrite(str(AFTER), device.screenshot())
    print(f"OK  saved {AFTER}")


if __name__ == "__main__":
    main()
