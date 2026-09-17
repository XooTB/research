# Research Agent

An agent-driven assistant (Cursor or Claude Code) for working with research
**papers** and **datasets**. Python scripts fetch, download, profile, and run
experiments on Colab; the agent does the reasoning (relevance ranking, criteria
screening, usability verdicts, modelling decisions). Everything is stored
locally in this workspace.

## Layout

```
research/NOW.md                                    # generated: focus, in flight, next up, outcomes, handoff
research/<ws>/workstream.md, experiments/, tasks/  # research tracker (+ findings/decisions/journal .md)
papers/<topic>/<year>-<author>-<title>/paper.pdf   # organized PDFs
datasets/<topic>/<slug>/ + REPORT.md               # datasets + verification
notebooks/                                          # notebooks run on Colab
.research/library.db                               # SQLite: papers, datasets, notes
.research/references.bib                            # auto-exported BibTeX
.research/config.yaml                               # sources, paths, credentials, colab
.research/colab/runs/                               # run records pulled back from Colab
agent/scripts/                                      # the tools (below)
agent/experiments/                                  # experiment scripts run on Colab
.cursor/skills/<name>/SKILL.md  (= .claude/skills)  # how the agent uses them
```

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install requests          # required
.venv/bin/pip install -r agent/requirements.txt   # optional extras (pandas, etc.)
```

The only hard dependency is `requests`. Optional libs (`pandas`, `pyarrow`,
`huggingface_hub`, `kaggle`) unlock richer dataset profiling and downloads; the
scripts fall back to the stdlib when they're absent.

## Scripts

All scripts print JSON to stdout and progress/errors to stderr.

| Script | Purpose |
|--------|---------|
| `research.py status\|next\|list\|show\|find\|refs\|results\|verdict\|new\|set\|log\|link-run\|check` | Research tracker: what's next, what was tried, computed verdicts from metric rows, findings, decisions, handoffs (skill `research-tracker`) |
| `papers_search.py --query ... [--author ...] [--sources ...] [--limit N]` | Search PubMed / Semantic Scholar / arXiv / OpenAlex, merged + deduped |
| `papers_add.py --input picks.json --topic ...` | Download PDFs, record in DB, export BibTeX |
| `datasets_search.py --query ... [--sources ...]` | Search Hugging Face / Kaggle / Zenodo (free only) |
| `datasets_add.py --input ds.json --topic ...` | Download datasets into `datasets/<topic>/<slug>/` |
| `datasets_verify.py --id N \| --path DIR` | Profile schema/rows/dtypes/missing, write `REPORT.md` |
| `ingest_csv.py --csv FILE` | Import an existing dataset shortlist CSV as candidates |
| `library.py [--papers\|--datasets] [--topic ...] [--status ...]` | List / summarize the library |
| `colab_sync.py start\|run\|job\|logs\|pull\|status\|stop` | Drive a Colab session: upload code + datasets incrementally, run scripts/notebooks (`--experiment E###` links runs to the tracker), pull run records back |
| `colab_runs.py [--last\|--compare\|--ledger] [--name ...]` | Read Colab run records (with code/data provenance); `--compare` shows metric deltas; `--ledger` lists external-validation scorings |
| `workspace_check.py [--quick] [--only ...] [--fix]` | Reconcile library DB ↔ disk, packed files, OS table verifies, doc numbers, run provenance, validation ledger, agent symlinks; exits 1 on errors |

## Sources & credentials

- **Papers:** all keyless. Optional `ncbi_email`, `ncbi_api_key`,
  `semantic_scholar_api_key` in `config.yaml` raise rate limits.
- **Datasets:** Hugging Face & Zenodo are open; Kaggle needs a free token at
  `~/.kaggle/kaggle.json`. Only free datasets are surfaced.

## GPU work (Google Colab)

There is no local GPU. The agent drives a Colab runtime from the terminal with
Google's [`colab` CLI](https://github.com/googlecolab/google-colab-cli)
(`uv tool install google-colab-cli --with 'jupyter-kernel-client<1'`, then a one-time login described in the
`colab-compute` skill) through `colab_sync.py`:

```bash
.venv/bin/python agent/scripts/colab_sync.py start --dataset <slug>          # session + code + data + deps
.venv/bin/python agent/scripts/colab_sync.py run <script.py|notebook.ipynb>  # repeat freely
.venv/bin/python agent/scripts/colab_sync.py stop                            # pull records, release the VM
```

The local working tree is uploaded straight into the session — only changed
files after the first push — so nothing has to be committed, pushed, or
cloned. On the runtime, `agent/scripts/colab_env.py` provides the helpers (same
config, same `datasets/<topic>/<slug>/` paths as locally). Records written with
`colab_env.save_run()` come back to `.research/colab/runs/` automatically, and
`colab_runs.py --last` / `--compare` reads them. Settings live under `colab:` in
`.research/config.yaml`; the full workflow is in the `colab-compute` skill.

## Usage

Every session starts from `research/NOW.md` and ends with a handoff
(`research.py log`); the `research-tracking` rule makes agents do both. Ask
*"what's next?"*, *"what have we tried and did anything beat the clinical
baseline?"*, or *"what do we know about GSE53963?"* and the agent answers from
`research.py` queries.

Just talk to the agent (Cursor or Claude Code), e.g. *"find recent papers on
chemotherapy response prediction that use gene expression"*, *"verify the GDSC
dataset"*, or *"train a survival model on GSE14764 using a GPU"*. The `research-papers`,
`research-datasets`, and `colab-compute` skills drive the scripts above.
