"""
单独跑一次膜拜任务（不用调度器）。

用法：
    python -m dev_tools.test_mobai

游戏先停在主城首页。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.device import Device
from core.ui import UI
from tasks.mobai import MobaiTask


def main() -> None:
    device = Device("127.0.0.1:16512")
    ui = UI(device, [])
    task = MobaiTask(name="膜拜")
    task.run(ui)
    print("OK")


if __name__ == "__main__":
    main()
