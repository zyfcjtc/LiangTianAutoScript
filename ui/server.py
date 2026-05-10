"""
ui/server.py — SRC-style three-column layout
  196px sidebar  |  272px task panel  |  flex-1 log
"""
import json
import time
from datetime import datetime
from pathlib import Path

from pywebio import start_server
from pywebio.input import actions, checkbox, input, input_group
from pywebio.output import put_buttons, put_html, put_scope, toast, use_scope
from pywebio.session import run_js, set_env

from core import runtime
from core.logger import log_buffer, log_buffer_lock
from tasks import TASK_REGISTRY

# ── constants ──────────────────────────────────────────────────────────────────

DEFAULT_INTERVALS_MIN = {
    "粥棚": 180,
    "膜拜": 1440,
    "建木营": 1440,
}

# ── helpers ────────────────────────────────────────────────────────────────────

def _fmt_at(at: datetime | None) -> str:
    if at is None:
        return "—"
    now = datetime.now()
    if at.date() == now.date():
        return at.strftime("%H:%M")
    if (at.date() - now.date()).days == 1:
        return f"明天 {at.strftime('%H:%M')}"
    return at.strftime("%m-%d %H:%M")


def _status_label(s: str) -> str:
    return {
        "starting": "启动中",
        "idle":     "待机",
        "running":  "运行中",
        "stopping": "停止中",
        "stopped":  "已停止",
        "error":    "错误",
    }.get(s, s)


def _status_dot_emoji(s: str) -> str:
    return {"starting": "⚪", "idle": "🟢", "running": "🟡",
            "stopping": "🟠", "stopped": "⚫", "error": "🔴"}.get(s, "⚪")


def _status_css(s: str) -> str:
    return {
        "starting": "dot-starting",
        "idle":     "dot-idle",
        "running":  "dot-running",
        "stopping": "dot-stopping",
        "stopped":  "dot-stopped",
        "error":    "dot-error",
    }.get(s, "dot-starting")


def _version() -> str:
    import sys
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) \
        else Path(__file__).parent.parent
    p = base / "version.txt"
    return p.read_text("utf-8").strip() if p.exists() else "dev"


def _emu_list_hash(snap, selected: str | None) -> tuple:
    return tuple((s.name, s.status) for s in snap) + (selected,)


def _task_hash(s) -> tuple:
    return (s.status, s.current_task,
            tuple((t.name, str(t.next_run)) for t in s.tasks))

# ── form handlers ──────────────────────────────────────────────────────────────

def _handle_add() -> None:
    all_tasks = list(TASK_REGISTRY.keys())
    fields = [
        input("名字", name="name", required=True, placeholder="如：主号 / 小号"),
        input("ADB 端口", name="serial", required=True, value="127.0.0.1:16384"),
        input("MuMu 实例编号", name="mumu_instance", type="number",
              placeholder="留空则不自动启动",
              help_text="实例 0→16384，实例 1→16416，以此类推"),
        input("游戏包名", name="package", placeholder="留空则不自动启动游戏",
              help_text="如: com.chengzhu.zcylt091.esj"),
        checkbox("启动选项", name="auto_login", options=[
            {"label": "自动启动游戏并登录",     "value": "1"},
            {"label": "跑完所有任务后自动关闭", "value": "run_once"},
        ]),
        checkbox("启用的任务", name="tasks",
                 options=[{"label": n, "value": n} for n in all_tasks]),
    ]
    for i, task_name in enumerate(all_tasks):
        default = DEFAULT_INTERVALS_MIN.get(task_name, 60)
        fields.append(input(
            f"{task_name} — 间隔（分钟）", name=f"interval_{i}",
            type="number", value=str(default), help_text="未勾选时忽略",
        ))
    data = input_group("添加模拟器", fields)
    if not data:
        return
    raw = data.get("mumu_instance")
    mumu_instance = int(raw) if raw not in (None, "") else None
    task_specs = {
        t: {"interval_minutes": int(data.get(f"interval_{i}") or DEFAULT_INTERVALS_MIN.get(t, 60))}
        for i, t in enumerate(all_tasks)
        if t in data["tasks"]
    }
    try:
        opts = data.get("auto_login") or []
        runtime.add_emulator(
            data["name"], data["serial"], task_specs,
            mumu_instance=mumu_instance,
            package=data.get("package") or None,
            auto_login="1" in opts,
            run_once="run_once" in opts,
        )
        toast(f"已添加 {data['name']}", color="success")
    except Exception as e:
        toast(f"添加失败: {e}", color="error", duration=6)


def _handle_delete(name: str) -> None:
    import threading
    ok = actions(
        f"确认删除「{name}」？",
        buttons=[
            {"label": "确认删除", "value": True,  "color": "danger"},
            {"label": "取消",     "value": False},
        ],
    )
    if ok:
        toast(f"正在停止 {name}…", duration=4)
        threading.Thread(target=runtime.remove_emulator, args=(name,), daemon=True).start()

# ── HTML generators ────────────────────────────────────────────────────────────

def _task_panel_html(s) -> str:
    dot_cls = _status_css(s.status)
    status_text = _status_label(s.status)
    err_html = f'<div class="tp-err">{s.last_error}</div>' if s.last_error else ""

    # 运行中
    if s.current_task:
        running_html = (
            f'<div class="tp-running-item">'
            f'<span class="tp-run-dot"></span>'
            f'{s.current_task}'
            f'</div>'
        )
    else:
        running_html = '<div class="tp-hint">无任务</div>'

    # 等待中
    rows = []
    for t in s.tasks:
        if t.name == s.current_task:
            continue
        rows.append(
            f'<div class="tp-row">'
            f'<span class="tp-task-name">{t.name}</span>'
            f'<span class="tp-badge">{_fmt_at(t.next_run)}</span>'
            f'</div>'
        )
    pending_html = "".join(rows) if rows else '<div class="tp-hint">无任务</div>'

    return (
        f'<div class="tp-head">'
        f'  <div class="tp-emu-name">{s.name}</div>'
        f'  <div class="tp-status-row">'
        f'    <span class="tp-dot {dot_cls}"></span>'
        f'    <span class="tp-status-text">{status_text}</span>'
        f'  </div>'
        f'{err_html}'
        f'</div>'
        f'<div class="tp-section">'
        f'  <div class="tp-section-label">运行中</div>'
        f'  {running_html}'
        f'</div>'
        f'<div class="tp-section">'
        f'  <div class="tp-section-label">等待中</div>'
        f'  {pending_html}'
        f'</div>'
    )

# ── CSS ────────────────────────────────────────────────────────────────────────

_CSS = """\
<style>
:root {
  --bg:         #f7f2eb;
  --bg-nav:     #ede4d4;
  --bg-hover:   #e4d8c4;
  --bg-active:  rgba(196, 82, 42, .10);
  --border:     #d0bfa8;
  --text:       #2a1f12;
  --text-dim:   #7a5c3a;
  --text-muted: #b09878;
  --accent:     #c4522a;
  --clr-idle:   #5a8a3a;
  --clr-run:    #c8800a;
  --clr-err:    #c03020;
}

* { box-sizing: border-box; }
html, body {
  margin: 0; padding: 0; height: 100%;
  background: var(--bg); color: var(--text);
  font-family: "Microsoft YaHei UI","Segoe UI",sans-serif;
}
.pywebio { height: 100vh !important; overflow: hidden !important; }
.pywebio-content { height: 100% !important; overflow: hidden !important;
                   padding: 0 !important; max-width: 100% !important; }

::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #484f58; }

/* ─ root grid ─ */
#pywebio-scope-root {
  display: grid;
  grid-template-rows: 46px 1fr;
  height: 100vh;
  overflow: hidden;
}

/* ─ header ─ */
#pywebio-scope-header {
  background: var(--bg-nav);
  display: flex; align-items: center;
  padding: 0 18px; gap: 10px;
  border-bottom: 1px solid var(--border);
  z-index: 10;
}
#pywebio-scope-header p { margin: 0; }
.hdr-title { font-size: 14px; font-weight: 600; color: var(--text); letter-spacing: .01em; }
.hdr-flex  { flex: 1; }
.hdr-ver   {
  font-size: 11px; color: var(--text-muted);
  border: 1px solid var(--border); padding: 2px 9px; border-radius: 20px;
}

/* ─ body row ─ */
#pywebio-scope-body {
  display: flex; overflow: hidden; height: 100%;
}

/* ─ LEFT sidebar ─ */
#pywebio-scope-emu_list {
  width: 196px; flex-shrink: 0;
  background: var(--bg-nav);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  overflow-y: auto;
}
#pywebio-scope-emu_list > div { display: flex; flex-direction: column; height: 100%; }

.el-label {
  padding: 14px 14px 5px;
  font-size: 10px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase;
  color: var(--text-muted);
}
/* emulator nav items (PyWebIO buttons) */
#pywebio-scope-emu_list .btn-group { width: 100%; display: block; margin: 0 !important; padding: 0 6px 2px; }
#pywebio-scope-emu_list .btn {
  display: flex; align-items: center; gap: 7px;
  width: 100%; padding: 7px 10px;
  background: transparent !important; border: none !important;
  border-radius: 6px !important;
  color: var(--text-dim) !important; font-size: 13px;
  text-align: left; cursor: pointer;
  transition: background .12s, color .12s;
}
#pywebio-scope-emu_list .btn:hover {
  background: var(--bg-hover) !important; color: var(--text) !important;
}
#pywebio-scope-emu_list .btn-primary {
  background: var(--bg-active) !important;
  color: #79c0ff !important;
}
.el-spacer { flex: 1; }
.el-sep    { height: 1px; background: var(--border); margin: 6px 10px; }

/* add button — 覆盖 Bootstrap secondary 灰色背景 */
#pywebio-scope-emu_list .btn-secondary,
#pywebio-scope-emu_list .btn-group,
#pywebio-scope-emu_list .btn-group > .btn {
  background: transparent !important;
  color: var(--text-dim) !important;
  box-shadow: none !important;
}

/* ─ MIDDLE task panel ─ */
#pywebio-scope-task_panel {
  width: 272px; flex-shrink: 0;
  background: var(--bg);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  overflow-y: auto;
}
#pywebio-scope-task_panel > div { display: flex; flex-direction: column; }

.tp-head {
  padding: 16px 16px 14px;
  border-bottom: 1px solid var(--border);
}
.tp-emu-name { font-size: 15px; font-weight: 700; color: var(--text); margin-bottom: 6px; }
.tp-status-row { display: flex; align-items: center; gap: 6px; }
.tp-dot {
  width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
  transition: background .3s, box-shadow .3s;
}
.dot-idle     { background: var(--clr-idle);  box-shadow: 0 0 5px var(--clr-idle); }
.dot-running  { background: var(--clr-run);   box-shadow: 0 0 5px var(--clr-run); }
.dot-starting { background: var(--text-dim); }
.dot-stopping { background: var(--text-dim); }
.dot-stopped  { background: var(--text-muted); }
.dot-error    { background: var(--clr-err);   box-shadow: 0 0 5px var(--clr-err); }
.tp-status-text { font-size: 12px; color: var(--text-dim); }
.tp-err { font-size: 12px; color: var(--clr-err); padding: 6px 0 0; }

.tp-section { padding: 12px 0 4px; }
.tp-section-label {
  font-size: 10px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase;
  color: var(--text-muted); padding: 0 16px 7px;
}

/* running task */
.tp-running-item {
  display: flex; align-items: center; gap: 9px;
  margin: 0 10px;
  padding: 8px 12px;
  background: rgba(210,153,34,.07);
  border-left: 2px solid var(--clr-run);
  border-radius: 0 6px 6px 0;
  font-size: 13px; color: var(--clr-run);
}
.tp-run-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--clr-run); flex-shrink: 0;
  animation: blink 1.6s ease-in-out infinite;
}
@keyframes blink { 0%,100% { opacity:1; } 50% { opacity:.3; } }

.tp-hint { padding: 4px 16px; font-size: 12px; color: var(--text-muted); font-style: italic; }

/* pending task rows */
.tp-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 7px 16px; transition: background .1s;
}
.tp-row:hover { background: var(--bg-hover); }
.tp-task-name { font-size: 13px; color: var(--text); }
.tp-badge {
  font-size: 11px; padding: 2px 9px; border-radius: 20px; flex-shrink: 0;
  background: rgba(68,147,248,.1); color: #79c0ff;
}

.tp-spacer { flex: 1; min-height: 12px; }

/* delete button */
#pywebio-scope-task_panel .btn-group { margin: 0 !important; padding: 8px 10px; }
#pywebio-scope-task_panel .btn-danger {
  width: 100%; border-radius: 6px !important; font-size: 12px !important;
  padding: 6px !important;
}

/* ─ RIGHT log panel ─ */
#pywebio-scope-log_panel {
  flex: 1; background: var(--bg);
  display: flex; flex-direction: column;
  overflow: hidden;
}
#pywebio-scope-log_panel > div { display: flex; flex-direction: column; height: 100%; }

.lp-header {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 16px; flex-shrink: 0;
  border-bottom: 1px solid var(--border);
  font-size: 10px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase;
  color: var(--text-muted);
}
.lp-bar { width: 3px; height: 13px; background: var(--accent); border-radius: 2px; flex-shrink: 0; }
.lp-log {
  flex: 1; overflow-y: auto; padding: 10px 20px 10px 24px;
  font-family: "Cascadia Code","Consolas","Courier New",monospace;
  font-size: 12px; color: #6a5040; line-height: 1.75;
}
.lp-log .row { white-space: pre-wrap; word-break: break-all; }
.lp-empty {
  flex: 1; display: flex; align-items: center; justify-content: center;
  font-size: 13px; color: var(--text-muted); font-style: italic;
}
</style>
"""

# ── JS ─────────────────────────────────────────────────────────────────────────

_JS = """\
<script>
(function() {
  if (window.__scInit) return;
  window.__scInit = true;
  window.__appendLog = function(line) {
    var box = document.getElementById('lp-log-box');
    if (!box) return;
    var stick = box.scrollTop + box.clientHeight >= box.scrollHeight - 30;
    var d = document.createElement('div');
    d.className = 'row'; d.textContent = line; box.appendChild(d);
    while (box.children.length > 800) box.removeChild(box.firstChild);
    if (stick) box.scrollTop = box.scrollHeight;
  };
})();
</script>
"""

# ── panel renderers ────────────────────────────────────────────────────────────

def _render_emu_list(selected: str | None, snap: list, select_fn) -> None:
    with use_scope("emu_list", clear=True):
        put_html('<div class="el-label">模拟器</div>')
        if not snap:
            put_html('<div class="tp-hint" style="padding:8px 14px">尚无模拟器</div>')
        for s in snap:
            label = f"{_status_dot_emoji(s.status)}  {s.name}"
            put_buttons(
                [{"label": label, "value": s.name,
                  "color": "primary" if s.name == selected else "secondary"}],
                onclick=lambda _, n=s.name: select_fn(n),
            )
        put_html('<div class="el-spacer"></div>')
        put_html('<div class="el-sep"></div>')
        put_buttons(
            [{"label": "＋  添加模拟器", "value": "add", "color": "secondary"}],
            onclick=lambda _: _handle_add(),
        )


def _render_task_panel(s, del_fn) -> None:
    with use_scope("task_panel", clear=True):
        if s is None:
            put_html('<div class="lp-empty">← 选择一个模拟器</div>')
            return
        put_html(_task_panel_html(s))
        put_html('<div class="tp-spacer"></div>')
        put_buttons(
            [{"label": "删除模拟器", "value": "del", "color": "danger"}],
            onclick=lambda _, n=s.name: del_fn(n),
        )


def _render_log_panel(s) -> None:
    emu_name = s.name if s else "—"
    with use_scope("log_panel", clear=True):
        put_html(
            f'<div class="lp-header">'
            f'<span class="lp-bar"></span>'
            f'日志 &mdash; {emu_name}'
            f'</div>'
            f'<div class="lp-log" id="lp-log-box"></div>'
        )
    with log_buffer_lock:
        tail = [e["formatted"] for e in log_buffer
                if e["thread"] == emu_name][-300:]
    if tail:
        run_js(f"""
          var box = document.getElementById('lp-log-box');
          if (box) {{
            {json.dumps(tail, ensure_ascii=False)}.forEach(function(l) {{
              var d = document.createElement('div');
              d.className='row'; d.textContent=l; box.appendChild(d);
            }});
            box.scrollTop = box.scrollHeight;
          }}
        """)


def _render_empty_log_panel() -> None:
    with use_scope("log_panel", clear=True):
        put_html(
            '<div class="lp-header"><span class="lp-bar"></span>日志</div>'
            '<div class="lp-empty">← 从左侧选择一个模拟器</div>'
        )

# ── main app ───────────────────────────────────────────────────────────────────

def _app() -> None:
    set_env(title="良田自动脚本", output_max_width="100%")

    put_html(_CSS)
    put_html(_JS)

    put_scope("root")
    with use_scope("root"):
        put_scope("header")
        put_scope("body")
    with use_scope("body"):
        put_scope("emu_list")
        put_scope("task_panel")
        put_scope("log_panel")

    ver = _version()
    with use_scope("header"):
        put_html(
            f'<span class="hdr-title">🌾 良田自动脚本</span>'
            f'<span class="hdr-flex"></span>'
            f'<span class="hdr-ver">v{ver}</span>'
        )

    # ── state ──────────────────────────────────────────────────────────────────
    selected:      list[str | None] = [None]
    last_emu_hash: list             = [None]
    last_task_hash:list             = [None]
    last_log_id:   list             = [-1]

    def select_emu(name: str) -> None:
        selected[0]       = name
        last_task_hash[0] = None
        last_log_id[0]    = -1
        snap = runtime.list_schedulers()
        s = next((x for x in snap if x.name == name), None)
        _render_emu_list(selected[0], snap, select_emu)
        _render_task_panel(s, _handle_delete)
        _render_log_panel(s)

    # ── initial render ─────────────────────────────────────────────────────────
    snap = runtime.list_schedulers()
    if snap:
        selected[0] = snap[0].name
    _render_emu_list(selected[0], snap, select_emu)
    s0 = next((x for x in snap if x.name == selected[0]), None)
    _render_task_panel(s0, _handle_delete)
    if s0:
        _render_log_panel(s0)
    else:
        _render_empty_log_panel()
    last_emu_hash[0]  = _emu_list_hash(snap, selected[0])
    last_task_hash[0] = _task_hash(s0) if s0 else None

    # ── polling loop ───────────────────────────────────────────────────────────
    while True:
        time.sleep(1)
        snap = runtime.list_schedulers()
        keys = tuple(s.name for s in snap)

        eh = _emu_list_hash(snap, selected[0])
        if eh != last_emu_hash[0]:
            last_emu_hash[0] = eh
            if selected[0] not in keys:
                selected[0]       = keys[0] if keys else None
                last_task_hash[0] = None
                last_log_id[0]    = -1
                s_new = next((x for x in snap if x.name == selected[0]), None)
                _render_task_panel(s_new, _handle_delete)
                if s_new:
                    _render_log_panel(s_new)
                else:
                    _render_empty_log_panel()
            _render_emu_list(selected[0], snap, select_emu)

        if selected[0]:
            s = next((x for x in snap if x.name == selected[0]), None)
            if s:
                th = _task_hash(s)
                if th != last_task_hash[0]:
                    last_task_hash[0] = th
                    _render_task_panel(s, _handle_delete)

        if selected[0]:
            emu_name = selected[0]
            with log_buffer_lock:
                new_logs = [e for e in log_buffer
                            if e["id"] > last_log_id[0]
                            and e["thread"] == emu_name]
            if new_logs:
                last_log_id[0] = new_logs[-1]["id"]
                for e in new_logs:
                    line = json.dumps(e["formatted"], ensure_ascii=False)
                    run_js(f"window.__appendLog({line})")


def serve(port: int = 8080) -> None:
    start_server(_app, port=port, debug=False, auto_open_webbrowser=True)
