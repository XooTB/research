---
name: colab-compute
description: >-
  Run machine learning on a Google Colab runtime that the agent drives itself
  from the terminal (Google's colab CLI via agent/scripts/colab_sync.py), using
  this workspace's code and datasets. Use whenever work needs the ML stack, an
  accelerator, or more RAM than the local machine has — training or evaluating
  models, survival modelling, torch/CUDA code, "I don't have a GPU", jobs too
  slow locally — and whenever writing, running, or debugging experiment scripts
  or notebooks that execute on Colab.
---

# Colab compute

The agent runs code on Colab itself. Google's `colab` CLI rents a runtime;
`agent/scripts/colab_sync.py` uploads the local working tree into it, runs
scripts or notebooks there, and pulls run records back. Edit → run → read →
decide → repeat, as often as the task needs. No human runs cells, and nothing
is committed, pushed, or cloned to make a run happen.

## Hard constraints

| Constraint | Consequence |
|---|---|
| No local GPU; local `.venv` is Python 3.14 with almost nothing installed | All ML code runs on the session. Don't reproduce the runtime env locally |
| A session is a live kernel on a rented VM (torch/pandas/sklearn preinstalled) | It persists between commands until `stop` (keep-alive daemon, ~24 h cap). Always `stop` when done |
| The VM disk is ephemeral | Keep results with `colab_env.save_run()`; `run`, `logs` and `stop` pull those records back |
| Accelerators are tier-gated and not guaranteed | `start` requests `colab.gpu` (T4) and falls back to CPU. The OS survival models run fine on CPU |
| Long websocket executions are fragile | `run` uses `colab.exec_timeout` (3600 s); anything longer goes through `job` |
| Datasets upload from the **local working tree** | Packed >100 MB originals must exist unzipped locally (`github_pack.py unpack`); zips are never uploaded |
| `colab repl`, `console`, `auth`, `drivemount` need a TTY or a human | Never call them from the agent |

## One-time setup (user)

```
- [ ] Install the CLI (Python ≥3.12; Linux/macOS):
        uv tool install google-colab-cli --with 'jupyter-kernel-client<1'
      The pin matters: v0.6.0 breaks with jupyter-kernel-client 1.x
      ("no attribute 'KernelClient'", upstream PR #125)
- [ ] Authenticate, and make colab.auth in .research/config.yaml match:
      oauth2 (default): run `colab --auth=oauth2 sessions` in a terminal (in Claude Code:
        `! colab --auth=oauth2 sessions`) and finish the copy-paste consent.
        Known issue: may ask to log in again roughly hourly.
      adc (steadier for long unattended loops): install gcloud (yay -S google-cloud-cli), run
        gcloud auth application-default login --scopes=openid,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/colaboratory
        then set colab.auth: adc
- [ ] Check: `colab --auth=<method> sessions` exits 0
```

If a `colab_sync.py` command reports an auth, 401 or 403 error, stop and ask
the user to redo the step above. Do not retry in a loop, and never start the
interactive login yourself.

## The loop

```bash
PY=.venv/bin/python; S=agent/scripts/colab_sync.py
$PY $S start --dataset os-training-pool --dataset os-validation   # session + code + data + requirements
$PY $S run agent/experiments/colab_smoke.py --dataset os-training-pool   # first run in a new setup
$PY $S run agent/experiments/<experiment>.py --penalizer 0.05     # sync changes, run, pull records
$PY agent/scripts/colab_runs.py --compare --name <experiment>      # did the change help?
# edit and run again, as many iterations as the task needs
$PY $S stop                                                        # pull, save session log, release VM
```

1. **start** once per work session. It is idempotent: a live session of the same
   name is reused, and only what changed is uploaded.
2. **run** after every edit. Script output streams to stderr; stdout is a JSON
   summary `{script, exit_code, sync, new_runs}`; the command exits with the
   script's exit code. Read the output, then decide.
3. Change one thing per iteration and compare records, not memory.
4. **stop** when finished, when blocked, or before handing back to the user.

## `colab_sync.py` reference

| Command | Does |
|---|---|
| `start [--dataset S ...] [--gpu T4 \| --cpu]` | Create or reuse the session, upload `colab.sync_paths` + datasets, install `agent/requirements-colab.txt`, report the runtime |
| `push [--dataset S ...]` | Upload changed files only. Datasets pushed once stay synced for the session |
| `run [--timeout SEC] <file.py \| file.ipynb> [args...]` | Push, run on the session, pull new run records |
| `job <name> <file.py> [args...]` | Push, then start the script detached on the VM |
| `logs <name> [-n 40]` | Tail a job; report running or exit code; pull records once it has finished |
| `pull` | Copy new `.research/colab/runs/*` from the session |
| `status` | CLI session status plus what is synced |
| `stop` | Pull, save the CLI session history to `.research/colab/sessions/` (gitignored), release the VM |

Every command takes `-s NAME` (default `colab.session`), placed after the
subcommand. `--dataset` takes a slug (`os-validation`), `topic/slug`, or a
sub-path (`os-validation/labels.csv`) to upload just part of a dataset. Settings
live in the `colab:` block of `.research/config.yaml`.

How it works: changed files are tarred, gzipped, split into
`colab.upload_chunk_mb` parts, sent with `colab upload`, and extracted into
`colab.runtime_dir` (`/content/research`) through `colab exec`. A manifest on the
runtime (size + mtime per file) makes later pushes incremental; a recreated
session simply gets everything again.

## Writing experiment code

**Prefer scripts over notebooks** for anything you will iterate on: they diff
cleanly, take arguments, and give `run` a real exit code. Put them in
`agent/experiments/` (synced with `agent/`). A script runs like `python file.py
args` from the workspace root on the runtime, with `agent/scripts` on `sys.path`.

```python
import colab_env as ce

ce.require("lifelines", "scikit-survival")                 # no-op when present
tables = ce.ensure_os_tables()                              # paths to the compiled OS tables
labels = ce.memo("os-train-labels-v1", lambda: load_labels(tables["train"]))  # reused across runs
...
ce.save_run("os-lasso", {"params": {...}, "train_cv": {...}})  # pulled back automatically
```

- `ce.memo(key, fn)` caches a value in the session kernel, so repeated `run`s
  skip reloading large matrices. Workspace modules are re-imported on every
  `run`, so code edits always take effect while the memo survives. Bump the key
  when the loading code changes.
- Put every number you will judge in the `save_run` payload: `colab_runs.py
  --compare` diffs numeric leaves across runs.
- Figures: save to a file and pass it in `save_run(files=[...])`.

### Notebooks

`run notebook.ipynb` executes every code cell on the session and writes the
executed copy next to the input as `<name>_output.ipynb` (gitignored). Record
blocks printed between `===RUN-RECORD-BEGIN===` and `===RUN-RECORD-END===` are
imported, and `save_run` folders are pulled. Notebooks start with the bootstrap
cell from `notebooks/ovarian-os-first-pass.ipynb`, which finds `/content/research`
on Colab or the local checkout otherwise.

### `colab_env.py` helpers

| Call | Does |
|---|---|
| `ce.summary()` · `ce.report()` | Runtime report: GPU, RAM, disk, workspace |
| `ce.gpu_info()` | nvidia-smi view plus whether torch can reach the GPU |
| `ce.require(...)` · `ce.install_requirements()` | Install only what is missing · `agent/requirements-colab.txt` |
| `ce.memo(key, fn)` | Compute once per session kernel |
| `ce.workspace()` · `ce.dataset_dir(slug)` · `ce.dataset_csv(slug, name)` | Paths in the normal `datasets/<topic>/<slug>/` layout |
| `ce.ensure_dataset(slug)` · `ce.ensure_os_tables()` | Fail clearly if a dataset was not pushed |
| `ce.load_geo(slug)` · `ce.geo_xy(slug, label=...)` · `ce.load_xena(slug, name)` · `ce.tcga_os()` | Loaders |
| `ce.gpl_gene_map("GPL96")` · `ce.collapse_to_genes(X, map)` | Probe → gene symbol |
| `ce.save_run(name, payload, files=[...])` | `.research/colab/runs/<utc>-<name>/run.json` with provenance, env snapshot, and pending validation entries |
| `ce.register_validation(candidate, cohorts, config=..., reason=None)` | Record a frozen candidate in the validation ledger **before** scoring external cohorts; refuses a repeat |
| `ce.run_context()` | The provenance `save_run` stores (from `colab_sync.py`, else local git state) |

## Long jobs

`run` holds a connection for the whole execution. For anything that may exceed
`colab.exec_timeout`, or that you want to poll while doing other work:

```bash
$PY $S job rsf-grid agent/experiments/<experiment>.py --trees 1000
$PY $S logs rsf-grid        # repeat until exit_code is set; records are pulled then
```

## Reading results back

```bash
.venv/bin/python agent/scripts/colab_runs.py --last       # newest record in full
.venv/bin/python agent/scripts/colab_runs.py --compare    # metric deltas across runs
.venv/bin/python agent/scripts/colab_runs.py --ledger     # validation scorings per candidate
```

Never report a result as verified unless you read it from a pulled record or
from `run`'s own output.

## Provenance

Because the uncommitted working tree is what runs, a git commit on its own does
not identify a result. `run` and `job` therefore record, in every
`save_run` record's `provenance` block:

- `git.code_commit`: HEAD when the synced code roots (`colab.sync_paths`) are
  clean, otherwise a snapshot commit of the working tree kept under
  `refs/runs/<stamp>-<script>`. The branch, index, and working tree are not
  touched. Reproduce a run with `git checkout <code_commit>` or
  `git show <code_commit>:path`. Run refs are local; `git push origin 'refs/runs/*'`
  shares them.
- `datasets`: per pushed dataset root, file count, bytes, and a sha256 over the
  files (hashes cached in `.research/colab/hash-cache.json`, gitignored).
- `script`, `args`, `session`, `command`, `invoked_at`.

The runtime gets this through `$RESEARCH_RUN_CONTEXT`. Records pulled without it
(e.g. a notebook kernel that didn't see the variable) are stamped locally from
the same invocation, marked `stamped_locally`. Run things through
`colab_sync.py`: a record with `provenance.via = "unknown"` can't be traced, and
`workspace_check.py` flags it.

## Iterating without overfitting (OS workstream)

A loop that watches external-validation scores will overfit to them. So:

- Make every tuning and model-selection decision on **training-pool
  cross-validation** only.
- Score `os-validation` cohorts only for a **frozen** candidate. Call
  `ce.register_validation(candidate, cohorts, config={...})` before the first
  line that touches validation outcomes, then `save_run`. The call checks
  `.research/validation-ledger.jsonl` (synced to the runtime, merged back on
  every pull) and raises `ValidationAlreadyScored` when the candidate name or
  its config hash was already scored. Don't work around it by renaming the
  candidate. If a re-score is legitimate (a scoring bug, a newly attached
  cohort), pass `reason=` and say so in the write-up.
- Tuning experiments should push `os-training-pool` only. Push `os-validation`
  when a candidate is frozen.
- Always report the clinical-only baseline beside every model
  (`docs/current-focus-overall-survival.md` §2).

## Raw `colab` CLI

`colab_sync.py` covers the loop; use the CLI directly for anything else, with
`--auth=<colab.auth>` before the subcommand. `colab skill` prints Google's full
agent guide for the installed version. Useful: `colab sessions`, `colab status
-s S`, `colab restart-kernel -s S` (wedged kernel, keeps the VM), `colab log -s S
-n 20` (structured events when something fails), `colab install -s S pkg`.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| 401 / 403, "could not authenticate", keep-alive `consecutive_4xx_errors` | Login expired or missing the `colaboratory` scope. Stop; ask the user to redo the one-time setup |
| `start` warns the GPU was not granted | Quota or tier. Continue on CPU, or `stop` and retry later |
| `no result from session ...` | Session reclaimed or wedged. `colab sessions`, then `colab_sync.py start` (re-uploads) or `colab restart-kernel -s S` |
| `packed originals missing locally` | `.venv/bin/python agent/scripts/github_pack.py unpack` |
| `FileNotFoundError: dataset not found` on the runtime | Not pushed this session: `colab_sync.py push --dataset <slug>` |
| `is not under colab.sync_paths` | Move the script under `agent/` or `notebooks/`, or add its folder to `colab.sync_paths` |
| `run` times out | Raise `--timeout`, or use `job` + `logs` |
| `torch_cuda: false` with a GPU present | Something reinstalled CPU-only torch. Never pin torch/numpy in `requirements-colab.txt`; `stop` and `start` fresh |
| Kernel dies loading a big matrix | ~13 GB RAM on the free tier. Load with `usecols`/`chunksize`, or `memo` a reduced matrix |

## Related

- Session driver `agent/scripts/colab_sync.py` · runtime helpers `agent/scripts/colab_env.py` · records `agent/scripts/colab_runs.py`
- Workspace health (DB/disk, packed files, OS tables, run provenance, ledger): `agent/scripts/workspace_check.py`
- Smoke test: `agent/experiments/colab_smoke.py`
- Convert datasets so the runtime can load them: [datasets-to-csv](../datasets-to-csv/SKILL.md)
- Find and download datasets: [research-datasets](../research-datasets/SKILL.md)
