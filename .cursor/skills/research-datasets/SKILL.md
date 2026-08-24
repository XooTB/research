---
name: research-datasets
description: >-
  Find, download, and verify research datasets from Hugging Face, Kaggle,
  Zenodo, or direct URLs. Use when the user wants to discover free datasets for
  a topic, download one, inspect its structure/schema (columns, rows, dtypes,
  missing values, file formats, size), judge usability, or manage their tracked
  dataset library.
---

# Research Datasets

Datasets are organized under `datasets/<topic>/<slug>/` with a `REPORT.md`
verification report per dataset, and tracked in the SQLite library. Scripts
fetch and profile; **you (the agent) judge relevance and usability**. Only
**free** datasets are surfaced.

## Setup

- Python: `.venv/bin/python`  ·  Scripts: `agent/scripts/`
- Kaggle needs `~/.kaggle/kaggle.json` (free token) or `KAGGLE_USERNAME`/
  `KAGGLE_KEY`. Missing creds → Kaggle is skipped gracefully with a note.
- `pandas` + `pyarrow` (optional) enable dtype/missing-value profiling and
  `.parquet`. Without them, CSV/TSV still profile via stdlib.

## Workflow

```
- [ ] 1. Search sources for candidates
- [ ] 2. Rank + check against the user's requirements
- [ ] 3. Download the chosen dataset(s)
- [ ] 4. Verify structure/usability -> REPORT.md, then summarize the verdict
```

### 1. Search

```bash
.venv/bin/python agent/scripts/datasets_search.py --query "<topic>" [--sources huggingface,zenodo,kaggle] [--limit 15]
```

Returns `name, source, source_id, url, description, license, size_hint,
file_format, is_free` plus popularity signals. Read the JSON.

### 2. Rank + check (your job)

Judge fit against what the user needs: required columns/labels, task type,
size, license, format. Prefer well-licensed, reasonably sized, popular sets.
Call out anything that looks paywalled, gated, or license-restricted.

### 3. Download

Write chosen dataset dicts to a temp JSON file, then:

```bash
.venv/bin/python agent/scripts/datasets_add.py --input /tmp/ds.json --topic "<topic-slug>"
```

Downloads into `datasets/<topic>/<slug>/` and records the entry. For an
arbitrary link, use an entry like
`{"source":"direct","url":"https://...","name":"...","topic":"..."}`.
Use `--no-download` to track as a candidate without fetching.

If an extraction CSV exists (`docs/extracted/<topic>-datasets.csv`, written by
the paper-dataset-extractor skill), adding datasets also re-syncs paper↔dataset
links in the DB automatically — newly tracked datasets get linked to papers
that cite their accessions.

Downloads need network egress — request full network permission for the
download command. Large datasets (multi-GB) can be slow; set a generous
timeout and check progress. `datasets_add.py` then packs any file over
100 MB for GitHub (see the github-file-size rule); unpacked originals stay
on disk and are gitignored. After a clone, restore them with:

```bash
.venv/bin/python agent/scripts/github_pack.py unpack
```

### 4. Verify + usability

```bash
.venv/bin/python agent/scripts/datasets_verify.py --id <dataset_id>
# or:  --path datasets/<topic>/<slug>
```

Profiles every file (columns, rows, dtypes, missing %, formats, size), writes
`REPORT.md`, and marks the dataset `verified` in the DB. Then **you** write the
usability verdict: does it have the needed columns/labels? enough rows? clean
enough? any red flags? Fill the "Usability verdict" section of `REPORT.md` and
summarize in chat.

## Inspecting the library

```bash
.venv/bin/python agent/scripts/library.py                          # summary
.venv/bin/python agent/scripts/library.py --datasets [--topic <slug>] [--status candidate|downloaded|verified]
```

## Ingesting an existing shortlist CSV

```bash
.venv/bin/python agent/scripts/ingest_csv.py --csv "Datasets  - Drug & Treatment.csv"
```

Records each row as a tracked candidate (upsert-safe to re-run).
