---
description: Track all research work (focus, next, experiments, verdicts, findings, decisions, handoffs) in research/ via agent/scripts/research.py
alwaysApply: true
---

# Research work is tracked in research/, every session

`research/` is the project's memory across sessions and tools; chat history is not. Full guide:
`.cursor/skills/research-tracker/SKILL.md`. Read it before planning, running, or closing
experiments.

**Start of session:** read `research/NOW.md` (focus, in flight, next up, latest outcomes, last
handoff), then `.venv/bin/python agent/scripts/research.py next`. Work on tracked items; if the
request isn't covered, create the experiment or task first (`research.py new`).

**Query, don't read.** Answer "what's next / what did we try / did X work / what do we know
about Y" with `research.py next | list | results | verdict | refs | find | show`, not by
opening tracker files or long docs. Outputs are small and capped.

**Results are data.** Any run whose numbers matter runs as `colab_sync.py run --experiment E###
…` and saves metric rows (`colab_env.metric_row` → `save_run(metrics=…)`). Verdicts are
computed from the experiment's pre-registered success rule; never judge, hand-write, or edit a
verdict, and never change a rule once results exist.

**Record as you go.** Findings (evidence refs required) and decisions (with rejected
alternatives) via `research.py new finding|decision`. Status/outcome/priority via
`research.py set`. Nothing is deleted: close as `abandoned` with an outcome. Agents may
reprioritize planned items when one makes others easier, and say why in the handoff.

**End of session / before handing back:** update touched items, `research.py log "<Did / State
/ Next / Watch>"`, and make `research.py check` report ok. Never hand-edit `research/NOW.md`.
