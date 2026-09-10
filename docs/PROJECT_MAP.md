# Project Map

## Project Identity

- repository type: 工具仓库（非产品代码、非固件），本次不含可编译产物
- primary language(s): Python 3.13（GUI + 扫描器 + 自检）、PowerShell 5.1（安装与初始化脚本）、VBScript（启动器）
- main runtime/platform: Windows 桌面；GUI 为 tkinter，依赖系统 Python 3.13.9（自带 tkinter 8.6）
- build system or IDE: 无构建系统。改完直接运行；`selftest.py` 是唯一的验证入口（113 项、约 1 秒）

## Startup Chain

1. 用户双击 `打开工作流工具.vbs`（纯 ASCII、无 BOM，用 `fso.BuildPath` 取同目录路径，没有硬编码盘符或中文路径）。
2. VBS 以隐藏窗口方式执行 `pyw "workflow-tool.pyw"`。
3. `pyw` 解析到**系统** Python 的 `pythonw.exe`（3.13.9）—— 托管 Python 3.13.12 没有 tkinter，走错解释器会直接失败。
4. `workflow-tool.pyw` 定义模块级常量与函数，然后 `if __name__ == "__main__"` 下实例化 `WorkflowTool(tk.Tk)`。
5. `WorkflowTool.__init__()` 构建界面：项目路径输入区、场景卡片、两个 agent 的状态徽章、若干操作按钮行、右侧输出面板。
6. `mainloop()` 进入事件循环；所有动作由按钮回调触发。

模块级函数不依赖 Tk，可以脱离窗口单独加载和驱动 —— `selftest.py` 正是靠这一点在无窗口环境下做行为断言。

## Active Communication Chains

### 1. GUI 动作链（按钮 → 实际工作）

| 动作 | 实现位置 | 机制 |
| --- | --- | --- |
| 安装 / 重装 skill | `install_skill()` | **进程内 Python**：`shutil.rmtree()` 旧目录 + `shutil.copytree()` 复制源。**不走 `install-skill.ps1`** |
| 初始化项目交接文件 | `init_project()` | 进程内 Python：`shutil.copy2()` 三个模板；目标已存在则跳过 |
| 检查工程卫生 | `run_hygiene_scan()` | 进程内延迟 `import check_hygiene`，调用 `scan()` + `format_report()` |
| 运行工具箱自检 | GUI 回调 | **子进程**执行 `sys.executable selftest.py`，300 秒超时，输出回填右侧面板 |
| 打开目录 / 打开 HANDOFF | `open_in_explorer()` 等 | `subprocess.run(["explorer", ...])` |

关键区分：GUI 的安装逻辑（Python）与命令行脚本 `install-skill.ps1`（PowerShell）是**两条独立实现**，只保证结果一致（都得到与源逐字节相同的副本），不共享代码。改一边要记得对另一边。

### 2. 技能分发链

源 `skill/project-handoff-resume/`（唯一源，含 `SKILL.md` 与 `agents/openai.yaml`）
→ 复制到 `~/.codex/skills/project-handoff-resume/`（`CODEX_HOME` 可覆盖）
→ 复制到 `~/.workbuddy/skills/project-handoff-resume/`（无官方覆盖变量）。

两个 agent 的技能目录**互不可见**，不存在共享目录；两份副本必须逐字节一致，靠 `diff -r` 或自检的第 6 分区保证。

### 3. 交接文件落地链（写侧）

`templates/CODEX_PROJECT_PROMPT.md`、`templates/docs/PROJECT_MAP.md`、`templates/docs/HANDOFF.md`
→ 复制进目标工程根目录与 `docs/`。
入口有两个，结果一致：`init-project.ps1`（PowerShell）与 `init_project()`（GUI，Python）。`one-click-init-project.ps1` 用同进程 `& $initScript` 调用前者。

### 4. 交接恢复链（读侧，由 skill 定义）

新会话 → 加载 `project-handoff-resume` skill → 依次读 `CODEX_PROJECT_PROMPT.md`、`docs/PROJECT_MAP.md`、`docs/HANDOFF.md` → 从上次的 Open Question 继续，**不重新全量读仓库**。

## Core Business Objects

- `HANDOFF_FILES` —— 三份交接文件的相对路径列表，是「工程是否已接入工作流」的判据（统一由 `project_handoff_status()` 使用）。
- `AGENT_NAMES` —— 两个 agent 的名字，驱动安装目标与状态徽章。
- `SKILL_SOURCE_DIR` / `TEMPLATES_DIR` / `TEMPLATE_ROOT` —— 相对脚本自身定位的路径常量，保证工具箱整体可搬移。
- `resolve_project_path(raw)` —— 项目路径的唯一入口，返回 `Path | None`。**空白一律为 `None`**（`Path("")` 等于 `Path(".")`，否则会把 CWD 当成项目）。
- `skill_installed_map()` / `skill_installed()` —— 逐 agent 与整体的就绪状态。
- `check_hygiene.scan()` / `format_report()` —— 扫描器对外只有这两个门面，GUI 与自检都经由它们调用。

## Currently Enabled vs Present In Tree

- **运行时启用**：VBS 启动器、`workflow-tool.pyw` 全套、`check_hygiene.py`、`selftest.py`（手动或经 GUI 触发）、`install-skill.ps1`、`init-project.ps1`、`one-click-init-project.ps1`。
- **在树中但不被运行时调用**：`templates/`（被复制，不被执行）、根目录的三份交接文件（被 agent 阅读，不被程序读取）、`README.md` / `PROMPTS.md`（纯文档）。
- **不是产物目录**：本仓库没有 `build/`、`release/`、`__pycache__/`。若发现 `__pycache__` 说明有地方漏了 `sys.dont_write_bytecode` 保护。

## Known Suspicious Areas

- **`templates/` 与真实工程无法区分。** 它的内部布局和"已接入工作流的工程"完全一样，所以 `project_handoff_status(".../templates")` 会返回「完整」。GUI 指向它时会显示成可用项目并推荐续聊，实际打开的是模板文件。属于低危但真实的误判。
- **两条安装实现可能漂移。** `install_skill()`（Python，GUI 用）与 `install-skill.ps1`（PowerShell，命令行用）各自实现同一件事；自检覆盖了 Python 路径与 `.ps1` 的首次安装，但 `.ps1` 的"目标已存在时重跑"分支从未被真正执行过。
- **`check_hygiene` 的跳过列表含 `.workbuddy/`**，导致它无法检查装在 `~/.workbuddy/skills/` 下的技能 —— 而这恰恰是最常被编辑的一类文件。
- **GUI 的安装逻辑绕过了 PowerShell 脚本**，所以"GUI 能装"并不能证明"`install-skill.ps1` 能用"，反之亦然。
