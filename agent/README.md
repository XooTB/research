# Research Agent

A Cursor-driven assistant for working with research **papers** and **datasets**.
Python scripts fetch, download, and profile; the Cursor agent does the reasoning
(relevance ranking, criteria screening, usability verdicts). Everything is
stored locally in this workspace.

## Layout

```
papers/<topic>/<year>-<author>-<title>/paper.pdf   # organized PDFs
datasets/<topic>/<slug>/ + REPORT.md               # datasets + verification
notebooks/                                          # notebooks run on Colab GPUs
.research/library.db                               # SQLite: papers, datasets, notes
.research/references.bib                            # auto-exported BibTeX
.research/config.yaml                               # sources, paths, credentials, colab
.research/colab/runs/                               # run records from Colab sessions
agent/scripts/                                      # the tools (below)
.cursor/skills/research-papers|research-datasets|colab-compute   # how the agent uses them
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
| `papers_search.py --query ... [--author ...] [--sources ...] [--limit N]` | Search PubMed / Semantic Scholar / arXiv / OpenAlex, merged + deduped |
| `papers_add.py --input picks.json --topic ...` | Download PDFs, record in DB, export BibTeX |
| `datasets_search.py --query ... [--sources ...]` | Search Hugging Face / Kaggle / Zenodo (free only) |
| `datasets_add.py --input ds.json --topic ...` | Download datasets into `datasets/<topic>/<slug>/` |
| `datasets_verify.py --id N \| --path DIR` | Profile schema/rows/dtypes/missing, write `REPORT.md` |
| `ingest_csv.py --csv FILE` | Import an existing dataset shortlist CSV as candidates |
| `library.py [--papers\|--datasets] [--topic ...] [--status ...]` | List / summarize the library |
| `colab_check.py [--dataset <slug>]` | Pre-flight before a Colab session: config sanity, unpushed commits, dataset reachable from the remote |

## Sources & credentials

- **Papers:** all keyless. Optional `ncbi_email`, `ncbi_api_key`,
  `semantic_scholar_api_key` in `config.yaml` raise rate limits.
- **Datasets:** Hugging Face & Zenodo are open; Kaggle needs a free token at
  `~/.kaggle/kaggle.json`. Only free datasets are surfaced.

## GPU work (Google Colab)

There is no local GPU, so model training happens on a free Colab runtime
attached to a local notebook via Google's Colab extension for Cursor.

```bash
.venv/bin/python agent/scripts/colab_check.py --dataset <slug>   # push whatever it flags
```

Then open `notebooks/colab-smoke-test.ipynb`, pick *Select Kernel → Colab →
GPU*, and run it. The bootstrap cell sparse-clones this repo onto the runtime
and `agent/scripts/colab_env.py` provides the runtime helpers — same config,
same `datasets/<topic>/<slug>/` paths as the local scripts. Settings live under
`colab:` in `.research/config.yaml`; the full workflow and its failure modes are
in the `colab-compute` skill.

The runtime clones the **GitHub remote**, so anything not pushed does not exist
as far as a notebook is concerned.

## Usage

Just talk to the Cursor agent, e.g. *"find recent papers on chemotherapy
response prediction that use gene expression"*, *"verify the GDSC dataset"*, or
*"train a survival model on GSE14764 using a GPU"*. The `research-papers`,
`research-datasets`, and `colab-compute` skills drive the scripts above.
