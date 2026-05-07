import os
import subprocess
import threading
import time
from pathlib import Path

import yaml

from core.device import Device
from core import launcher
from core.logger import logger
from core.scheduler import Scheduler
from core.ui import UI as PageUI

_lock = threading.Lock()
schedulers: list[Scheduler] = []
config_path: Path | None = None
ui_port: int = 8080
mumu_exe: str | None = None


def list_schedulers() -> list[Scheduler]:
    with _lock:
        return list(schedulers)


def add_emulator(
    name: str,
    serial: str,
    task_specs: dict,
    mumu_instance: int | None = None,
    package: str | None = None,
    auto_login: bool = False,
    run_once: bool = False,
) -> Scheduler:
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

    # 快速校验重名（短暂持锁）
    with _lock:
        if any(s.name == name for s in schedulers):
            raise ValueError(f"模拟器名 '{name}' 已存在")

    # 启动模拟器 + 游戏（耗时操作，锁外执行）
    if mumu_instance is not None:
        exe = mumu_exe or launcher.find_mumu_exe()
        if exe:
            launcher.ensure_running(serial, exe, mumu_instance)
        else:
            logger.warning("未找到 MuMuPlayer.exe，跳过自动启动")

    if package and auto_login:
        launcher.ensure_game_running(serial, package)

    # 建立设备连接并注册调度器（持锁）
    with _lock:
        # 二次校验（防并发重复添加）
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

        sched = Scheduler(
            PageUI(device, []), tasks,
            name=name, serial=serial,
            mumu_instance=mumu_instance, package=package,
            auto_login=auto_login, run_once=run_once,
        )
        thread = threading.Thread(target=sched.loop, name=name, daemon=True)
        sched.thread = thread
        thread.start()
        schedulers.append(sched)
        _save_config_locked()
        logger.info(f"已添加模拟器: {name} ({serial})")

    # 若有 run_once 调度器，启动收尾 watcher
    if run_once:
        _ensure_shutdown_watcher()

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


# ── run_once 收尾 ────────────────────────────────────────────────────────────

_watcher_started = False
_watcher_lock = threading.Lock()


def _ensure_shutdown_watcher() -> None:
    global _watcher_started
    with _watcher_lock:
        if _watcher_started:
            return
        _watcher_started = True
    t = threading.Thread(target=_shutdown_watcher, name="shutdown-watcher", daemon=True)
    t.start()


def _shutdown_watcher() -> None:
    """等所有 run_once 调度器跑完，关游戏 → 关 MuMu → 退出进程。"""
    while True:
        time.sleep(3)
        with _lock:
            run_once = [s for s in schedulers if s.run_once]
        if not run_once:
            continue
        if not all(s.status == "stopped" for s in run_once):
            continue

        logger.info("所有任务已完成，开始收尾关闭...")

        exe = mumu_exe or launcher.find_mumu_exe()
        for s in run_once:
            # 关游戏
            if s.package:
                try:
                    from adbutils import adb
                    adb.device(serial=s.serial).shell(f"am force-stop {s.package}")
                    logger.info(f"已关闭游戏 ({s.serial})")
                except Exception:
                    pass

            # 关 MuMu
            if s.mumu_instance is not None and exe:
                mgr = launcher._find_manager(exe)
                if mgr:
                    subprocess.run(
                        [mgr, "control", "-v", str(s.mumu_instance), "shutdown"],
                        capture_output=True,
                    )
                    logger.info(f"已关闭 MuMu 实例 {s.mumu_instance}")

        time.sleep(2)
        logger.info("退出脚本")
        os._exit(0)


# ── 持久化 ───────────────────────────────────────────────────────────────────

def _save_config_locked() -> None:
    if config_path is None:
        return
    cfg: dict = {"ui": {"port": ui_port}}
    if mumu_exe:
        cfg["mumu"] = {"exe": mumu_exe}
    emu_list = []
    for s in schedulers:
        entry: dict = {
            "name": s.name,
            "serial": s.serial,
            "tasks": {
                t.name: {"interval_minutes": t.interval_minutes}
                for t in s.tasks
            },
        }
        if s.mumu_instance is not None:
            entry["mumu_instance"] = s.mumu_instance
        if s.package:
            entry["package"] = s.package
        if s.auto_login:
            entry["auto_login"] = True
        if s.run_once:
            entry["run_once"] = True
        emu_list.append(entry)
    cfg["emulators"] = emu_list
    config_path.write_text(
        yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
