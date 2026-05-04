import threading
from pathlib import Path

import yaml

from core.device import Device
from core.logger import logger
from core.scheduler import Scheduler
from core.ui import UI as PageUI

_lock = threading.Lock()
schedulers: list[Scheduler] = []
config_path: Path | None = None
ui_port: int = 8080


def list_schedulers() -> list[Scheduler]:
    with _lock:
        return list(schedulers)


def add_emulator(name: str, serial: str, task_specs: dict) -> Scheduler:
    """task_specs: {task_name: {"interval_minutes": int}}
    Raises ValueError on validation failure, RuntimeError on connection failure.
    """
    from tasks import TASK_REGISTRY

    name = name.strip()
    serial = serial.strip()
    if not name:
        raise ValueError("名字不能为空")
    if not serial:
        raise ValueError("端口不能为空")

    with _lock:
        if any(s.name == name for s in schedulers):
            raise ValueError(f"模拟器名 '{name}' 已存在")

        try:
            device = Device(serial)
        except Exception as e:
            raise RuntimeError(f"连接 {serial} 失败: {e}")

        tasks = []
        for task_name, cfg in task_specs.items():
            cls = TASK_REGISTRY.get(task_name)
            if cls is None:
                raise ValueError(f"未知任务: {task_name}")
            tasks.append(cls(name=task_name, **(cfg or {})))

        sched = Scheduler(PageUI(device, []), tasks, name=name, serial=serial)
        thread = threading.Thread(target=sched.loop, name=name, daemon=True)
        sched.thread = thread
        thread.start()
        schedulers.append(sched)
        _save_config_locked()
        logger.info(f"已添加模拟器: {name} ({serial})")
        return sched


def remove_emulator(name: str, join_timeout: float = 30.0) -> bool:
    with _lock:
        target = next((s for s in schedulers if s.name == name), None)
        if target is None:
            return False
        target.stop()

    if target.thread is not None:
        target.thread.join(timeout=join_timeout)

    with _lock:
        if target in schedulers:
            schedulers.remove(target)
        _save_config_locked()
    logger.info(f"已删除模拟器: {name}")
    return True


def _save_config_locked() -> None:
    if config_path is None:
        return
    cfg = {
        "ui": {"port": ui_port},
        "emulators": [
            {
                "name": s.name,
                "serial": s.serial,
                "tasks": {
                    t.name: {"interval_minutes": t.interval_minutes}
                    for t in s.tasks
                },
            }
            for s in schedulers
        ],
    }
    config_path.write_text(
        yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
