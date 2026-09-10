---
name: project-handoff-resume
description: Restore project context from repository-maintained handoff files before doing fresh exploration, then continue the active task and refresh those files afterwards. Works with both Codex and WorkBuddy. Use when the repository keeps CODEX_PROJECT_PROMPT.md, docs/PROJECT_MAP.md, or docs/HANDOFF.md; when the user says "使用 project-handoff-resume"、"继续这个工程"、"接着上次继续"、"pick up where we left off"、"resume this project"; or when the user asks to resume a large project without re-reading the whole codebase from scratch.
---

# Project Handoff Resume

## Overview

This skill restores project context from repository-maintained handoff files before doing fresh exploration. It is for long-running codebase work where the agent should resume from prior findings, open questions, and the agreed workflow instead of rebuilding context from zero.

The workflow is agent-neutral: the same instructions drive Codex and WorkBuddy, and the handoff files they read and maintain are identical. Only the skill install location differs.

## When To Use

Use this skill when any of these are true:

- The repository contains `CODEX_PROJECT_PROMPT.md`.
- The repository contains `docs/PROJECT_MAP.md` or `docs/HANDOFF.md`.
- The user says things like "继续这个工程", "接着上次继续", "使用 project-handoff-resume", "continue this project", "pick up where we left off", "resume analysis", or "don't reread everything from scratch".
- The codebase is large enough that repeated rediscovery wastes time or context window.

## Resume Workflow

Follow this order:

1. Look for these files in the repository root:
   - `CODEX_PROJECT_PROMPT.md`
   - `docs/PROJECT_MAP.md`
   - `docs/HANDOFF.md`
2. Read them in that order when present.
3. Treat them as the starting context unless direct code inspection contradicts them.
4. Continue from the latest open question or unfinished task in `docs/HANDOFF.md`.
5. Only read additional source files needed for the active path; do not restart broad repository discovery unless the handoff files are missing or obviously stale.

## Reading Rules

- Prefer the handoff files over conversation memory when resuming in a new chat.
- Prefer concrete file and function references over prose summaries.
- If handoff files and code disagree, trust the code and record the correction.
- If only one or two handoff files exist, use what is available and continue.
- Handoff file names stay as they are, `CODEX_PROJECT_PROMPT.md` included, so one repository works with every agent without renaming anything.

## Maintenance Rules

After substantial work, refresh the repository memory:

1. Update `docs/HANDOFF.md` when findings, open questions, or next steps changed.
2. Update `docs/PROJECT_MAP.md` when stable architecture understanding changed.
3. Update `CODEX_PROJECT_PROMPT.md` only when the default reading order or repository workflow changed.
4. Keep updates concise and additive; do not turn them into verbose changelogs.

Treat work as substantial when any of these happened:

- multiple files were inspected to answer one codepath question
- any code was edited
- a suspected bug was confirmed or ruled out
- the next recommended investigation changed
- the architecture understanding became meaningfully clearer

## Closeout Checklist

Before sending the final answer after substantial work:

1. Re-read `docs/HANDOFF.md`.
2. Check whether `Confirmed Findings`, `Open Questions`, or `Recommended Next Steps` are now stale.
3. Update only the sections that changed.
4. If the project map changed, refresh `docs/PROJECT_MAP.md` too.
5. In the final user-facing answer, mention that the handoff files were refreshed when they were.

## Preferred Handoff Shape

Prefer keeping `docs/HANDOFF.md` in this shape:

- `Current Status`
- `Update Rule`
- `Confirmed Findings`
- `Open Questions`
- `Recommended Next Steps`
- `How To Resume In A New Chat`

The repository template ships exactly these sections, in this order, so agents that follow the template and agents that follow this list produce the same file shape. `Update Rule` restates the substantial-work triggers from Maintenance Rules inside the file itself, so a fresh chat knows when the handoff is due for a refresh without loading the skill.

Do not expand it into a session-by-session log unless the repository already wants that.

## Agent Install Locations

The same skill directory is installed once per agent:

- Codex: `~/.codex/skills/project-handoff-resume/`, or `%CODEX_HOME%/skills/project-handoff-resume/` when `CODEX_HOME` is set. `CODEX_HOME` is officially supported by Codex.
- WorkBuddy: `~/.workbuddy/skills/project-handoff-resume/`. WorkBuddy loads user-level skills only from `~/.workbuddy/skills/`; project-level skills belong in `{project}/.workbuddy/skills/`. There is no official WorkBuddy home-directory environment variable — the installer's `WORKBUDDY_HOME` override is a self-test hook and will desync the install location from where WorkBuddy actually reads if set.

`install-skill.ps1` and the GUI tool install into both by default. Keep the two copies byte-identical so behavior never diverges, and re-run the installer after editing the source copy inside this toolbox.

Note: `agents/openai.yaml` is Codex-only interface metadata. WorkBuddy ignores it, so it is harmless to copy, and safe to delete on the WorkBuddy side if a minimal tree is preferred.

## Fallbacks

- If none of the handoff files exist, do normal repository discovery and suggest creating them for future continuity.
- If the files exist but are stale, continue the task and repair them before finishing.
- If the user asks for a clean re-read despite handoff files existing, follow the user's request.

## Example Resume Prompt

Example user prompts that should trigger this skill:

- "使用 project-handoff-resume，然后继续这个工程。"
- "Use project-handoff-resume and continue this repo."
- "Read the handoff files and pick up where we left off."
- "Don't start over; resume this large project from the repo notes."
