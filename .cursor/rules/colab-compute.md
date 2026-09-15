---
description: Route GPU/ML work to Google Colab, driven by the agent via colab_sync.py; this machine has no GPU
alwaysApply: true
---

# ML work runs on Colab, and the agent runs it

This machine has **no GPU**, and the local `.venv` is Python 3.14 with only
`requests` and `pymupdf`. Do not try to fix that.

- Never `pip install` torch / pandas / scikit-learn into `.venv`. Most have no
  3.14 wheels, and the local env is deliberately minimal.
- Anything needing the ML stack, an accelerator, or more than ~14 GB RAM runs on
  a Colab session through `agent/scripts/colab_sync.py` (wraps Google's `colab` CLI).
- Read `.cursor/skills/colab-compute/SKILL.md` before writing experiment code or
  notebooks, or changing `colab_sync.py` / `colab_env.py`.

## Run it yourself, iterate as much as the task needs

```bash
.venv/bin/python agent/scripts/colab_sync.py start --dataset <slug>        # once per work session
.venv/bin/python agent/scripts/colab_sync.py run <script.py|nb.ipynb> [args] # edit → run → read → decide → repeat
.venv/bin/python agent/scripts/colab_sync.py stop                           # always, when done
```

- The local working tree is what runs. No commit, push, or clone is needed;
  `run` uploads only changed files and pulls run records back.
- Decide from what you read back — `run`'s output and exit code,
  `colab_runs.py --last` / `--compare`. Never report a result you did not read.
- `stop` the session when finished, when blocked, or before handing back to the
  user. Idle sessions burn quota.
- If the CLI reports an auth error, stop and ask the user to re-authenticate
  (skill: one-time setup). Never retry in a loop.

## Iterate without overfitting the validators

Tune and select models on **training-pool cross-validation only**. Score
external validation cohorts once per frozen candidate and record it; never loop
on their numbers (docs/current-focus-overall-survival.md §2).
