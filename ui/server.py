import json
import threading
import time
from datetime import datetime

from pywebio import start_server
from pywebio.input import actions, checkbox, input, input_group
from pywebio.output import (
    put_buttons,
    put_html,
    put_markdown,
    put_scope,
    put_text,
    use_scope,
    toast,
)
from pywebio.session import run_js, set_env

from core import runtime
from core.logger import log_buffer, log_buffer_lock
from tasks import TASK_REGISTRY

REFRESH_SEC = 1
LOG_DOM_LIMIT = 300

DEFAULT_INTERVALS_MIN = {
    "粥棚": 180,
    "膜拜": 1440,
}


def _fmt_next(at: datetime | None) -> str:
    if at is None:
        return "-"
    delta = (at - datetime.now()).total_seconds()
    if delta < 0:
        return "now"
    if delta < 60:
        return "<1m"
    if delta < 3600:
        return f"{int(delta // 60)}m"
    return f"{int(delta // 3600)}h{int((delta % 3600) // 60)}m"


def _status_label(s: str) -> str:
    return {
        "starting": "⚪ 启动中",
        "idle": "🟢 待机",
        "running": "🟡 运行中",
        "stopping": "🟠 停止中",
        "stopped": "⚫ 已停止",
        "error": "🔴 错误",
    }.get(s, s)


def _handle_add() -> None:
    options = [
        {
            "label": f"{n} (默认 {DEFAULT_INTERVALS_MIN.get(n, 60)} 分钟)",
            "value": n,
            "selected": True,
        }
        for n in TASK_REGISTRY.keys()
    ]
    data = input_group("添加模拟器", [
        input("名字", name="name", required=True, placeholder="如：主号 / 小号 / 二号机"),
        input("ADB 端口", name="serial", required=True,
              value="127.0.0.1:", placeholder="例: 127.0.0.1:16512"),
        checkbox("启用的任务", name="tasks", options=options),
    ])
    if not data:
        return
    task_specs = {
        t: {"interval_minutes": DEFAULT_INTERVALS_MIN.get(t, 60)}
        for t in data["tasks"]
    }
    try:
        runtime.add_emulator(data["name"], data["serial"], task_specs)
        toast(f"已添加 {data['name']}", color="success")
    except Exception as e:
        toast(f"添加失败: {e}", color="error", duration=6)


def _handle_delete(name: str) -> None:
    ok = actions(
        f"确认删除「{name}」？\n如果它正在跑任务，会等任务结束才停止（可能要等几分钟）。",
        buttons=[
            {"label": "确认删除", "value": True, "color": "danger"},
            {"label": "取消", "value": False},
        ],
    )
    if not ok:
        return
    toast(f"正在停止 {name}...", duration=4)
    threading.Thread(target=runtime.remove_emulator, args=(name,), daemon=True).start()


_HTML_SHELL = f"""
<style>
  #status-table {{ border-collapse: collapse; width: 100%; margin: 8px 0; }}
  #status-table th, #status-table td {{ border: 1px solid #ddd; padding: 6px 10px; text-align: left; }}
  #status-table thead {{ background: #f5f5f5; }}
  #log-box {{
    max-height: 420px; overflow-y: auto;
    border: 1px solid #ddd; padding: 8px;
    font-family: Consolas, "Courier New", monospace; font-size: 12px;
    background: #fafafa; line-height: 1.5;
  }}
  #log-box .row {{ white-space: pre; }}
</style>
<table id="status-table">
  <thead>
    <tr>
      <th>模拟器</th><th>状态</th><th>当前任务</th>
      <th>下次任务</th><th>倒计时</th><th>上次错误</th>
    </tr>
  </thead>
  <tbody id="status-body"></tbody>
</table>
<h3>实时日志</h3>
<div id="log-box"></div>
<script>
window.__lastTbl = '';
window.__updateTable = function(rows) {{
  const json = JSON.stringify(rows);
  if (json === window.__lastTbl) return;
  window.__lastTbl = json;
  const body = document.getElementById('status-body');
  while (body.firstChild) body.removeChild(body.firstChild);
  for (const r of rows) {{
    const tr = document.createElement('tr');
    for (const c of r) {{
      const td = document.createElement('td');
      td.textContent = c;
      tr.appendChild(td);
    }}
    body.appendChild(tr);
  }}
  if (rows.length === 0) {{
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.colSpan = 6;
    td.style.textAlign = 'center';
    td.style.color = '#888';
    td.textContent = '当前没有模拟器，点上方按钮添加';
    tr.appendChild(td);
    body.appendChild(tr);
  }}
}};
window.__appendLogs = function(lines) {{
  const box = document.getElementById('log-box');
  const stick = box.scrollTop + box.clientHeight >= box.scrollHeight - 20;
  for (const line of lines) {{
    const div = document.createElement('div');
    div.className = 'row';
    div.textContent = line;
    box.appendChild(div);
  }}
  while (box.children.length > {LOG_DOM_LIMIT}) box.removeChild(box.firstChild);
  if (stick) box.scrollTop = box.scrollHeight;
}};
</script>
"""


def _app() -> None:
    set_env(title="AutoScript 监控")
    put_markdown("# AutoScript 监控")
    put_buttons(
        [{"label": "+ 添加模拟器", "value": "add", "color": "primary"}],
        onclick=lambda _: _handle_add(),
    )
    put_html(_HTML_SHELL)
    put_markdown("### 操作")
    put_scope("actions")

    last_action_keys: tuple = ()
    last_log_id = -1

    while True:
        snap = runtime.list_schedulers()

        rows = [
            [
                s.name,
                _status_label(s.status),
                s.current_task or "-",
                s.next_task or "-",
                _fmt_next(s.next_run_at),
                s.last_error or "-",
            ]
            for s in snap
        ]
        run_js("window.__updateTable(%s)" % json.dumps(rows, ensure_ascii=False))

        keys = tuple(s.name for s in snap)
        if keys != last_action_keys:
            last_action_keys = keys
            with use_scope("actions", clear=True):
                if not snap:
                    put_text("（无）")
                else:
                    for s in snap:
                        n = s.name
                        put_buttons(
                            [{"label": f"删除 {n}", "value": "del", "color": "danger"}],
                            onclick=lambda _, name=n: _handle_delete(name),
                            small=True,
                        )

        with log_buffer_lock:
            new_logs = [e for e in log_buffer if e["id"] > last_log_id]
        if new_logs:
            last_log_id = new_logs[-1]["id"]
            lines = [e["formatted"] for e in new_logs]
            run_js("window.__appendLogs(%s)" % json.dumps(lines, ensure_ascii=False))

        time.sleep(REFRESH_SEC)


def serve(port: int = 8080) -> None:
    start_server(_app, port=port, debug=False, auto_open_webbrowser=True)
