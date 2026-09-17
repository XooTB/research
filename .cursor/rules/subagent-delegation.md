---
description: Delegate big tasks to sub-agents running on composer or grok models
alwaysApply: true
---

# Sub-Agent Delegation

## When to delegate

Run work through sub-agents (`Task` tool) whenever a task is **big**, i.e. it matches any of:

- Multi-step workflows: paper searches + screening + downloads, dataset discovery + download + verification, batch CSV conversion
- Long-running or high-volume execution (batch downloads, parsing many PDFs, processing many files)
- Changes spanning more than ~3 files, or exploration of unfamiliar parts of the workspace
- Work that would flood the main conversation with tool output (large search results, verbose script logs)

Keep small, single-step actions (one search, one file edit, a quick question) in the main agent.

## Model selection

Always pass an explicit `model` when launching sub-agents for big tasks — do not inherit the parent model:

- **Default:** `cursor-grok-4.5-high` — for exploration, analysis, and research-style sub-tasks that need more reasoning
- **Alternative:** `composer-2.5-fast` — for execution-heavy work (running scripts, downloads, file processing, batch edits)
- Keep the main agent on the user's chosen model for orchestration, review, and final answers

## Sub-agent instructions

Sub-agents do NOT see the user's message or prior context, so every prompt must be self-contained:

1. **Goal**: what to accomplish and why, in concrete terms
2. **Context**: relevant file paths, topic names, DB locations (`.research/library.db`), script locations (`agent/scripts/`), and any decisions already made. Name the research-tracker IDs involved (`E###`/`T###`, relevant `F###`/`D###`); the sub-agent can run `research.py show <ID>` instead of you pasting history
3. **Constraints**: what not to do (e.g. don't modify unrelated files, don't install new dependencies without asking)
4. **Output contract**: exactly what to return (e.g. "return a JSON summary of downloaded datasets with paths and row counts"), kept short
5. **Tooling hints**: which scripts/skills to use (see `.cursor/skills/research-papers`, `research-datasets`, `datasets-to-csv`, `paper-dataset-extractor`; pack files over 100 MB with `agent/scripts/github_pack.py`)

Tracker ownership: sub-agents may add findings/decisions (`research.py new finding|decision`, evidence refs required), plan new items, and run with `colab_sync.py run --experiment <ID>`. The main agent closes items, changes priorities and success rules, reviews what sub-agents recorded, and writes the session handoff (`.cursor/skills/research-tracker/SKILL.md`).

Launch independent sub-agents in parallel (single message, multiple `Task` calls). Prefer `run_in_background: true` for long-running work so the main agent can keep orchestrating.
