# Handoff

## Current Status

工具箱功能完整、已通过端到端自测，并已初始化为 git 仓库推送到 GitHub。它自己也接入了这套交接工作流 —— 本文件与根目录的 `CODEX_PROJECT_PROMPT.md`、`docs/PROJECT_MAP.md` 就是它对自己运行 `init-project.ps1` 的产物。当前没有已知的功能缺陷，剩下的都是"未被覆盖的分支"而不是"已知会坏的地方"。

自测基线（改完任何东西都应与之一致）：

- `python selftest.py` → **113 通过 / 0 失败 / 1 跳过**
- `python check_hygiene.py .` → **0 问题**
- 两个 agent 技能目录里的副本与 `skill/project-handoff-resume/` **逐字节一致**
- 三个 `.ps1` 的 UTF-8 BOM 完好
- 仓库状态：`main` 与 `origin/main` 一致，提交依次为 `fc57771`（初始化）→ `ac909d3`（接入自身交接工作流）→ `0a2a129`（忽略 `.workbuddy/`）→ `781eb8a`（补录仓库状态与续做前提）→ 本次提交（新增 `docs/ENGINEERING_NOTES.md`）

若在有 CI 的仓库里接手：本仓库**没有** CI，推送不消耗构建分钟，可以随时直接推。

**工程知识库**：`docs/ENGINEERING_NOTES.md` 是本仓库的常驻工程笔记，装着从 `esp32_s3_eink_test` 会话里带过来的全部一手排障细节（两个真缺陷的定位过程、沙箱限制、GitHub 推送三道障碍的修法、Windows 文件卫生、GUI 验证陷阱、自检设计原则）。**本文件只给结论，细节一律查那份**。它不依赖任何外部工程，本仓库自带 —— 即使 `esp32_s3_eink_test` 出了任何问题，这套知识也不会丢。

## Update Rule

Refresh this file after substantial work. Treat work as substantial when at least one of these happened:

1. code edits were made
2. a suspected bug was confirmed or ruled out
3. multiple files were traced to complete one runtime chain
4. the next recommended investigation changed
5. the architecture understanding became meaningfully clearer

## Confirmed Findings

**架构与实现**

- GUI 的安装逻辑走**进程内 Python**（`shutil.rmtree` + `shutil.copytree`），**不调用 `install-skill.ps1`**。命令行脚本是另一条独立实现，两者只保证结果一致，不共享代码。
- `resolve_project_path()` 是整个工具箱取项目路径的唯一入口，空白/纯空格/None 一律返回 `None`，并剥掉从资源管理器粘来的包裹引号。四个边界（`""` / `"   "` / 带引号 / 正常）实测正确。
- `run_hygiene_scan()` 在 import 前后用 `sys.dont_write_bytecode` 包住，避免第一次扫描在工具箱里留下 `__pycache__`。
- GUI 自身不依赖 Tk 的部分（`agent_home`、`install_skill`、`init_project`、`project_handoff_status`、`resolve_project_path`、`run_hygiene_scan`）可脱离窗口加载并驱动 —— 自检正是靠这一点在无窗口环境下断言行为。

**已验证的行为**

- 端到端闭环在桌面一次性测试工程上跑通：初始化 → 幂等（不覆盖用户内容、mtime 不变）→ 填写交接 → 按交接续聊改代码 → 11 项测试通过 → 回写交接。
- GUI：54 项回归 + 49 项新增 + 7 项路径单元全通过；真实入口用 `runpy` + 猴补 `mainloop` 冒烟通过（窗口 mapped、按钮数量、双徽章）。
- 卫生检查正反两向通过；skill 首次安装、GUI 重装路径（含清掉刻意植入的陈旧文件）均通过。
- 启动链是程序化验证的：`打开工作流工具.vbs` → `pyw` 解析到系统 Python 3.13.9（tkinter 8.6）。**托管 Python 3.13.12 没有 tkinter。**
- 在真实工程上运行 `init-project.ps1` 成功（目标就是本仓库自己），生成的三份文件与 `templates/` 逐字节一致。
- `project_handoff_status(本工具箱)` 现在返回「完整」。
- **续做本仓库的前提**：新会话的**工作目录必须开在本仓库根目录**，再说「使用 project-handoff-resume，然后继续这个工程」。skill 读的是**相对当前会话工作目录**的三份交接文件，那句话本身不带路径 —— 在别的目录（例如 `esp32_s3_eink_test`）说同一句话，会去续做那个目录的工程。skill 未自动触发时的兜底句是「先读 CODEX_PROJECT_PROMPT.md、docs/PROJECT_MAP.md、docs/HANDOFF.md，再继续这个工程，不要从头重新阅读。」更省事：开本仓库自己的 GUI、把项目路径指向它自己，状态会显示「完整」并推荐续聊。

**仓库约定**

- `.workbuddy/` 已加入 `.gitignore`：在本目录开会话时 WorkBuddy 会生成 `.workbuddy/memory/`，属会话数据而非仓库内容。与 `esp32_s3_eink_test` 仓库的策略一致。
- 本文件与 `CODEX_PROJECT_PROMPT.md`、`docs/PROJECT_MAP.md` 的**章节标题保持英文**（对齐 `templates/` 与自检的结构检查），**正文用中文**。
- 工具箱**自己的记忆不在本目录**：`esp32_s3_eink_test` 会话的原始日志（含两个真缺陷的定位过程、沙箱限制、推送排障）本写在 `C:\Users\Admin\Desktop\esp32_s3_eink_test\.workbuddy\memory\2026-09-10.md`，但那属于那个工程的目录、随时可能被清理。**已把其中与工具箱有关的一切提炼进本仓库的 `docs/ENGINEERING_NOTES.md`**，那是权威副本；本文件只保留结论。以后复盘**只看 `docs/ENGINEERING_NOTES.md`**，不必再去翻 esp32 工程的日志。
- **本仓库自洽**：代码、skill 源、交接三件套、工程笔记全部随仓库走，不引用 `esp32_s3_eink_test` 里的任何路径。克隆本仓库即可独立续做与排障。

**修过的两个真缺陷**

（完整的定位过程、复现步骤与验证方式见 `docs/ENGINEERING_NOTES.md` §1。）

1. `one-click-init-project.ps1` 曾用**裸名 `powershell -File`** 调用兄弟脚本：名字解析不到时，在 `$ErrorActionPreference = "Stop"` 下会让整个脚本静默中断（只看到部分输出和非零退出码）。已改为同进程 `& $initScript -ProjectPath $ProjectPath`。
2. GUI 中空路径会退化成 `Path(".")`（即 GUI 进程的当前目录），于是把 CWD 当项目来报告，甚至可能往 CWD 写模板文件。已由 `resolve_project_path()` 堵住，7 处调用点全部处理 `None`。

**环境事实（会反复踩到）**

- 沙箱拦 **PowerShell 的 `Remove-Item -Recurse`（连工作区内也拦）**，但**不拦 Python 的 `shutil.rmtree`**。这是环境限制而非脚本缺陷。
- 沙箱给工具进程设 `PYTHONDONTWRITEBYTECODE=1`，会掩盖 `__pycache__` 类副作用并产出假阴性；验证这类副作用要在清掉该变量的子进程里跑。
- 沙箱会注入一个不可用的 `http_proxy`（`127.0.0.1:51798`），且 WorkBuddy 捆绑的 PortableGit 里没有任何 `git-credential-*`，而系统 gitconfig 却写着 `credential.helper=helper-selector`（指向不存在的程序，静默失败）。本仓库已在 `.git/config` 配好 `http.proxy=http://127.0.0.1:7897`（需 Clash 在跑）与指向系统 GCM 8.3 短路径的 `credential.helper`。
- 沙箱下 `git fetch` / `git push -u` **不会留下远端跟踪引用**（reflog 有记录但 ref 文件不落地），必要时手工 `mkdir -p .git/refs/remotes/origin && printf '%s\n' "$(git rev-parse HEAD)" > .git/refs/remotes/origin/main`。用户自己的终端不会遇到。
- 本仓库换行符策略：`.gitattributes` 规定仓库内统一 LF（**含 `.ps1`/`.vbs`**），只给 `.bat`/`.cmd` 预留 CRLF。**不要照抄 `esp32_s3_eink_test` 的 `.ps1 → crlf` 规则** —— 本仓库的文件由两个 agent 写出、都产 LF。

## Open Questions

1. **`install-skill.ps1` 的"目标已存在时重跑"从未真正执行过。** 沙箱拦递归删除，所以这是全套里唯一没有实测背书的分支（自检里显式标记为 SKIP，不伪装成通过）。需要在非沙箱终端手动跑一次确认。
2. **`check_hygiene.py` 扫不到 `.workbuddy/` 下的文件**，因此无法检查装在 `~/.workbuddy/skills/` 里的技能 —— 而那正是最常被编辑的一类文件。是放宽跳过规则（只跳过 `memory/`、`plugins/`），还是加一个 `--force`／"扫描根自身是 `.workbuddy` 时不跳过"的例外？
3. **`templates/` 与真实工程无法区分。** 它的内部布局和"已接入工作流的工程"完全一样，所以 `project_handoff_status(".../templates")` 会返回「完整」，GUI 会把它当可用项目并推荐续聊。要不要加标志文件，或让状态逻辑排除名为 `templates` 的目录？
4. **GUI 从未被人工双击确认过。** 启动链是程序化验证的，真机冷启动与窗口外观仍缺一次人工确认。
5. **`WORKBUDDY_HOME` 这个自检钩子是否保留。** 它不是 WorkBuddy 的官方变量，正常流程里设置它会让安装位置与实际读取位置静默脱节；目前只被自检用来重定向到临时目录。

## Recommended Next Steps

1. 在非沙箱终端跑一次 `install-skill.ps1`（目标已存在的情况），补上唯一未覆盖的分支。
2. 给 `check_hygiene.py` 增加能扫描 `.workbuddy` 下指定目录的能力（`--force` 或放宽跳过规则），让"检查已安装技能"成为可能。
3. 考虑把两条安装实现合并成一条（让 `.ps1` 只做薄封装），消除 GUI 与命令行之间的漂移风险。
4. 人工双击 `打开工作流工具.vbs`，确认冷启动、窗口尺寸与按钮换行。
5. **日常纪律**：改完任何东西 → `python selftest.py` → `python check_hygiene.py .` → 提交；若改了 `skill/` 源，还要确认两份已装副本同步。

## How To Resume In A New Chat

Use:

`使用 project-handoff-resume，然后继续这个工程。`

If the skill is unavailable, use:

`先读 CODEX_PROJECT_PROMPT.md、docs/PROJECT_MAP.md、docs/HANDOFF.md，再继续这个工程，不要从头重新阅读。`

Source repository:

`https://github.com/QRT-debug/workflow-tool`
