---
name: research-tracker
description: >-
  Track the research itself: current focus, what's next, which approaches were
  tried and their computed verdicts, results, findings, decisions, and session
  handoffs, via agent/scripts/research.py over research/. Use at the start and
  end of every work session; whenever the user asks "where are we", "what's
  next", "what have we tried", "did X work", "what do we know about <cohort or
  dataset>"; before planning, running, or closing an experiment; when a result,
  notable observation, or decision happens; when reprioritizing work; and when
  briefing sub-agents.
---

# Research tracker

`research/` is the project's memory across sessions and tools. It holds what we are trying to
learn, what's planned, what ran, what it showed, and why we chose what we chose. Chat
history is not memory: if it isn't in the tracker, the next session doesn't know it.

Everything is plain text in git. `agent/scripts/research.py` rebuilds an in-memory index
(SQLite + full-text search) from those files and the run records on every call, so
**query instead of reading files**. Queries return a few hundred characters; the files can be
many thousands.

```
PY=.venv/bin/python; R="$PY agent/scripts/research.py"
```

## Layout and item types

```
research/NOW.md                          GENERATED overview; never edit by hand
research/<ws>/workstream.md              goal, question, success rule [criterion], milestones, reference body
research/<ws>/experiments/E###-slug.md   one approach / hypothesis (may span many runs)
research/<ws>/tasks/T###-slug.md         work that isn't an experiment: acquisition, conversion, write-up
research/<ws>/findings.md                append-only: notable, evidenced observations (F###)
research/<ws>/decisions.md               append-only: choices + why + what was rejected (D###)
research/<ws>/journal.md                 append-only: session handoffs
.research/colab/runs/<run>/run.json      run records; their "metrics" rows are the results
```

| Type | Use it for | Lifecycle |
|---|---|---|
| **Experiment** `E###` | Testing an idea whose outcome is uncertain: a model, a preprocessing choice, a feature set, an endpoint | planned → running (first run linked) → done (verdict computed) or abandoned |
| **Task** `T###` | Work with a known shape: get data, convert, write up, fix tooling | planned → running → done/abandoned |
| **Finding** `F###` | Something we now know, with evidence: a result pattern, a data quirk, a leakage, a failure mode | append-only; replace with a new finding that `supersedes:` it |
| **Decision** `D###` | A choice that constrains future work, with the alternatives rejected | append-only; reverse with a new decision that `supersedes:` it |
| **Journal** | Session handoff: what was done, where it stopped, what's next and why | append-only |

IDs are global across workstreams and allocated by `research.py new`. Refer to things by
ID everywhere: commit messages, notebooks, docs, chat, sub-agent briefs.

## Session protocol

**Start**
1. Read `research/NOW.md`. Claude Code loads it through CLAUDE.md; in Cursor, open it.
2. `$R next` for the actionable queue. For the item you pick: `$R show <ID>`, plus
   `--section plan` if you need its plan.
3. If the user's request isn't covered by an existing item, create one before starting
   (below). Work that matters is never untracked.

**During**
- Mark the item running when you start it (`$R set T002 status running`). Experiments switch
  automatically when their first run is linked.
- Record findings and decisions when they happen, not at the end.
- Every run whose numbers matter goes through `colab_sync.py run --experiment E###` and saves
  metric rows (see Results).

**End** (also before handing back to the user or stopping a long task)
1. Update the items you touched: status, outcome, and new planned items the work revealed.
2. `$R log "<handoff>" --label "<short topic>"`, following the handoff template below.
3. `$R check` must report `"ok":true` (it's also part of `workspace_check.py`). Writes regenerate
   `NOW.md` automatically; `$R status` forces it.

## Answering questions: query, don't read

| Question | Command | Reads prose? |
|---|---|---|
| Where are we? | `research/NOW.md` (≈1k tokens) | no |
| What's next? | `$R next` (running, ready by priority, blocked with what they wait on) | no |
| What have we tried and how did it go? | `$R list --kind experiment` (status, verdict, outcome line) | no |
| Did anything meet the bar? | `$R list --kind experiment` (verdict column) + `$R results --metric delta_c_vs_clinical_transported --split external --min 0.03` | no |
| Numbers for one experiment | `$R results --experiment E003 [--metric cindex]` | no |
| Verdict and why | `$R verdict E003` (rule, basis, per-model cohort counts) | no |
| Everything about a cohort/dataset/run/ID | `$R refs gse53963` | no |
| Did we ever look at X? | `$R find <words> [--kind finding\|decision\|journal] [--any]` | snippets only |
| One item in detail | `$R show E003`, then `--section plan\|notes\|interpretation`, or `--body` | only if needed |
| Workstream reference (product, rules, cohort roles, protocol) | `$R show os-hgsoc --section "data in hand"` (prefix match; a miss lists the section names) | one section |
| Anything else | `$R sql "SELECT … FROM item\|edge\|metric\|fts"` (read-only) | no |

Outputs are capped (`truncated` tells you when). Narrow with flags rather than raising
`--limit`. Open a file only to edit a body section or when a query points you at one.

## Recording work

### Plan an experiment or task

```bash
$R new experiment --title "Gene-count sweep for LASSO-Cox" \
   --summary "Sweep 100–2000 top-variance genes; choose by pool CV only" \
   --hypothesis "More genes improve pool CV C-index up to a plateau" \
   --depends-on E003 --priority 2 --tags lasso-cox,feature-selection \
   --plan "Grid 100/250/500/1000/2000 × penalizer; 5-fold CV on os-training-pool; no validators"
$R new task --title "Attach GSE9891 survival" --summary "…" --priority 2
```

Then edit the file's `## Plan` section with anything longer. Before the first run, decide the
experiment's **success rule** (next section) and set it with `$R criterion` if it differs from
the workstream's.

### Success rules and verdicts: computed, never judged

- By default an experiment inherits the workstream's `[criterion]` (os-hgsoc:
  `delta_c_vs_clinical_transported >= 0.03` on ≥ 2 external cohorts, same model; D006).
- If that isn't the right test, give the experiment its own rule **before its first run**:
  ```bash
  $R criterion E005 --metric cindex --split cv --op ">=" --threshold 0.62 --models lasso_cox [--min-cohorts 1] [--cohorts …]
  $R criterion E005 --none      # no numeric test: verdict n/a, judged by its outcome line
  $R criterion E005 --inherit   # back to the workstream rule
  ```
  It writes this table into the file (refused once the experiment has runs):
  ```toml
  [criterion]
  metric = "cindex"        # a metric name from its rows
  split = "cv"             # train | cv | external
  op = ">="                # >= > <= <
  threshold = 0.62
  min_cohorts = 1          # distinct cohorts that must pass, for one model
  models = ["lasso_cox"]   # optional filter; `cohorts = [...]` also allowed
  ```
  Use `--none` (or `new experiment --criterion-none`) only for experiments with no numeric test.
- The rule's hash is frozen when the first run is linked. Changing it afterwards is a
  `criterion-changed` error: don't move the goalposts. Close the experiment and pre-register a
  new one.
- Verdict = the rule applied to the **latest run per (model, cohort)** of the experiment's
  linked runs: `supported`, `not-supported`, `no-data`, or `n/a`. `n/a` does **not** mean
  "unknown": the experiment had no numeric rule (e.g. E001/E002 predate the workstream rule), so
  report its outcome line, which `verdict` includes, and say it wasn't judged by a pre-registered
  rule. `$R verdict E###` shows it
  any time. `$R set E### status done --outcome "…"` computes and stores it; hand-edited verdicts
  fail `check`.
- `done` requires data for its rule. An experiment that couldn't produce it is `abandoned`,
  with an outcome saying why.
- Never phrase an outcome that contradicts the verdict. Interpretation (why, caveats, what
  next) goes in the `## Interpretation` section.

### Results: metric rows

Runs record results as flat rows. In experiment code on Colab:

```python
import colab_env as ce
rows = [ce.metric_row("lasso_cox", "gse32062", "external", "cindex", c, ci_lo=lo, ci_hi=hi, n=260),
        ce.metric_row("lasso_cox", "gse32062", "external", "delta_c_vs_clinical_transported", d,
                      baseline="clinical_transported")]
ce.save_run("os-lasso-sweep", payload, metrics=rows)   # invalid rows raise; None/NaN rows are dropped
```

Run it linked: `colab_sync.py run --experiment E005 agent/experiments/<script>.py` (the same for
`job --experiment E005 <name> <script>`). The flag goes before the script. The pulled run is
added to the experiment's `runs`, the status becomes `running`, and `NOW.md` refreshes. Runs
without `--experiment` are only for smoke tests; `check` warns about unlinked runs.
`$R link-run <run> --experiment E###` repairs a missed link.

Naming conventions (queries depend on them; all lowercase):

| Field | Convention | Examples |
|---|---|---|
| `model` | snake_case model id; baselines named for what they are | `lasso_cox`, `rsf`, `deepsurv`, `clinical_transported`, `clinical_oof` |
| `cohort` | dataset cohort id, or the pooled table's slug | `gse32062`, `tcga-ov`, `os-training-pool` |
| `split` | `train` (in-sample), `cv` (out-of-fold within the named cohort), `external` (never seen in training) | |
| `metric` | `cindex`, `logrank_p`, `auc_3y`, `delta_<metric>_vs_<baseline>` | `delta_c_vs_clinical_transported` |
| extras | `ci_lo`, `ci_hi`, `n`, `baseline` | |

A run that produces numbers but no rows can't be queried or judged. Add rows even for
"failed" runs: negative results are results.

### Close an item

```bash
$R set E005 status done --outcome "Plateau at 500 genes (pool CV C 0.611); more genes add nothing."
$R set T002 status abandoned --outcome "curatedOvarianData GSE9891 lacks OS time; Tothill supplement unavailable."
```

Outcome: one self-contained line (≤ 300 chars) with the key numbers and the comparison. It is
what every later query shows. Nothing is deleted: abandon instead.

### Findings and decisions

```bash
$R new finding --title "GSE140082 follow-up too short for 5-year OS" \
   --refs "gse140082,E003,run:20260918T101500Z-os-first-pass" --tags follow-up,validation \
   --body "Max OS 3.6 y; KM curves cross after 2 y. Treat as supportive only."
$R new decision --title "Use transported clinical Cox as the deciding baseline" \
   --refs "E003" --tags success-rule \
   --body "Why … Rejected: per-cohort CV baseline (fit on the target cohort)."
$R new finding --title "…corrected claim…" --refs "…" --supersedes F004 --body "…"
```

- **Finding** = one claim + evidence refs (`E###`/`T###`, `run:<name>`, dataset slug, doc path).
  Refs are required and checked. Record data quirks, leakage, failure modes, surprising
  numbers, confirmations of assumptions.
- **Decision** = what we'll do, why, and the rejected alternatives. Record anything a future
  session might otherwise re-litigate: scope, splits, preprocessing, baselines, success rules,
  exclusions, tooling.
- Both are append-only. To correct or reverse one, add a new entry with `--supersedes`; queries
  then hide the old one unless `--all`.

### Reprioritize

Priority 1 is highest. `next` orders ready items by priority, then ID; dependencies decide
blocked vs ready.

```bash
$R set T003 priority 1
$R set E004 depends_on "E003,T003"
```

Agents may reprioritize planned items themselves when one would make others easier or
cheaper: it unblocks several items, removes a data limitation, or de-risks a larger
experiment. Log a one-line reason in the handoff. Verdicts are never adjusted; only the order
of work is.

### Handoff template (`$R log`)

```
Did: <items touched and what changed, with IDs>
State: <what is running / half-done / broken, where it stopped>
Next: <the next item(s) by ID and why they come first>
Watch: <open questions, risks, anything surprising>
```

Keep it under ~10 lines; `NOW.md` shows the latest one.

## Validation, provenance, and the tracker

- An experiment that scores external validators sets `validation_candidate` (the name passed
  to `ce.register_validation`). The ledger entry records the experiment too. See the
  colab-compute skill for the score-once rule.
- Run records carry the code snapshot commit and dataset hashes; `results` rows show `run`, so
  any number traces back to its exact code and data.

## Sub-agents

Brief sub-agents with tracker IDs ("work on T002; evidence goes in findings with refs"). They
may `new finding` / `new decision`, `log`, and plan new items. Closing items, changing
priorities, and success rules stay with the main agent, which reviews what they added before
reporting to the user.

## New workstream

Only when the user starts a genuinely separate line of research. Copy
`research/os-hgsoc/workstream.md` as a template into `research/<slug>/workstream.md`: set `id`
to the slug, `status = "active"`, summary, question, `[criterion]`, `milestones`, then add
experiments with `research.py new … --ws <slug>`. Pause or finish old ones by setting their
`status` (`paused`/`done`/`dropped`) in the file.

## Check codes

| Code | Fix |
|---|---|
| `now-stale` | `$R status` |
| `run-not-linked` / `run-orphan` | `$R link-run <run> --experiment E###` (or it was a smoke test: ignore the warning) |
| `no-outcome` | `$R set <ID> outcome "…"` |
| `verdict-mismatch` | `$R set <ID> status done --outcome "…"` recomputes; never hand-edit `verdict` |
| `criterion-changed` | restore the rule (`git log -p` on the file), or abandon and pre-register a new experiment |
| `done-without-data` | link the runs, or `set <ID> status abandoned` |
| `unknown-ref` / `unknown-dependency` | fix the ID or path |
| `no-next-step` | plan the next experiment: the workstream has nothing ready or running |
| `stale-running` | update it, or close/abandon it |

## Never

- Hand-edit `NOW.md`, `verdict`, `verdict_basis`, `criterion_hash`, or `runs`.
- Delete an item or rewrite a finding/decision in place.
- Report a result that isn't in a metric row or a pulled run record.
- Change a success rule after an experiment has results.
- End a session without a handoff and a clean `research.py check`.
