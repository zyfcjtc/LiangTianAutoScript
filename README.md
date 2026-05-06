# 良田自动脚本

为「这城有良田」做的自动化日常脚本，跑在 MuMu 模拟器上，自带 Web 监控面板。

---

## 现已支持

- ✅ **粥棚自动招揽流民**（默认每 3 小时跑一次）
- ✅ **个人面板膜拜**：跨服榜 + 排行榜，6 个 tab 全自动（每天一次）
- ✅ **建木营资源收集**：自动扫描并点击粮草 / 木材 / 金矿 / 精铁收集图标（每天一次）
- ✅ **多模拟器并行**：每个模拟器独立线程 + 独立日志页签
- ✅ **Web 监控面板**：实时状态、按模拟器分页签查看日志、UI 加/删模拟器
- ✅ **自定义任务间隔**：添加模拟器时可为每个任务单独设置执行间隔
- ✅ **防机检测**：点击位置 ±4px 抖动、sleep ±15% 抖动

## 规划中

- [ ] 政务派遣（含按角色筛选）
- [ ] 缉盗 / 打山匪

---

## 普通用户：用 .exe

### 准备 MuMu

1. 安装 MuMu 12 模拟器并启动「这城有良田」
2. 开启 ADB 调试：MuMu 设置 → 其他设置 → **启用 ADB 调试**
3. **锁定分辨率为手机版 720×1280, DPI 240**——所有按钮素材都基于这个分辨率，改了就废
4. 找 ADB 端口：默认 `127.0.0.1:16384`；多开实例每个 +32（16416 / 16448 / ...）

```cmd
netstat -ano | findstr "1638 1641 1644 1647 1651 1654 1657 1660"
```
能看到所有 MuMu 实例的 ADB 端口。

### 启动

1. 从 [Releases](../../releases) 下载最新版 `LiangtianAutoScript-vX.X.X.zip`
2. 解压到任意位置
3. 双击 `LiangtianAutoScript.exe`
4. 黑窗口出现后等 10-20 秒（首次解压依赖会慢），浏览器自动开 `http://127.0.0.1:8080`
5. UI 里点 **+ 添加模拟器**，填名字 + 端口、勾选任务 → 确认

提示：

- **黑窗口不能关**，关了脚本就停。浏览器关了不影响后台运行
- UI 里加的模拟器**重启后会丢**，要永久保留请编辑 `config.yaml`

### 停止

关掉黑色 cmd 窗口即可。

---

## 开发者：从源码运行

需要 Python 3.10+。

```cmd
git clone https://github.com/zyfcjtc/LiangtianAutoScript.git
cd LiangtianAutoScript
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python main.py
```

## 开发者：打包 .exe

```cmd
.venv\Scripts\activate.bat
pip install pyinstaller
pyinstaller --onefile --name LiangtianAutoScript --add-data "assets;assets" --collect-all pywebio --collect-all adbutils main.py
copy config.yaml dist\
```

输出 `dist/LiangtianAutoScript.exe` (~70 MB)。

PowerShell 用户也可以跑 `build.ps1`（需要先放行执行策略：`Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`）。

## 加新任务

整体流程已经稳定，加新任务只是套娃：

1. 用 `python -m dev_tools.capture` 截游戏按钮，按 `场景/BTN_动作` 命名（如 `porridge/BTN_COLLECT`）
2. 在 `tasks/` 下新建 `xxx.py`，参考 [tasks/porridge.py](tasks/porridge.py) 或 [tasks/mobai.py](tasks/mobai.py)
3. 在 [tasks/\_\_init\_\_.py](tasks/__init__.py) 的 `TASK_REGISTRY` 里注册任务名 → 类
4. UI 添加模拟器时就能勾选这个新任务了

---

## 项目结构

```
core/         核心框架 (设备 / 模板匹配 / 调度器 / 运行时)
tasks/        游戏任务实现
ui/           PyWebIO Web 监控面板
assets/       按钮图片素材
dev_tools/    截图 / 调试工具
config.yaml   启动时加载的模拟器配置
```

## 技术栈

- Python 3.10+
- [adbutils](https://github.com/openatx/adbutils) — 设备通信
- [opencv-python](https://github.com/opencv/opencv-python) — 模板匹配
- [PyWebIO](https://github.com/pywebio/PyWebIO) — 监控 UI
- [PyInstaller](https://pyinstaller.org/) — 打包

## 致谢 / 关于 Alas

本项目的整体架构（设备抽象 → 模板匹配 → Page 状态机 → 任务调度器 → Web 监控）灵感来自以下两个开源项目：

- [**StarRailCopilot (SRC)**](https://github.com/LmeSzinc/StarRailCopilot) — 崩坏：星穹铁道的自动化脚本，本项目最直接的参考来源
- [**AzurLaneAutoScript (Alas)**](https://github.com/LmeSzinc/AzurLaneAutoScript) — SRC 的前身，开创了这一类「截图—识别—点击—调度」工程框架的工程范式

需要说明：

- **本项目不是 SRC / Alas 的 fork**，没有复用其任何代码
- 只是吸收了它们成熟的设计思想，例如：
  - `Button` 对象绑定模板图 + `search_area` 限定区域的素材组织方式
  - 用 `Page` 状态机做 UI 间寻路（虽然「这城有良田」简单到目前还没用上）
  - 多模拟器各跑一个调度线程的并发模型
- 从零用 Python 重写，针对「这城有良田」这种 2D 模拟经营游戏做了大幅**简化**：不需要小地图单应性变换、不需要训练数字 OCR、不需要复杂的 OCR 模型

如果你想做更复杂的游戏（崩铁 / 碧蓝航线 / 原神 / 明日方舟…），**强烈建议直接读 SRC / Alas 的实现**，比看本项目收获大得多。

## License

GPL-3.0 — 详见 [LICENSE](LICENSE)。

```
Copyright (C) 2026 zyfcjtc

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
```

## 免责声明

仅供个人学习与自用。游戏内自动化可能违反相关服务条款，使用风险自负。本项目不会提供任何破解、反调试、外挂功能。
