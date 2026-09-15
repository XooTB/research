# Research workspace

Shared agent config lives in `.cursor/` and is symlinked for Claude Code — edit
the `.cursor/` originals, never replace a symlink with a copy:

- `.claude/skills` → `.cursor/skills` (research-papers, research-datasets,
  datasets-to-csv, paper-dataset-extractor, medical-dataset-finder, colab-compute)
- `.claude/rules/*.md` → `.cursor/rules/*.md` (always loaded). Rules must stay
  `.md`: Claude Code ignores anything resolving to `.mdc`
- `.mcp.json` → `.cursor/mcp.json`

## Sub-agent models (overrides `subagent-delegation.md`)

That rule is shared with Cursor and names Cursor models. In Claude Code, follow
its *when to delegate* and *how to brief* guidance, but map the models to
cheaper Claude ones via the `Agent` tool's `model` parameter (it names the
`Task` tool; use `Agent` here):

- `cursor-grok-4.5-high` (exploration, analysis, research) → `sonnet`
- `composer-2.5-fast` (running scripts, downloads, batch edits) → `haiku`

Pick whichever cheaper available model fits the sub-task. Keep the main session
on the user's model for orchestration and final answers.

Tooling overview: @agent/README.md

Current workstream (read before any modelling or data work):
@docs/current-focus-overall-survival.md
