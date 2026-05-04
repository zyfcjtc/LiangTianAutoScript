import threading
from pathlib import Path

import yaml

from core.device import Device
from core.logger import logger
from core.scheduler import Scheduler
from core.ui import UI
from tasks import TASK_REGISTRY
from ui.server import serve

CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def start_emulator(emu: dict) -> Scheduler | None:
    name = emu["name"]
    serial = emu["serial"]
    try:
        device = Device(serial)
    except Exception as e:
        logger.exception(f"[{name}] 连接模拟器失败: {e}")
        sched = Scheduler(UI(None, []), [], name=name)
        sched.status = "error"
        sched.last_error = f"连接失败: {e}"
        return sched

    tasks = []
    for task_name, task_cfg in (emu.get("tasks") or {}).items():
        cls = TASK_REGISTRY.get(task_name)
        if cls is None:
            logger.warning(f"[{name}] 未知任务名: {task_name}（已忽略）")
            continue
        tasks.append(cls(name=task_name, **(task_cfg or {})))

    sched = Scheduler(UI(device, []), tasks, name=name)
    threading.Thread(target=sched.loop, name=name, daemon=True).start()
    return sched


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

    schedulers = []
    for emu in config.get("emulators", []):
        sched = start_emulator(emu)
        if sched is not None:
            schedulers.append(sched)

    if not schedulers:
        logger.warning("没有任何模拟器启动成功，UI 仍会启动用于排查")

    port = config.get("ui", {}).get("port", 8080)
    logger.info(f"UI 启动: http://127.0.0.1:{port}")
    serve(schedulers, port=port)


if __name__ == "__main__":
    main()
