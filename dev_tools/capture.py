"""
截图 / 框选保存按钮素材。

用法：
    python -m dev_tools.capture

输入：
    1   从模拟器截一张全屏（保存到 dev_tools/last.png）
    2   在上次截图上拖框 -> 输入名字 -> 保存到 assets/<name>.png
    q   退出
"""
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.device import Device

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
LAST = ROOT / "dev_tools" / "last.png"


def shoot(device: Device) -> None:
    img = device.screenshot()
    cv2.imwrite(str(LAST), img)
    print(f"saved {LAST}  size={img.shape[1]}x{img.shape[0]}")


def crop() -> None:
    if not LAST.exists():
        print("先输入 1 截一张图")
        return
    img = cv2.imread(str(LAST))
    print("拖框选择按钮区域，回车确认 / Esc 取消")
    x, y, w, h = cv2.selectROI("crop", img, fromCenter=False, showCrosshair=True)
    cv2.destroyWindow("crop")
    if w == 0 or h == 0:
        print("已取消")
        return
    name = input("保存为 (例: main/BTN_PORRIDGE): ").strip()
    if not name:
        return
    out = ASSETS / f"{name}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), img[y:y + h, x:x + w])
    margin = 20
    sx1, sy1 = max(0, x - margin), max(0, y - margin)
    sx2, sy2 = x + w + margin, y + h + margin
    print(f"saved {out}")
    print(f"  原坐标:    x={x} y={y} w={w} h={h}")
    print(f"  search_area=({sx1}, {sy1}, {sx2}, {sy2})")


def main() -> None:
    device = Device("127.0.0.1:16512")
    print("[1] 截图  [2] 框选保存  [q] 退出")
    while True:
        try:
            cmd = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if cmd == "1":
            shoot(device)
        elif cmd == "2":
            crop()
        elif cmd == "q":
            break


if __name__ == "__main__":
    main()
