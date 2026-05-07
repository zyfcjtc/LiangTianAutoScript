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
    put_table,
    put_text,
    toast,
    use_scope,
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
    "建木营": 1440,
}


def _fmt_at(at: datetime | None) -> str:
    if at is None:
        return "-"
    now = datetime.now()
    if at.date() == now.date():
        return at.strftime("%H:%M")
    if (at.date() - now.date()).days == 1:
        return f"明天 {at.strftime('%H:%M')}"
    return at.strftime("%m-%d %H:%M")


def _status_label(s: str) -> str:
    return {
        "starting": "⚪ 启动中",
        "idle": "🟢 待机",
        "running": "🟡 运行中",
        "stopping": "🟠 停止中",
        "stopped": "⚫ 已停止",
        "error": "🔴 错误",
    }.get(s, s)


def _table_hash(snap) -> tuple:
    return tuple(
        (
            s.name, s.status, s.current_task, s.next_task,
            _fmt_at(s.next_run_at), s.last_error,
        )
        for s in snap
    )


def _handle_add() -> None:
    all_tasks = list(TASK_REGISTRY.keys())
    fields = [
        input("名字", name="name", required=True, placeholder="如：主号 / 小号 / 二号机"),
        input("ADB 端口", name="serial", required=True,
              value="127.0.0.1:", placeholder="例: 127.0.0.1:16512"),
        input("MuMu 实例编号", name="mumu_instance", type="number",
              placeholder="留空则不自动启动",
              help_text="实例 0 → 端口 16384，实例 1 → 16416，以此类推"),
        input("游戏包名", name="package",
              placeholder="留空则不自动启动游戏",
              help_text="如: com.chengzhu.zcylt091.esj"),
        checkbox("启动选项", name="auto_login", options=[
            {"label": "自动启动游戏并登录", "value": "1"},
        ], value=["1"]),
        checkbox("启用的任务", name="tasks", options=[
            {"label": n, "value": n} for n in all_tasks
        ]),
    ]
    for i, task_name in enumerate(all_tasks):
        default = DEFAULT_INTERVALS_MIN.get(task_name, 60)
        fields.append(input(
            f"{task_name} — 间隔（分钟）",
            name=f"interval_{i}",
            type="number",
            value=str(default),
            help_text="未勾选时忽略",
        ))
    data = input_group("添加模拟器", fields)
    if not data:
        return
    raw_instance = data.get("mumu_instance")
    mumu_instance = int(raw_instance) if raw_instance not in (None, "") else None
    task_specs = {
        t: {"interval_minutes": int(data.get(f"interval_{i}") or DEFAULT_INTERVALS_MIN.get(t, 60))}
        for i, t in enumerate(all_tasks)
        if t in data["tasks"]
    }
    try:
        package = data.get("package") or None
        auto_login = "1" in (data.get("auto_login") or [])
        runtime.add_emulator(
            data["name"], data["serial"], task_specs,
            mumu_instance=mumu_instance, package=package, auto_login=auto_login,
        )
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


_LOG_HTML = """
<style>
  #log-tabs { display: flex; gap: 0; margin-top: 8px; flex-wrap: wrap; }
  #log-tabs button {
    padding: 6px 14px; border: 1px solid #ccc; border-bottom: none;
    background: #f0f0f0; cursor: pointer; font-size: 13px;
    margin-right: 2px; border-radius: 4px 4px 0 0;
  }
  #log-tabs button.active { background: white; font-weight: bold; position: relative; top: 1px; }
  .log-box {
    max-height: 420px; overflow-y: auto;
    border: 1px solid #ccc; padding: 8px;
    font-family: Consolas, "Courier New", monospace; font-size: 12px;
    background: #fafafa; line-height: 1.5;
  }
  .log-box .row { white-space: pre; }
</style>
<div id="log-tabs"></div>
<div id="log-content">
  <div data-tab="all" class="log-box"></div>
</div>
<script>
(function() {
  if (window.__logInit) return;
  window.__logInit = true;
  window.__activeTab = 'all';
  window.__LOG_LIMIT = 300;

  function append(tab, line) {
    const box = document.querySelector('#log-content .log-box[data-tab="' + CSS.escape(tab) + '"]');
    if (!box) return;
    const stick = box.scrollTop + box.clientHeight >= box.scrollHeight - 20;
    const div = document.createElement('div');
    div.className = 'row';
    div.textContent = line;
    box.appendChild(div);
    while (box.children.length > window.__LOG_LIMIT) box.removeChild(box.firstChild);
    if (stick && box.style.display !== 'none') box.scrollTop = box.scrollHeight;
  }

  window.__switchTab = function(name) {
    window.__activeTab = name;
    document.querySelectorAll('#log-tabs button').forEach(b =>
      b.classList.toggle('active', b.dataset.tab === name));
    document.querySelectorAll('#log-content .log-box').forEach(b =>
      b.style.display = (b.dataset.tab === name) ? '' : 'none');
    const active = document.querySelector('#log-content .log-box[data-tab="' + CSS.escape(name) + '"]');
    if (active) active.scrollTop = active.scrollHeight;
  };

  window.__appendLogs = function(entries) {
    for (const e of entries) {
      append('all', e.formatted);
      if (e.thread && document.querySelector('#log-content .log-box[data-tab="' + CSS.escape(e.thread) + '"]')) {
        append(e.thread, e.formatted);
      }
    }
  };

  window.__syncTabs = function(names) {
    const tabsEl = document.getElementById('log-tabs');
    const contentEl = document.getElementById('log-content');
    if (!tabsEl.querySelector('button[data-tab="all"]')) {
      const btn = document.createElement('button');
      btn.dataset.tab = 'all';
      btn.textContent = '全部';
      btn.classList.add('active');
      btn.onclick = () => window.__switchTab('all');
      tabsEl.insertBefore(btn, tabsEl.firstChild);
    }
    const wanted = new Set(['all', ...names]);
    tabsEl.querySelectorAll('button').forEach(b => {
      if (!wanted.has(b.dataset.tab)) b.remove();
    });
    contentEl.querySelectorAll('.log-box').forEach(b => {
      if (!wanted.has(b.dataset.tab)) b.remove();
    });
    for (const n of names) {
      if (!tabsEl.querySelector('button[data-tab="' + CSS.escape(n) + '"]')) {
        const btn = document.createElement('button');
        btn.dataset.tab = n;
        btn.textContent = n;
        btn.onclick = () => window.__switchTab(n);
        tabsEl.appendChild(btn);
      }
      if (!contentEl.querySelector('.log-box[data-tab="' + CSS.escape(n) + '"]')) {
        const box = document.createElement('div');
        box.dataset.tab = n;
        box.className = 'log-box';
        box.style.display = 'none';
        contentEl.appendChild(box);
      }
    }
    if (!wanted.has(window.__activeTab)) window.__switchTab('all');
  };
})();
</script>
"""


def _app() -> None:
    set_env(title="AutoScript 监控")
    put_markdown("# AutoScript 监控")
    put_buttons(
        [{"label": "+ 添加模拟器", "value": "add", "color": "primary"}],
        onclick=lambda _: _handle_add(),
    )
    put_scope("status_table")
    put_markdown("### 实时日志")
    put_html(_LOG_HTML)

    last_table_hash: tuple | None = None
    last_emu_keys: tuple = ()
    last_log_id = -1

    while True:
        snap = runtime.list_schedulers()

        keys = tuple(s.name for s in snap)
        if keys != last_emu_keys:
            last_emu_keys = keys
            run_js("window.__syncTabs(%s)" % json.dumps(list(keys), ensure_ascii=False))

        h = _table_hash(snap)
        if h != last_table_hash:
            last_table_hash = h
            with use_scope("status_table", clear=True):
                if not snap:
                    put_text("当前没有模拟器，点上方按钮添加")
                else:
                    rows = [["模拟器", "状态", "当前任务", "下次任务", "下次时间", "上次错误", ""]]
                    for s in snap:
                        name = s.name
                        rows.append([
                            name,
                            _status_label(s.status),
                            s.current_task or "-",
                            s.next_task or "-",
                            _fmt_at(s.next_run_at),
                            s.last_error or "-",
                            put_buttons(
                                [{"label": "删除", "value": "del", "color": "danger"}],
                                onclick=lambda _, n=name: _handle_delete(n),
                                small=True,
                            ),
                        ])
                    put_table(rows)

        with log_buffer_lock:
            new_logs = [e for e in log_buffer if e["id"] > last_log_id]
        if new_logs:
            last_log_id = new_logs[-1]["id"]
            entries = [{"thread": e["thread"], "formatted": e["formatted"]} for e in new_logs]
            run_js("window.__appendLogs(%s)" % json.dumps(entries, ensure_ascii=False))

        time.sleep(REFRESH_SEC)


def serve(port: int = 8080) -> None:
    start_server(_app, port=port, debug=False, auto_open_webbrowser=True)
