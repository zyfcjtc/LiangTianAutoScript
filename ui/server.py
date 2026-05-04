import time
from datetime import datetime

from pywebio import start_server
from pywebio.output import (
    clear,
    put_markdown,
    put_scope,
    put_table,
    put_text,
    use_scope,
)
from pywebio.session import set_env

from core.logger import log_buffer, log_buffer_lock

REFRESH_SEC = 2
LOG_TAIL = 80


def _fmt_next(at: datetime | None) -> str:
    if at is None:
        return "-"
    delta = (at - datetime.now()).total_seconds()
    if delta < 0:
        return "now"
    if delta < 60:
        return f"{int(delta)}s"
    if delta < 3600:
        return f"{int(delta // 60)}m"
    return f"{int(delta // 3600)}h{int((delta % 3600) // 60)}m"


def _status_dot(s: str) -> str:
    return {
        "starting": "⚪ 启动中",
        "idle": "🟢 待机",
        "running": "🟡 运行中",
        "error": "🔴 错误",
    }.get(s, s)


def _build_app(schedulers):
    def app():
        set_env(title="AutoScript 监控")
        put_markdown("# AutoScript 监控")
        put_markdown(f"自动每 {REFRESH_SEC} 秒刷新一次。关掉这个标签页不会停止脚本运行。")
        put_scope("status")
        put_markdown("## 实时日志")
        put_scope("logs")

        while True:
            rows = [["模拟器", "状态", "当前任务", "下次任务", "倒计时", "上次错误"]]
            for s in schedulers:
                rows.append([
                    s.name,
                    _status_dot(s.status),
                    s.current_task or "-",
                    s.next_task or "-",
                    _fmt_next(s.next_run_at),
                    s.last_error or "-",
                ])
            with use_scope("status", clear=True):
                put_table(rows)

            with log_buffer_lock:
                entries = list(log_buffer)
            tail = entries[-LOG_TAIL:]
            with use_scope("logs", clear=True):
                for e in tail:
                    put_text(e["formatted"])

            time.sleep(REFRESH_SEC)

    return app


def serve(schedulers, port: int = 8080) -> None:
    start_server(_build_app(schedulers), port=port, debug=False, auto_open_webbrowser=True)
