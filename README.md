# Codex / WorkBuddy Workflow Template

This package is a portable continuity workflow for large projects. It is shared by two agents: **Codex** and **WorkBuddy**.

It contains:

- a reusable local skill: `project-handoff-resume`
- a skill installer that installs the skill for both agents
- project handoff templates for any repository
- a project initializer that copies those templates into a target repository
- a one-line project bootstrap script: `one-click-init-project.ps1`
- a double-click GUI tool: `workflow-tool.pyw`
- a launcher: `打开工作流工具.vbs`
- a copy-paste prompt guide: `PROMPTS.md`
- a text-hygiene checker: `check_hygiene.py`
- a self-test: `selftest.py`

## Where the skill gets installed

There is a single skill source, and it is copied to both agents so the two copies stay identical:

- Codex: `~/.codex/skills/project-handoff-resume/`, or `%CODEX_HOME%/skills/project-handoff-resume/` when `CODEX_HOME` is set. `CODEX_HOME` is officially supported by Codex.
- WorkBuddy: `~/.workbuddy/skills/project-handoff-resume/`. WorkBuddy reads user-level skills only from this path, and project-level skills from `{project}/.workbuddy/skills/`. There is no official WorkBuddy home environment variable, so leave the installer's `WORKBUDDY_HOME` override unset in normal use.

The two agents do not share a skill directory, which is why the installer writes to both places. After editing the source copy in this toolbox, re-run the installer so both agents pick up the change.

## Typical setup on a new computer

1. Install the skill for both agents:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-skill.ps1
```

Install for only one agent when that is intentional:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-skill.ps1 -Targets Codex
powershell -ExecutionPolicy Bypass -File .\install-skill.ps1 -Targets WorkBuddy
```

If you do not want to type commands, just double-click:

- `workflow-tool.pyw`
- or `打开工作流工具.vbs`

Inside the GUI, choose one of these cases first:

- same computer + same project
- same computer + different project
- new computer

The status card shows the Codex and WorkBuddy skill status separately, and the main install button writes to both at once.

2. Initialize a project:

```powershell
powershell -ExecutionPolicy Bypass -File .\init-project.ps1 -ProjectPath "C:\path\to\your\repo"
```

If you prefer changing only one path and reusing the same command, use:

```powershell
powershell -ExecutionPolicy Bypass -File .\one-click-init-project.ps1 -ProjectPath "C:\path\to\your\repo"
```

3. Open Codex or WorkBuddy in that project and start a new chat with:

```text
使用 project-handoff-resume，然后继续这个工程。
```

For more ready-to-use prompt examples, see [PROMPTS.md](C:/Users/Admin/Codex工作流工具箱/PROMPTS.md).

## What gets added to a project

- `CODEX_PROJECT_PROMPT.md`
- `docs/PROJECT_MAP.md`
- `docs/HANDOFF.md`

The handoff file names stay unchanged, `CODEX_PROJECT_PROMPT.md` included, so one repository works with every agent without renaming anything. Those files are the project memory. The skill is the reusable workflow for reading and maintaining that memory.

## Text hygiene check

`check_hygiene.py` scans a repository for the damage that silently corrupts agent-written files:

- control characters: backspace `0x08`, lone CR, and a backtick followed by a TAB (a collapsed ```` ``` ```` fence)
- bytes that are not valid UTF-8
- unclosed Markdown code fences
- `.ps1` files that contain non-ASCII text but no UTF-8 BOM, which mis-decodes under Windows PowerShell 5.1

Run it from a terminal:

```powershell
python .\check_hygiene.py "C:\path\to\your\repo"
```

It prints a per-file report and exits with code `1` when anything is found, so it can be wired into a hook or CI step. Generated trees such as `build/`, `release/`, `__pycache__/`, `.git/`, and `.workbuddy/` are skipped.

Inside the GUI, use the **检查工程卫生** button in the project card. It scans the currently selected project directory and writes the same report into the output panel.

## Self-test

`selftest.py` verifies the whole toolbox, not your project. Run it after editing anything in this folder:

```powershell
python .\selftest.py          # or -v for per-case detail
```

Or press **运行工具箱自检** in the GUI, which runs it in a separate process and prints the report into the output panel.

It covers:

- the three `.ps1` files keep their UTF-8 BOM
- the skill's `Preferred Handoff Shape` list and the `docs/HANDOFF.md` template list the same sections in the same order
- both installed skill copies are byte-identical to the source
- `check_hygiene.py` still catches all four defect classes, and still reports a clean tree as clean
- `init_project()` reproduces the templates byte-for-byte, is idempotent, and refuses bad paths
- the GUI's buttons, project-status branches, recommended-action branches, clipboard actions, and the hygiene button in both directions
- skill install, and that re-installing removes a stale leftover file

It never touches your real projects: every case builds a throwaway project under the system temp directory, and the install cases point `CODEX_HOME` / `WORKBUDDY_HOME` at a temp directory and restore them afterwards.

Exit codes: `0` all passed, `1` something failed, `2` the interpreter cannot run it (for example no tkinter — use `pyw` or the GUI button in that case).

One case is skipped by design under a restricted shell: re-running `install-skill.ps1` when the target directory already exists, because it removes the target tree recursively. Verify that one by hand.

## Notes

- `agents/openai.yaml` inside the skill is Codex-only interface metadata. WorkBuddy ignores it, so copying it is harmless.
- The same resume prompt works in both agents; no per-agent prompt variant is needed.
