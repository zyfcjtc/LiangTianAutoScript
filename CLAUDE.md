# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

自动化脚本，用于手游《这城有良田》，搭配 MuMu 模拟器运行。提供 Web 监控看板（PyWebIO）。架构参考 SRC / Alas。

## Commands

```cmd
# 开发环境运行（自动建 venv、安装依赖、拉最新代码）
Start.bat

# 手动激活 venv 后运行
.venv\Scripts\python.exe main.py

# 打包成单文件 exe（需先安装 pyinstaller：.venv\Scripts\pip install pyinstaller）
build.bat
# 输出：dist/LiangtianAutoScript.exe + LiangtianAutoScript-v{ver}.zip + patch-v{ver}.zip
# 注意：build.ps1 在中文 Windows PowerShell 5.1 下有编码/分号解析问题，用 build.bat

# 测试单个任务（dev_tools/ 下的 test_*.py 均为手动集成测试，需接模拟器）
.venv\Scripts\python.exe dev_tools/test_mobai.py
```

Python 版本：3.10–3.12（pywebview 依赖 pythonnet，3.13+ 无预构建 wheels，需用 `py -3.12` 建 venv）。主要依赖见 `requirements.txt`（adbutils、opencv-python、pywebio、pywebview、rapidocr-onnxruntime）。无自动化单元测试套件。

## Architecture

### 核心层（`core/`）

- **`device.py`** — ADB 设备抽象；截图（`screenshot()`）+ 触控输入（`tap/swipe`），内置 ±4px 坐标抖动防封号
- **`template.py`** — OpenCV 模板匹配；`Button` 类绑定图片路径 + 搜索区域 + 阈值；`match()` 返回坐标；`_crop_roi()` 供 ocr.py 复用
- **`ocr.py`** — RapidOCR（ONNX）识别中文；`find_text()` 返回文本坐标
- **`ui.py`** — 高层交互；`click_button()`、`wait_until_appear()`、`click_text()`（OCR 点击）
- **`scheduler.py`** — `Scheduler`：按间隔循环执行任务，维护状态（idle / running / error）
- **`runtime.py`** — 全局单例；注册所有 `Scheduler` 实例，线程安全；`add_emulator()` 启动新模拟器线程
- **`launcher.py`** — 启动 MuMu 实例 + 等待 ADB 连接 + 自动登录游戏
- **`logger.py`** — 统一日志；500 行环形缓冲区供 Web UI 读取
- 更新检查逻辑内联于 `ui/winapp.py`（`API.check_update` / `API.download_patch`）

### 任务层（`tasks/`）

`Task` 基类（`base.py`）：`interval_minutes` + `run(ui: UI)` 抽象方法。

已实现任务：

| 文件 | 任务 | 说明 |
|------|------|------|
| `porridge.py` | 粥棚 | OCR 找粥棚入口，连点 15 次招募 NPC |
| `mobai.py` | 膜拜 | 点头像→跨服/本服榜单共 6 个标签膜拜 |
| `jianmuying.py` | 建木营 | 模板匹配 4 种资源图标，滑屏扫 3 屏采集 |

`tasks/__init__.py` 中的 `TASK_REGISTRY`（`{"任务名": TaskClass}`）是 UI 自动获取可选任务列表的唯一来源。

### Windows 桌面客户端（`ui/winapp.py` + `ui/web/index.html`）

pywebview + Edge WebView2 单文件应用，默认启动（`--webui` 降级到 PyWebIO）。
- `API` 类通过 `js_api` 暴露给前端，JS 用 `window.pywebview.api.方法名()` 调用
- 冻结态 HTML 路径：`Path(sys._MEIPASS) / "ui/web/index.html"`；version.txt 路径：`Path(sys.executable).parent`
- 启动无终端：`pythonw.exe main.py`；打包用 `--windowed --onefile`
- 外部 `tasks/` 热更新：exe 旁若有 `tasks/` 目录，`main.py` 自动插入 `sys.path[0]` 优先加载

### Web UI（`ui/server.py`）

PyWebIO 单页应用，端口默认 8080。三栏布局：模拟器列表 | 任务面板 | 实时日志。日志直接读 `logger` 环形缓冲区，`run_js()` 实现无刷新更新。

### 配置（`config.yaml`）

结构：顶层 `ui.port`、`mumu.exe`，`emulators` 列表（每项含 `name`、`serial`、`mumu_instance`、`tasks`、`auto_login`）。`runtime.py` 在增删模拟器后自动持久化写回。

### 资源文件（`assets/`）

按场景分子目录（`main/`、`common/`、`porridge/`、`jianmuying/`、`rank/` 等），命名约定 `BTN_*.png`。**截图分辨率锁定 720×1280 / DPI 240**，换分辨率需重新截图。

### 开发工具（`dev_tools/`）

- `capture.py` — 截图 + 裁剪，生成新按钮模板
- `test_*.py` — 手动集成测试，直接连接模拟器验证单任务

## 添加新任务的标准流程

1. 用 `dev_tools/capture.py` 截图，存到 `assets/{scene}/BTN_*.png`
2. 新建 `tasks/mytask.py`，继承 `Task`，实现 `run(self, ui: UI)`
3. 在 `tasks/__init__.py` 的 `TASK_REGISTRY` 中注册任务名 → 类

不需要修改 core 层或 UI 层。

## 关键约束

- MuMu 多开时 ADB 端口会变（当前已知 16512），配置变更需同步 `config.yaml`
- 点击坐标抖动（±4px）和 sleep 随机化（±15%）在 `device.py` 实现，调参应走统一常量而非在各 task 中单独调
- `run_once` 模式下所有任务执行完毕后会自动关闭游戏和模拟器（`launcher.py` + `runtime._shutdown_watcher()`）

## 已知坑

- 版本比较必须双边 `.lstrip("v")`：GitHub tag 为 `v0.2.3`，version.txt 为 `0.2.3`
- `dist/` 打包前可能被资源管理器锁定，关闭相关 Explorer 窗口再构建
- PowerShell 5.1 中 `--add-data "a;b"` 的分号会被误解析，用 `$sep=[char]59; "a${sep}b"` 绕过

## Release 产物

每次发版两个附件：`LiangtianAutoScript-v{ver}.zip`（完整，~100MB）+ `patch-v{ver}.zip`（仅 `tasks/` + `assets/`，~0.5MB，热更新用）

```cmd
gh release create vX.Y.Z "LiangtianAutoScript-vX.Y.Z.zip" "patch-vX.Y.Z.zip" --title "vX.Y.Z ..." --notes "..."
```
