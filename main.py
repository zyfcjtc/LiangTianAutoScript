from pathlib import Path

import yaml

from core import runtime
from core.logger import logger
from ui.server import serve

CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}

    runtime.config_path = CONFIG_PATH
    runtime.ui_port = config.get("ui", {}).get("port", 8080)

    for emu in config.get("emulators", []):
        try:
            runtime.add_emulator(
                emu["name"],
                emu["serial"],
                emu.get("tasks") or {},
            )
        except Exception as e:
            logger.error(f"启动模拟器 {emu.get('name')} 失败: {e}")

    logger.info(f"UI 启动: http://127.0.0.1:{runtime.ui_port}")
    serve(port=runtime.ui_port)


if __name__ == "__main__":
    main()
