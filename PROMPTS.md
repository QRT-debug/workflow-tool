# 提示词指南

这个文件是给你直接复制使用的提示词清单，适合在不同电脑、不同项目里复用这套 Codex / WorkBuddy 通用工作流。两个智能体共用同一套交接文件和同一句续聊口令，不需要分开记。

## 1. 新电脑，第一次装好之后

在运行完 `install-skill.ps1` 之后（默认会把 skill 同时装给 Codex 和 WorkBuddy），打开 Codex 或 WorkBuddy 并进入你的工程目录，第一句直接发：

```text
使用 project-handoff-resume，然后继续这个工程。
```

## 2. 新项目，刚运行完 init-project.ps1 之后

如果模板文件刚创建出来，还没填内容，用这句：

```text
先帮助我填写 CODEX_PROJECT_PROMPT.md、docs/PROJECT_MAP.md、docs/HANDOFF.md。
请先阅读这个工程的入口文件、主流程和关键模块，然后把这三个文件初始化成可续聊状态。
```

## 3. 继续一个已经做过的项目

最常用的标准开场：

```text
使用 project-handoff-resume，然后继续这个工程。
```

更强一点的版本：

```text
使用 project-handoff-resume，然后继续这个工程。
先读 CODEX_PROJECT_PROMPT.md、docs/PROJECT_MAP.md、docs/HANDOFF.md。
不要从头重新扫描整个仓库，先从 HANDOFF 里的 open questions 或 next steps 开始。
```

## 4. 如果 skill 当前不可用

就直接用纯文本版：

```text
先读 CODEX_PROJECT_PROMPT.md、docs/PROJECT_MAP.md、docs/HANDOFF.md，再继续这个工程，不要从头重新阅读。
```

## 5. 只继续追某一个问题

如果你想把范围收紧，用这句：

```text
使用 project-handoff-resume，然后继续这个工程。
这次只继续追踪 HANDOFF 里列出的第一个 open question。
给我代码级结论，并更新 HANDOFF。
```

## 6. 继续并直接实现修复

如果你希望恢复上下文后直接干活，用这句：

```text
使用 project-handoff-resume，然后继续这个工程。
先根据 HANDOFF 恢复上下文，然后直接实现当前最优先的修复项。
做完后更新 docs/HANDOFF.md，必要时同步 docs/PROJECT_MAP.md。
```

## 7. 结束这一轮工作前

如果你准备换对话、换任务，先用这句收尾：

```text
在结束这轮之前，请刷新 docs/HANDOFF.md。
如果架构理解有变化，也同步更新 docs/PROJECT_MAP.md。
最后告诉我这次更新了哪些交接信息。
```

## 8. 用 review 模式继续

如果这次重点不是改代码，而是做审查，用这句：

```text
使用 project-handoff-resume，然后继续这个工程。
这次按 review 模式工作，先看 HANDOFF 里的当前疑点，优先找 bug、风险、回归和缺失测试。
```

## 9. 把这套工作流迁移到另一台电脑

如果你已经把整个模板包复制到新电脑上：

1. 先运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\install-skill.ps1
```

2. 再给某个项目初始化模板：

```powershell
powershell -ExecutionPolicy Bypass -File .\init-project.ps1 -ProjectPath "C:\path\to\your\repo"
```

3. 然后在 Codex 或 WorkBuddy 里开新对话，第一句发：

```text
使用 project-handoff-resume，然后继续这个工程。
```

## 10. 如果你只想改一个项目路径就完成初始化

可以直接运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\one-click-init-project.ps1 -ProjectPath "C:\path\to\your\repo"
```

如果你愿意，也可以直接编辑这个文件顶部的默认 `ProjectPath`，以后双击或重复运行都行。

## 11. 最推荐的长期习惯

长期项目建议一直按这个节奏走：

1. 第一次先初始化项目交接文件。
2. 每次新对话都用续聊提示词开场。
3. 每做完一轮较大的工作，就让 Codex 或 WorkBuddy 刷新 `docs/HANDOFF.md`。
4. 把 `docs/HANDOFF.md` 当作当前工作记忆，把 `docs/PROJECT_MAP.md` 当作长期架构记忆。
5. 提交前点一次「检查工程卫生」，别让控制字符或编码问题混进版本库。

## 12. 提交前跑一遍工程卫生检查

交接文件、README、模板这类文本最容易在反复改写中偷偷坏掉（代码围栏被压成反引号加 TAB、字符被退格吃掉、`.ps1` 少了 BOM 导致中文乱码）。提交前在工具箱目录跑：

```powershell
python .\check_hygiene.py "C:\path\to\your\repo"
```

也可以不开终端：在 `workflow-tool.pyw` 里选好项目目录，点「检查工程卫生」，报告会直接显示在右侧输出区。退出码为 1 说明有文件需要修。

另外，如果你改动过工具箱本身（脚本、模板、skill），点一次「运行工具箱自检」确认没弄坏东西——它会把 GUI 按钮、初始化、卫生检查、skill 安装等都跑一遍。

## 13. 一句话速查

如果你只想记住一句，记这个就够了：

```text
使用 project-handoff-resume，然后继续这个工程。
```
