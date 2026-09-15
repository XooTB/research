---
name: colab-compute
description: >-
  Run machine learning on a free Google Colab GPU/TPU from Cursor, VS Code, or Claude Code, using
  this workspace's datasets and scripts. Use whenever work needs an accelerator
  or more RAM than the local machine has — training models, CUDA/torch code,
  large matrix or survival modelling, "I don't have a GPU", jobs that are too
  slow or run out of memory locally — and whenever creating, running, or
  debugging a notebook that executes on a Colab runtime.
---

# Colab compute

The Google Colab extension attaches a **remote kernel** to a local notebook: the
`.ipynb` stays in this repo, the cells execute on a Google VM with a GPU. That
split drives every rule below.

## Hard constraints — read before writing any cell

| Constraint | Consequence |
|---|---|
| No terminal on the runtime (editor Remote Tunnels / SSH don't apply) | Everything shell-shaped goes in a cell: `!cmd` or `subprocess.run` |
| Runtime filesystem is empty and ephemeral | The repo must be cloned in every session; results must be pushed or copied out before it dies |
| The runtime clones the **GitHub remote**, not the local disk | Uncommitted or unpushed work is invisible to the runtime. Always push first |
| Free-tier sessions get reclaimed (idle in minutes, ~12h ceiling) and usually give a T4 | Checkpoint long runs to Drive; don't plan multi-hour uninterrupted training |
| Local Python is 3.14 with almost nothing installed; the runtime is 3.13 with the full ML stack (torch 2.11+cu128, pandas, sklearn) | Don't try to reproduce the runtime env locally — use the notebook for anything needing pandas/torch |
| Several `google.colab` helpers don't work in the extension (see below) | No Colab Secrets, so no implicit credentials on the runtime |
| Files over 100 MB are gitignored; git tracks a zip instead, split into `.zip.partNN` if the zip is also over the limit (github-file-size rule) | A fresh runtime clone has the archive, not the CSV. `ensure_dataset` unpacks automatically; anything reading paths directly must call `ce.restore_packed()` first |

Notebook-kernel use is within Colab's terms. SSH/tunnel workarounds are not, on
the free tier — don't suggest them.

## Configuration

`.research/config.yaml` → `colab:` block: `repo_url`, `branch`, `token_secret`,
`runtime_dir`, `sparse_paths`, `drive_dir`, `requirements`, `default_topic`.
Read it with `common.cfg("colab.<key>")`; never hardcode paths in scripts.

One-time user setup, in this order:

```
- [ ] Google Colab extension installed in Cursor or VS Code (publisher: Google).
      Claude Code agents edit and read notebooks from the terminal; the user
      runs cells in the editor
- [ ] Private repo only: GitHub PAT saved as a Colab secret named GITHUB_TOKEN
      (key icon in Colab's sidebar) with "Notebook access" enabled
- [ ] Kernel selected: Select Kernel -> Colab -> New Colab Server -> GPU
```

## Workflow

Agents cannot execute cells on a Colab kernel — there is no tool for it. Running
the notebook is the user's single manual step; everything either side of it is
automatable, so drive it like this:

```
- [ ] 1. Write / edit the notebook and any module it imports
- [ ] 2. Pre-flight: colab_check.py exits 0
- [ ] 3. Commit and push (the runtime clones the remote, not the disk)
- [ ] 4. Hand off: name the notebook, say "Run All", say what to expect
- [ ] 5. git pull, then colab_runs.py --last to read the actual results
- [ ] 6. Verify against expectations; if optimizing, change one thing and loop to 2
```

Never report a notebook's results as verified without step 5 — that record is
the only evidence an agent has. Do not idle waiting for the user to run cells;
finish the turn at step 4 with a clear handoff.

### Reading results back — `colab_runs.py`

```bash
.venv/bin/python agent/scripts/colab_runs.py --import-notebook notebooks/<nb>.ipynb
.venv/bin/python agent/scripts/colab_runs.py             # list, newest first
.venv/bin/python agent/scripts/colab_runs.py --last      # full newest record
.venv/bin/python agent/scripts/colab_runs.py --compare   # metric deltas across runs
```

`--compare` flattens every numeric metric to a dotted key with `first`, `last`
and `delta`, which is what answers "did that change help". Each record also
carries the environment snapshot, so a suspicious speedup can be checked against
which GPU the run actually got.

### 1. Pre-flight (always do this first)

```bash
.venv/bin/python agent/scripts/colab_check.py --dataset <slug> [--topic <topic>]
```

Exit 0 = ready. Otherwise read `next_steps`: it catches the failure that wastes
the most runtime minutes — a dataset that exists locally but was never pushed,
so the runtime's clone can't see it. Commit and push, then re-run.

### 3. Bootstrap cell

Every Colab notebook in this repo starts with the same cell. Copy it verbatim
from `notebooks/colab-smoke-test.ipynb` rather than rewriting it — it handles
private-repo tokens, re-runs idempotently, and falls back to the local checkout
so the notebook is still runnable against a local kernel.

It does a shallow, blobless, sparse clone into `/content/research` (a few MB of
code, not the 1.4 GB `datasets/` tree), then puts `agent/scripts` on `sys.path`
so `colab_env`, `common`, `db`, and `datasets_to_csv` all import unchanged.

### 4. Helpers — `agent/scripts/colab_env.py`

```python
import colab_env as ce
```

| Call | Does |
|---|---|
| `ce.summary()` | Human-readable runtime report: GPU, RAM, disk, workspace |
| `ce.report()` | Same as dict, for logging into a run record |
| `ce.gpu_info()` | nvidia-smi view plus whether torch can actually reach the GPU |
| `ce.require("torch", "lifelines")` | pip-installs only what's missing (usually a no-op) |
| `ce.install_requirements()` | Installs `agent/requirements-colab.txt` |
| `ce.workspace()` | Repo root, correct on runtime and locally |
| `ce.dataset_dir(slug[, topic])` · `ce.dataset_csv(slug, "expression.csv")` | Paths using the normal `datasets/<topic>/<slug>/` layout |
| `ce.ensure_dataset(slug)` | Widens sparse-checkout, fetches just that dataset, unpacks >100 MB archives |
| `ce.restore_packed()` | Rebuilds >100 MB originals from their committed zips |
| `ce.load_geo(slug)` | `(expression, phenotype)` DataFrames; phenotype indexed by `geo_accession` |
| `ce.geo_xy(slug, label="...")` | `(X, y, meta)` — X is samples x probes, y aligned and 0/1 |
| `ce.load_xena(slug, "HiSeqV2.csv")` | Xena/TSV matrix from `csv/` |
| `ce.tcga_os()` | `(X, time, event, clin, meta)` — TCGA-OV HiSeqV2 joined to overall survival (days) |
| `ce.gpl_gene_map("GPL96")` | Affymetrix probe → gene symbol (cached under `.research/cache/`) |
| `ce.collapse_to_genes(X, probe_to_gene)` | Average probes to gene symbols; `X` is samples × probes |
| `ce.save_run(name, payload, files=[...])` | Writes `.research/colab/runs/<utc>-<name>/run.json` with an env snapshot |
| `ce.mount_drive()` | Mounts Drive, returns the `colab.drive_dir` path |

`topic` defaults to `colab.default_topic`. For a non-0/1 label pass
`positive="..."`, e.g. `ce.geo_xy(slug, "status", positive="DOD (dead of disease)")`.

### Adding a dataset the runtime doesn't have yet

The runtime can only fetch what is committed. If `csv/` is missing for a
dataset, do the conversion **locally** and push, rather than converting on the
runtime where the output would be thrown away:

```bash
.venv/bin/python agent/scripts/datasets_to_csv.py --path datasets/<topic>/<slug>
.venv/bin/python agent/scripts/github_pack.py pack --path datasets/<topic>/<slug>
git add datasets/<topic>/<slug> && git commit -m "convert <slug> to csv" && git push
```

The pack step matters: several expression matrices exceed 100 MB, and GitHub
rejects those blobs outright. `colab_check.py` flags any that are still
pushable at that size.

### Packed data on the runtime

Large files reach the runtime as archives, so the raw CSV does not exist until
something unpacks it:

| Local disk | What git tracks | On the runtime after `ensure_dataset` |
|---|---|---|
| `csv/expression.csv` (< 100 MB) | the CSV | the CSV |
| `csv/expression.csv` (> 100 MB) | `csv/expression.csv.zip` | unpacked back to `csv/expression.csv` |
| zip also > 100 MB | `csv/expression.csv.zip.part01`, `.part02`, … | parts reassembled, then unpacked |

`ce.geo_xy` and `ce.load_geo` handle this for you. Two things to know:

- `.research` must stay in `colab.sparse_paths` — `.research/github-pack.json`
  is the manifest that tells the runtime what to unpack, and it is committed.
- A split archive is all-or-nothing. If some `.part` files never reached the
  remote, unpack refuses and leaves nothing behind rather than writing a
  truncated CSV. `colab_check.py --dataset <slug>` verifies every part of every
  packed file for that dataset is on the remote branch.

Reading a path directly, without going through the dataset helpers:

```python
ce.restore_packed()          # or, in a shell cell:
# !python /content/research/agent/scripts/github_pack.py unpack
```

### 5. Getting results out

The extension does not implement every `google.colab` helper, which rules out
the obvious routes — verified against Google's known-issues wiki:

| Helper | State in the extension |
|---|---|
| `userdata.get()` (Colab Secrets) | **Unsupported**, raises a timeout. There are no implicit credentials on the runtime, so an unattended `git push` cannot authenticate |
| `files.download()` | **Unsupported**; needs an ipywidget |
| `drive.mount()` | Works (extension v0.2.1+), via `ce.mount_drive()` |

So the default channel is **saved cell output**. The notebook file is local, so
anything printed and then saved lands on your disk with no credentials
involved. The final cell prints its record between `===RUN-RECORD-BEGIN===`
and `===RUN-RECORD-END===`, and this harvests it:

```bash
.venv/bin/python agent/scripts/colab_runs.py --import-notebook notebooks/<nb>.ipynb
```

Records land in `.research/colab/runs/`, after which `--last` and `--compare`
behave normally. The notebook must be **saved** first — unsaved output exists
only in the editor, not in the file. Re-importing is idempotent.

Two alternatives when that isn't enough:

- `ce.push_runs()` commits and pushes the records, but only if a PAT is already
  in the runtime environment as `GITHUB_TOKEN`. Set it with the ipywidget
  recipe from Google's wiki; do not put a token in a cell, it would be
  committed. Returns `{"pushed": False, ...}` rather than failing when absent.
- `ce.mount_drive()` plus `shutil.copytree` for model weights and anything
  large. Long training runs should checkpoint to Drive *during* training.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `summary()` says "none (CPU only)" | Kernel is a CPU runtime. Reconnect via Select Kernel → Colab → GPU |
| nvidia-smi sees a GPU but `torch_cuda: false` | Something reinstalled a CPU-only torch. Never pin torch/numpy in `requirements-colab.txt`; restart the runtime |
| `clone failed` / auth error in bootstrap | Private repo without a token. Add the `GITHUB_TOKEN` Colab secret and enable notebook access for it |
| `ModuleNotFoundError: colab_env` | Bootstrap cell not run this session, or `agent` missing from `colab.sparse_paths` |
| `AttributeError: module 'colab_env' has no attribute '...'` | Runtime clone is stale and Python cached the old import. Re-run the bootstrap cell — it fetches `origin`, hard-resets, and `importlib.reload`s |
| `FileNotFoundError: dataset not found` | The dataset isn't on the remote branch. Run `colab_check.py --dataset <slug>` locally |
| Dataset folder has `expression.csv.zip` but no `expression.csv` | Over the 100 MB limit, so only the zip is tracked. `ce.restore_packed()`, or `!python agent/scripts/github_pack.py unpack` |
| `missing parts: [...]` when unpacking | A split archive is incomplete on the remote. Push every `.zip.partNN`; re-run `colab_check.py --dataset <slug>` |
| Unpack does nothing and the CSV stays missing | `.research/github-pack.json` wasn't fetched (check `colab.sparse_paths`) or wasn't committed |
| Everything vanished mid-session | Session was reclaimed. Re-run from the bootstrap cell; results not pushed are gone |
| Kernel dies loading a big matrix | Runtime RAM (~13 GB on free tier). Load with `usecols`/`chunksize`, or subset probes before transposing |

## Related

- Training notebook: `notebooks/ovarian-os-lasso-cox.ipynb`
- Bootstrap cell template: `notebooks/colab-smoke-test.ipynb`
- Convert datasets so the runtime can load them: [datasets-to-csv](../datasets-to-csv/SKILL.md)
- Find and download datasets: [research-datasets](../research-datasets/SKILL.md)
