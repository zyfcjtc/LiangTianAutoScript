import subprocess
import time
from pathlib import Path

from adbutils import adb

from core.logger import logger

_DEFAULT_EXE_PATHS = [
    r"C:\Program Files\Netease\MuMuPlayer-12.0\shell\MuMuPlayer.exe",
    r"C:\Program Files (x86)\Netease\MuMuPlayer-12.0\shell\MuMuPlayer.exe",
]
_POLL_INTERVAL = 3
_LAUNCH_TIMEOUT = 120


def find_mumu_exe() -> str | None:
    """在常见安装路径中查找 MuMuPlayer.exe，找到则返回路径，否则返回 None。"""
    for p in _DEFAULT_EXE_PATHS:
        if Path(p).exists():
            return p
    return None


def is_adb_ready(serial: str) -> bool:
    try:
        adb.connect(serial)
        adb.device(serial=serial).shell("echo ok")
        return True
    except Exception:
        return False


def ensure_running(serial: str, exe: str, instance: int, timeout: int = _LAUNCH_TIMEOUT) -> None:
    """如果 ADB 不可达，启动指定 MuMu 实例并等待就绪；已就绪则直接返回。"""
    if is_adb_ready(serial):
        return

    logger.info(f"MuMu 实例 {instance} 未连接，正在启动: {exe} -v {instance}")
    subprocess.Popen([exe, "-v", str(instance)])

    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(_POLL_INTERVAL)
        if is_adb_ready(serial):
            logger.info(f"{serial} ADB 就绪")
            return

    raise RuntimeError(
        f"等待 {serial} 超时（{timeout}s），请检查 MuMu 是否正常启动"
    )
