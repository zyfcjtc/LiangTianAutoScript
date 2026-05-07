import sys
from pathlib import Path

import yaml

from core import runtime
from core.logger import logger
from ui.server import serve

# PyInstaller 打包后用 .exe 旁边的 config.yaml；否则用源码目录的
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"


def main() -> None:
    from core import launcher

    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}

    runtime.config_path = CONFIG_PATH
    runtime.ui_port = config.get("ui", {}).get("port", 8080)

    mumu_cfg = config.get("mumu") or {}
    runtime.mumu_exe = mumu_cfg.get("exe") or launcher.find_mumu_exe()
    if runtime.mumu_exe:
        logger.info(f"MuMu 路径: {runtime.mumu_exe}")

    for emu in config.get("emulators", []):
        try:
            runtime.add_emulator(
                emu["name"],
                emu["serial"],
                emu.get("tasks") or {},
                mumu_instance=emu.get("mumu_instance"),
                package=emu.get("package"),
                auto_login=emu.get("auto_login", True),
            )
        except Exception as e:
            logger.error(f"启动模拟器 {emu.get('name')} 失败: {e}")

    logger.info(f"UI 启动: http://127.0.0.1:{runtime.ui_port}")
    serve(port=runtime.ui_port)


if __name__ == "__main__":
    main()
