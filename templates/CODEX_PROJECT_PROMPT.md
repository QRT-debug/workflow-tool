# Project Prompt

## Purpose

Describe what this repository is, what kind of system it implements, and what the code is mainly for.

Keep this section stable over time. Put short, high-value context here rather than session notes.

## Reading Priorities

List the files a future agent chat should read first, in order. This workflow is shared by Codex and WorkBuddy, and both read the same handoff files, so no per-agent reading order is needed.

Example shape:

1. entrypoint file
2. runtime/task scheduler file
3. main business module
4. communication or API layer
5. hardware or persistence layer

## Runtime Facts

Record stable facts such as:

- real runtime entrypoint
- important recurring loop
- main callback or interrupt path
- main global state object

## Important Distinctions

Note things like:

- generated code vs handwritten code
- active module vs backup or deprecated module
- test harness vs production path

## Watchouts

Capture recurring traps:

- generated files that may overwrite changes
- inactive modules still present in tree
- config files that disagree with runtime code

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
