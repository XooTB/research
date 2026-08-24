---
name: colab-compute
description: >-
  Run machine learning on a free Google Colab GPU/TPU from inside Cursor, using
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
| No terminal on the runtime (Cursor's Remote Tunnels / SSH don't apply) | Everything shell-shaped goes in a cell: `!cmd` or `subprocess.run` |
| Runtime filesystem is empty and ephemeral | The repo must be cloned in every session; results must be pushed or copied out before it dies |
| The runtime clones the **GitHub remote**, not the local disk | Uncommitted or unpushed work is invisible to the runtime. Always push first |
| Free-tier sessions get reclaimed (idle in minutes, ~12h ceiling) and usually give a T4 | Checkpoint long runs to Drive; don't plan multi-hour uninterrupted training |
| Local Python is 3.14 with almost nothing installed; Colab is 3.12 with the full ML stack | Don't try to reproduce the runtime env locally — use the notebook for anything needing pandas/torch |
| Files over 100 MB are gitignored; git tracks a zip instead, split into `.zip.partNN` if the zip is also over the limit (github-file-size rule) | A fresh runtime clone has the archive, not the CSV. `ensure_dataset` unpacks automatically; anything reading paths directly must call `ce.restore_packed()` first |

Notebook-kernel use is within Colab's terms. SSH/tunnel workarounds are not, on
the free tier — don't suggest them.

## Configuration

`.research/config.yaml` → `colab:` block: `repo_url`, `branch`, `token_secret`,
`runtime_dir`, `sparse_paths`, `drive_dir`, `requirements`, `default_topic`.
Read it with `common.cfg("colab.<key>")`; never hardcode paths in scripts.

One-time user setup, in this order:

```
- [ ] Google Colab extension installed in Cursor (publisher: Google)
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

The last cell of a notebook pushes its `save_run` record, which makes results
readable from the terminal:

```bash
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

Ordered by what to reach for first:

| Artifact | Method |
|---|---|
| Run records, metrics, small CSVs | `git add .research/colab/runs && commit && push` from a cell — the bootstrap already set a credentialed remote |
| Model weights, checkpoints, anything large | `ce.mount_drive()` then `shutil.copytree` |
| One file, right now | `from google.colab import files; files.download(path)` |

Long training runs should checkpoint to Drive *during* training, not at the end.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `summary()` says "none (CPU only)" | Kernel is a CPU runtime. Reconnect via Select Kernel → Colab → GPU |
| nvidia-smi sees a GPU but `torch_cuda: false` | Something reinstalled a CPU-only torch. Never pin torch/numpy in `requirements-colab.txt`; restart the runtime |
| `clone failed` / auth error in bootstrap | Private repo without a token. Add the `GITHUB_TOKEN` Colab secret and enable notebook access for it |
| `ModuleNotFoundError: colab_env` | Bootstrap cell not run this session, or `agent` missing from `colab.sparse_paths` |
| `FileNotFoundError: dataset not found` | The dataset isn't on the remote branch. Run `colab_check.py --dataset <slug>` locally |
| Dataset folder has `expression.csv.zip` but no `expression.csv` | Over the 100 MB limit, so only the zip is tracked. `ce.restore_packed()`, or `!python agent/scripts/github_pack.py unpack` |
| `missing parts: [...]` when unpacking | A split archive is incomplete on the remote. Push every `.zip.partNN`; re-run `colab_check.py --dataset <slug>` |
| Unpack does nothing and the CSV stays missing | `.research/github-pack.json` wasn't fetched (check `colab.sparse_paths`) or wasn't committed |
| Everything vanished mid-session | Session was reclaimed. Re-run from the bootstrap cell; results not pushed are gone |
| Kernel dies loading a big matrix | Runtime RAM (~13 GB on free tier). Load with `usecols`/`chunksize`, or subset probes before transposing |

## Related

- Reference notebook: `notebooks/colab-smoke-test.ipynb`
- Convert datasets so the runtime can load them: [datasets-to-csv](../datasets-to-csv/SKILL.md)
- Find and download datasets: [research-datasets](../research-datasets/SKILL.md)
