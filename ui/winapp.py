"""
ui/winapp.py — pywebview Windows desktop app
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import webview

from core import runtime
from core.logger import log_buffer, log_buffer_lock

if getattr(sys, "frozen", False):
    _BASE = Path(sys.executable).parent
    _ROOT = _BASE
    _HTML_PATH = Path(sys._MEIPASS) / "ui" / "web" / "index.html"
else:
    _BASE = Path(__file__).parent
    _ROOT = _BASE.parent
    _HTML_PATH = _BASE / "web" / "index.html"


class API:
    """Exposed to the webview as window.pywebview.api"""

    def __init__(self) -> None:
        self._window: webview.Window | None = None
        self._win_x: int = 200
        self._win_y: int = 150
        self._maximized: bool = False

    # ── Window controls ──────────────────────────────────────────────────────

    def minimize(self) -> None:
        if self._window:
            self._window.minimize()

    def toggle_maximize(self) -> None:
        if not self._window:
            return
        if self._maximized:
            self._window.restore()
        else:
            self._window.maximize()
        self._maximized = not self._maximized

    def close(self) -> None:
        if self._window:
            self._window.destroy()

    def open_url(self, url: str) -> None:
        import webbrowser
        webbrowser.open(url)

    def drag_delta(self, dx: int, dy: int) -> None:
        if not self._window:
            return
        self._win_x += int(dx)
        self._win_y += int(dy)
        self._window.move(self._win_x, self._win_y)

    # ── Data API ─────────────────────────────────────────────────────────────

    def get_emulators(self) -> list[dict]:
        return [self._snap(s) for s in runtime.list_schedulers()]

    def get_logs(self, emu_name: str, since_id: int) -> list[dict]:
        since_id = int(since_id)
        with log_buffer_lock:
            if emu_name == "__all__":
                entries = [e for e in log_buffer if e["id"] > since_id]
            else:
                entries = [
                    e for e in log_buffer
                    if e["id"] > since_id and e["thread"] == emu_name
                ]
        return [
            {"id": e["id"], "text": e["formatted"],
             "level": e["level"], "thread": e["thread"]}
            for e in entries
        ]

    def get_task_registry(self) -> list[dict]:
        from tasks import TASK_REGISTRY
        _defaults = {"粥棚": 180, "膜拜": 1440, "建木营": 1440, "看广告": 1440}
        return [
            {"name": k, "default_interval": _defaults.get(k, 60)}
            for k in TASK_REGISTRY
        ]

    def get_version(self) -> str:
        p = _ROOT / "version.txt"
        return p.read_text("utf-8").strip() if p.exists() else "dev"

    _REPO = "zyfcjtc/LiangtianAutoScript"
    _API  = f"https://api.github.com/repos/{_REPO}/releases/latest"

    def get_current_info(self) -> dict:
        import os
        from datetime import datetime
        p = _ROOT / "version.txt"
        if p.exists():
            version = p.read_text("utf-8").strip()
        else:
            try:
                import subprocess
                version = subprocess.check_output(
                    ["git", "branch", "--show-current"],
                    cwd=str(_ROOT), stderr=subprocess.DEVNULL, text=True,
                ).strip() or "dev"
            except Exception:
                version = "dev"

        try:
            import subprocess
            raw = subprocess.check_output(
                ["git", "log", "-1", "--format=%ai"],
                cwd=str(_ROOT), stderr=subprocess.DEVNULL, text=True,
            ).strip()
            last_update = raw[:19]
        except Exception:
            try:
                mtime = os.path.getmtime(str(_ROOT / "main.py"))
                last_update = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                last_update = "未知"

        return {"version": version, "last_update": last_update}

    def check_update(self) -> dict:
        import urllib.request, json
        p = _ROOT / "version.txt"
        current = p.read_text("utf-8-sig").strip() if p.exists() else None
        try:
            req = urllib.request.Request(
                self._API,
                headers={"User-Agent": "LiangtianAutoScript-Updater"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            latest_tag = data["tag_name"]
            is_new = current is not None and latest_tag.lstrip("v") != current.lstrip("v")
            patch_asset = next(
                (a for a in data.get("assets", []) if a["name"].startswith("patch-")),
                None,
            )
            return {
                "ok": True,
                "latest": latest_tag,
                "date": data["published_at"][:10],
                "url": data["html_url"],
                "body": (data.get("body") or "")[:400],
                "has_update": is_new,
                "patch_available": patch_asset is not None,
                "patch_size_kb": round(patch_asset["size"] / 1024) if patch_asset else 0,
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def download_patch(self) -> dict:
        import urllib.request, json, zipfile, io, shutil
        tmp = _ROOT / "patch_tmp"
        try:
            req = urllib.request.Request(
                self._API,
                headers={"User-Agent": "LiangtianAutoScript-Updater"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                release = json.loads(resp.read())
            patch_asset = next(
                (a for a in release.get("assets", []) if a["name"].startswith("patch-")),
                None,
            )
            if not patch_asset:
                return {"ok": False, "error": "此版本无补丁包，请下载完整版"}
            dl_req = urllib.request.Request(
                patch_asset["browser_download_url"],
                headers={"User-Agent": "LiangtianAutoScript-Updater"},
            )
            with urllib.request.urlopen(dl_req, timeout=120) as resp:
                raw = resp.read()
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                # zip slip 校验
                for name in zf.namelist():
                    if name.startswith("/") or ".." in name:
                        return {"ok": False, "error": f"补丁包含非法路径: {name}"}
                # 先解到临时目录，成功后再合并
                if tmp.exists():
                    shutil.rmtree(tmp)
                zf.extractall(str(tmp))
            for item in tmp.iterdir():
                dest = _ROOT / item.name
                if dest.exists():
                    shutil.rmtree(dest) if dest.is_dir() else dest.unlink()
                shutil.move(str(item), str(_ROOT))
            shutil.rmtree(tmp, ignore_errors=True)
            (_ROOT / "version.txt").write_text(
                release["tag_name"].lstrip("v") + "\n", encoding="utf-8"
            )
            return {"ok": True}
        except Exception as exc:
            shutil.rmtree(tmp, ignore_errors=True)
            return {"ok": False, "error": str(exc)}

    def add_emulator(self, data: dict) -> dict:
        try:
            task_specs = {
                t["name"]: {"interval_minutes": int(t.get("interval", 60))}
                for t in (data.get("tasks") or [])
            }
            raw = data.get("mumu_instance")
            mumu_inst = int(raw) if raw not in (None, "", "null") else None
            runtime.add_emulator(
                data["name"].strip(),
                data["serial"].strip(),
                task_specs,
                mumu_instance=mumu_inst,
                package=(data.get("package") or "").strip() or None,
                auto_login=bool(data.get("auto_login")),
                run_once=bool(data.get("run_once")),
            )
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def trigger_task(self, emu_name: str, task_name: str) -> dict:
        ok = runtime.trigger_task(emu_name, task_name)
        return {"ok": ok}

    def delete_emulator(self, name: str) -> dict:
        threading.Thread(
            target=runtime.remove_emulator, args=(name,), daemon=True,
        ).start()
        return {"ok": True}

    @staticmethod
    def _snap(s) -> dict:
        return {
            "name": s.name,
            "serial": s.serial,
            "status": s.status,
            "current_task": s.current_task,
            "last_error": s.last_error,
            "tasks": [
                {
                    "name": t.name,
                    "next_run": t.next_run.isoformat() if t.next_run else None,
                    "interval_minutes": t.interval_minutes,
                }
                for t in s.tasks
            ],
        }


def start_winapp() -> None:
    api = API()
    window = webview.create_window(
        title="良田自动脚本",
        url=_HTML_PATH.as_uri(),
        js_api=api,
        width=1040,
        height=700,
        min_size=(800, 550),
        x=200,
        y=150,
        frameless=True,
        easy_drag=False,
        background_color="#FFFFFF",
    )
    api._window = window
    webview.start(debug=False)
