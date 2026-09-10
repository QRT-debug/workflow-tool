# Project Prompt

## Purpose

这个仓库不是固件工程，而是一套给 **Codex 与 WorkBuddy 共用的「跨会话续做」工作流工具箱**，只跑在 Windows 上。

它只解决一件事：让一个新会话不必从头把仓库读一遍，而是先读 `CODEX_PROJECT_PROMPT.md` + `docs/PROJECT_MAP.md` + `docs/HANDOFF.md`，然后接着上次的结论继续。

仓库由四部分组成：

1. `skill/project-handoff-resume/` —— 唯一的 skill 源，一份源同时装进两个 agent 的技能目录。
2. 脚本层 —— `install-skill.ps1`（装 skill）、`init-project.ps1`（给工程落地三份交接文件）、`one-click-init-project.ps1`（一键串起）。
3. `templates/` —— 三份交接文件的模板，会被复制进目标工程。
4. `workflow-tool.pyw` —— tkinter GUI，把所有动作收进一个窗口，另带卫生检查与自检两个诊断按钮。

本仓库自身也使用这套工作流：根目录的 `CODEX_PROJECT_PROMPT.md` 与 `docs/` 就是它初始化自己的产物。

## Reading Priorities

1. `README.md` —— 安装步骤、目录结构、每个文件干什么。
2. `PROMPTS.md` —— 13 个场景下实际该说的话（用户主要看这份）。
3. `workflow-tool.pyw` —— GUI 门面；真正被调用的逻辑是模块级的 `resolve_project_path()` / `project_handoff_status()` / `install_skill()` / `run_hygiene_scan()`，它们不依赖 Tk。
4. `install-skill.ps1` —— 双 agent 安装路径与 `-Targets Both|Codex|WorkBuddy`。
5. `init-project.ps1` 与 `one-click-init-project.ps1` —— 交接文件的落地方式（幂等，已存在则跳过）。
6. `check_hygiene.py` —— 文本卫生扫描器，同时被 GUI 与自检复用。
7. `selftest.py` —— 113 项自检，约 1 秒；**改完工具箱任何东西之后都要跑它**。
8. `skill/project-handoff-resume/SKILL.md` —— 交接工作流本身的定义；改它的章节结构必须同步改 `templates/`。

## Runtime Facts

- **真实入口**：`打开工作流工具.vbs` → `fso.BuildPath` 拼出同目录的 `workflow-tool.pyw` → 交给 `pyw`。
- **解释器**：`pyw` 解析到系统 Python（`...\Programs\Python\Python313\pythonw.exe`，3.13.9，tkinter 8.6）。**托管 Python 3.13.12 没有 tkinter**。
- **主循环**：`workflow-tool.pyw` 中 `WorkflowTool(tk.Tk).mainloop()`。
- **可脱离 Tk 驱动的模块级函数**：`agent_home()`、`skill_target_dir()`、`skill_installed_map()`、`install_skill()`、`project_handoff_status()`、`resolve_project_path()`、`init_project()`、`run_hygiene_scan()`。
- **技能安装点**：Codex 用 `~/.codex/skills/<name>`（`CODEX_HOME` 可覆盖）；WorkBuddy 用 `~/.workbuddy/skills/<name>`（**没有官方覆盖变量**）。工程级还有 `{project}/.workbuddy/skills/`。
- **git 远端**：`https://github.com/QRT-debug/workflow-tool.git`，分支 `main`。

## Important Distinctions

- `templates/` 下那三份是**模板**；根目录那三份是**本仓库自己的实例**。改模板的动机通常是要影响所有新初始化的工程，改根目录的只影响本仓库。
- `skill/project-handoff-resume/` 是**唯一源**，两个技能目录里都是副本。改了源必须重跑 `install-skill.ps1` 或用 `diff -r` 核对，否则 agent 读到旧版。
- `WORKBUDDY_HOME` **不是** WorkBuddy 的官方变量，它只是 `selftest.py` 用来把安装目标重定向到临时目录的自检钩子。别在正常流程里设它，否则装到哪和读到哪会静默不一致。
- `selftest.py` 的 fixture 全建在系统临时目录，安装类用例结束会还原 `CODEX_HOME`/`WORKBUDDY_HOME` —— 它**不碰真实工程，也不碰真实技能安装**。
- README.md 是英文、PROMPTS.md 是中文，这是历史状态而非刻意设计；新增文档可自行选择，保持章节标题英文即可与模板结构对齐。

## Watchouts

- **`.ps1` 改完必须复检 UTF-8 BOM。** 含中文的 `.ps1` 缺 BOM 时 PowerShell 5.1 按 GBK 解析，中文注释会吞掉换行并在**后续行**报出误导性语法错误。本环境的 `Write` 工具会清 BOM、`Edit` 会保留，所以"整文件重写"最容易翻车。复检：`head -c 3 x.ps1 | od -An -tx1` 应为 `ef bb bf`。
- **空路径会退化成当前目录。** `Path("")` 等于 `Path(".")`。任何取项目路径的代码都必须走 `resolve_project_path()`，它把空白/纯空格/None 统一变成 `None`，并顺带剥掉从资源管理器复制来的包裹引号。
- **托管 Python 没有 tkinter**，验证 GUI 必须用系统 Python，否则误报 `No module named 'tkinter'`。
- **沙箱拦 PowerShell 的 `Remove-Item -Recurse`（连工作区内也拦）**，但不拦 Python 的 `shutil.rmtree`。后果：`install-skill.ps1` 的"目标已存在时重跑"在沙箱里测不了，而 GUI 的 Python 重装路径可以正常测。这是环境限制，不是脚本缺陷，别去"修"脚本。
- **沙箱给工具进程设 `PYTHONDONTWRITEBYTECODE=1`**，会掩盖 `__pycache__` 类副作用并产出假阴性；验证这类副作用必须在子进程里清掉该变量再跑。
- **`check_hygiene.py` 的跳过列表含 `.workbuddy/`**，所以扫不到装在 `~/.workbuddy/skills/` 下的技能。要检查已安装的 skill 得先复制到别处。
- **推送 GitHub 依赖仓库级 git 配置。** 沙箱会注入一个不可用的 `http_proxy`（表现为 `schannel: server closed abruptly` 或 `CONNECT tunnel failed, response 502`），且 WorkBuddy 捆绑的 PortableGit 里没有任何 `git-credential-*`，而系统 gitconfig 却写着 `credential.helper=helper-selector`（指向不存在的程序，静默失败）。本仓库已在 `.git/config` 配好：`http.proxy=http://127.0.0.1:7897`（需要 Clash 在跑）+ `credential.helper` 指向系统 GCM 的 8.3 短路径。推送命令还要 `env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy git ...`。
- **换行符策略与 `esp32_s3_eink_test` 有意不同。** 本仓库 `.gitattributes` 规定仓库内统一 LF（**含 `.ps1`/`.vbs`**），只给 `.bat`/`.cmd` 预留 CRLF。原因：本仓库的文件由两个 agent 写出、都产 LF，钉成 CRLF 会让 git 每次检出都改写文件。别照抄那边的 `.ps1 → crlf` 规则。
- **别用 bash 的 `grep -c $'\r$'` 判断换行符**（`\r` 会在传输中损坏，曾把纯 LF 的整套文件报成 CRLF）；用 `git ls-files --eol` 或 `head -2 f | od -c`。
- **验证类命令不要串在管道下游**：`timeout N git fetch | head -3` 会让 `head` 提前关管道、git 中途夭折，你要查的副作用就悄悄丢了。

## Continuation Workflow

At the start of a new conversation:

1. If the local skill `project-handoff-resume` is available, use it.
2. Read this file.
3. Read `docs/PROJECT_MAP.md`.
4. Read `docs/HANDOFF.md`.
5. Continue from the last open question instead of restarting repository discovery.

## Closeout Workflow

After substantial work, refresh repository memory before ending the turn:

1. Update `docs/HANDOFF.md` if findings, open questions, or next steps changed.
2. Update `docs/PROJECT_MAP.md` if stable architecture understanding changed.
3. Update this file only if the reading order or workflow changed.
