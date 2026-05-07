import subprocess
import time
from pathlib import Path

from adbutils import adb

from core.logger import logger

# 按优先级排列的 MuMu 主程序默认路径（用于定位安装目录）
_DEFAULT_EXE_PATHS = [
    r"C:\Program Files\Netease\MuMu\nx_main\MuMuNxMain.exe",
    r"C:\Program Files (x86)\Netease\MuMu\nx_main\MuMuNxMain.exe",
    r"C:\Program Files\Netease\MuMuPlayer-12.0\shell\MuMuPlayer.exe",
    r"C:\Program Files (x86)\Netease\MuMuPlayer-12.0\shell\MuMuPlayer.exe",
]
_POLL_INTERVAL = 3
_LAUNCH_TIMEOUT = 120

# 游戏登录页面参数（分辨率锁定 720×1280）
_YIYUE_BTN = (360, 985)       # 公告弹窗「已阅」按钮（叠在登录页上方）
_LOGIN_BTN = (360, 1050)      # 「登录」按钮中心坐标
_LOGIN_SCREEN_WAIT = 35       # 启动 App 后等待登录页出现的秒数
_YIYUE_WAIT = 2               # 点「已阅」后等登录按钮可用的秒数
_GAME_LOAD_WAIT = 15          # 点击「登录」后等待进入主城的秒数


def find_mumu_exe() -> str | None:
    """在常见安装路径中查找 MuMu 主程序，找到则返回路径，否则返回 None。"""
    for p in _DEFAULT_EXE_PATHS:
        if Path(p).exists():
            return p
    return None


def _find_manager(hint: str) -> str | None:
    """从 hint（任意 MuMu 目录内的 exe）推导 MuMuManager.exe 路径。"""
    manager = Path(hint).parent / "MuMuManager.exe"
    return str(manager) if manager.exists() else None


def is_adb_ready(serial: str) -> bool:
    try:
        adb.connect(serial)
        adb.device(serial=serial).shell("echo ok")
        return True
    except Exception:
        return False


# 这些 Activity 出现时说明还在登录流程中，不算"已进主城"
_LOGIN_ACTIVITIES = ("cn.ewan.supersdk.activity",)


def _is_in_game(serial: str, package: str) -> bool:
    """包名在前台且不在登录流程中（即已进主城）才返回 True。"""
    try:
        focus = adb.device(serial=serial).shell(
            "dumpsys window | grep mCurrentFocus"
        ).strip()
        if package not in focus:
            return False
        return not any(act in focus for act in _LOGIN_ACTIVITIES)
    except Exception:
        return False


def ensure_running(serial: str, exe: str, instance: int, timeout: int = _LAUNCH_TIMEOUT) -> None:
    """如果 ADB 不可达，启动指定 MuMu 实例并等待就绪；已就绪则直接返回。"""
    if is_adb_ready(serial):
        return

    manager = _find_manager(exe)
    if manager:
        cmd = [manager, "control", "-v", str(instance), "launch"]
    else:
        cmd = [exe, "-v", str(instance)]

    logger.info(f"MuMu instance {instance} offline, launching: {' '.join(cmd)}")
    subprocess.Popen(cmd)

    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(_POLL_INTERVAL)
        if is_adb_ready(serial):
            logger.info(f"{serial} ADB ready")
            return

    raise RuntimeError(
        f"Timed out waiting for {serial} ({timeout}s). Check if MuMu started correctly."
    )


def ensure_game_running(serial: str, package: str) -> None:
    """确保游戏已进主城；已在主城则直接跳过，否则启动并完成登录流程。"""
    if _is_in_game(serial, package):
        logger.info("Game already in main city, skipping login")
        return

    d = adb.device(serial=serial)
    logger.info(f"Launching game: {package}")
    d.shell(f"monkey -p {package} -c android.intent.category.LAUNCHER 1")

    logger.info(f"Waiting {_LOGIN_SCREEN_WAIT}s for login screen...")
    time.sleep(_LOGIN_SCREEN_WAIT)

    logger.info(f"Tapping 已阅 at {_YIYUE_BTN}")
    d.shell(f"input tap {_YIYUE_BTN[0]} {_YIYUE_BTN[1]}")
    time.sleep(_YIYUE_WAIT)

    logger.info(f"Tapping 登录 at {_LOGIN_BTN}")
    d.shell(f"input tap {_LOGIN_BTN[0]} {_LOGIN_BTN[1]}")

    logger.info(f"Waiting {_GAME_LOAD_WAIT}s for game to load...")
    time.sleep(_GAME_LOAD_WAIT)
    logger.info("Game startup complete")
