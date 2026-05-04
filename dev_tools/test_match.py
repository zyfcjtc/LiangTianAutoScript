"""
验证模板匹配是否工作。

用法：
    python -m dev_tools.test_match

会截一张图，尝试找 BTN_PORRIDGE，把识别结果可视化保存到 dev_tools/match_result.png
"""
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.device import Device
from core.template import Button, match

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dev_tools" / "match_result.png"


def main() -> None:
    device = Device("127.0.0.1:16512")
    screen = device.screenshot()
    print(f"screen size: {screen.shape[1]}x{screen.shape[0]}")

    btn = Button(
        name="main.BTN_PORRIDGE",
        template_path="main/BTN_PORRIDGE.png",
        search_area=(263, 542, 380, 637),
    )

    point = match(screen, btn)
    if point is None:
        print("NOT FOUND")
    else:
        print(f"FOUND at {point}")
        cv2.circle(screen, point, 30, (0, 255, 0), 4)

    x1, y1, x2, y2 = btn.search_area
    cv2.rectangle(screen, (x1, y1), (x2, y2), (0, 200, 255), 2)
    cv2.imwrite(str(OUT), screen)
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()
