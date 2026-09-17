---
name: paper-dataset-extractor
description: >-
  Extract dataset references (GEO/SRA/dbGaP/ArrayExpress accessions, data
  repository URLs, named resources like TCGA/cBioPortal, DOIs) from the PDFs of
  collected papers into a CSV/JSON inventory with sentence-level context, then
  download the datasets. Use whenever the user asks to "extract the datasets
  used in these papers", find which datasets a paper library used, build a
  dataset inventory from papers, or get data out of a paper collection —
  instead of reading PDFs with an LLM.
---

# Paper Dataset Extractor

Deterministically mines `papers/<collection>/*/paper.pdf` for dataset
references and emits `docs/extracted/<collection>-datasets.{csv,json}` —
**deterministic extraction first, LLM judgment second, download always**:
the script finds candidates, you triage, then download every obtainable
dataset without asking for confirmation. Only skip gated/paywalled ones.

## Setup

- Python: `.venv/bin/python` with `pymupdf` installed
  (`.venv/bin/pip install pymupdf` if missing).
- Papers without `paper.pdf` on disk are skipped — extraction only covers
  downloaded PDFs; fall back to LLM-over-abstracts for the rest.

## Scope first — pick the right collection

The workspace holds multiple unrelated paper collections under `papers/`.
**Never run the extractor bare (all collections) unless the user explicitly
asks for everything.** Decide the target collection from context, in this
order:

1. Explicit mention ("the ovarian cancer papers", "from 2011-bell…")
2. The topic of the current conversation / files the user has open
   (e.g. `docs/ovarian-cancer-prognosis-ml.md` → `ovarian-cancer-prognosis-ml`)
3. Recently added/modified collections in `papers/`

If still ambiguous (multiple active topics, no signal), ask the user which
collection before running anything. Downloads in step 3 must stay within the
same topic slug — never pull datasets for other topics.

## Workflow

```
- [ ] 0. Determine the target collection from context (see "Scope first")
- [ ] 1. Run the extractor over that collection only
- [ ] 2. Triage findings (dedupe across papers, drop reference-list noise)
- [ ] 3. Download every obtainable dataset via the research-datasets skill
- [ ] 4. Update the collection's dataset inventory doc with results
```

### 1. Extract

```bash
.venv/bin/python agent/scripts/paper_datasets_extract.py --collection <collection>
```

(The no-argument all-collections mode exists for maintenance/regeneration
only — do not use it to answer a topic-specific request.)

Each run also syncs paper↔dataset links into the DB's `paper_datasets` table
(evidence + context, matched against already-tracked datasets), so step 3's
record-keeping includes the DB linkage automatically. Manual re-sync:
`.venv/bin/python agent/scripts/paper_dataset_links.py --topic <collection>`.

Output rows: `paper, kind, value, url, context`.

- `kind`: accession type (`GEO series`, `SRA/BioProject`, `dbGaP`, …),
  `url`, `DOI`, or `name:<Resource>` (TCGA, cBioPortal, curatedOvarianData…)
- `url`: canonical link, pre-built for known accession types
- `context`: ±160 chars around the match — use it to judge "dataset used in
  this study" vs "merely cited"

### 2. Triage

- Group by `value` across papers — most-reused datasets are usually the
  priority cohorts.
- Drop DOIs that are just references (figure DOIs like
  `10.1371/journal.pcbi.XXXXXXX.g001`, citations) unless the context shows
  data deposition.
- Prefer findings whose context mentions "deposited", "available at",
  "we used", "downloaded from".

### 3. Download — default action, do this without asking

For every surviving candidate, attempt a download. Only skip (with a note)
when a resource is truly gated: dbGaP/EGA controlled access, login-walled
portals, or paywalled supplements.

Build direct-download URLs per repository, then register via the
`research-datasets` skill (`datasets_add.py` with a `direct` entry, then
`datasets_verify.py`):

| Kind | Direct download recipe |
|---|---|
| `GSEnnnnn` | Matrix: `https://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnnnnn/GSEnnnnn/matrix/GSEnnnnn_series_matrix.txt.gz`; supplements under `.../suppl/` |
| `E-MTAB-nnnn` | `https://www.ebi.ac.uk/biostudies/files/E-MTAB-nnnn/` |
| `TCGA` | UCSC Xena: `https://tcga.xenahubs.net` hub (expression + clinical); GDC portal for raw |
| `zenodo` / `figshare` / `osf` DOI | Resolve the DOI, download the record's files |
| Bioconductor data pkg (e.g. curatedOvarianData) | Note as R-package dependency; don't raw-download |

GEO FTP rule: `GSEnnnnn` bucket = accession with last 3 digits replaced by
`nnn` (GSE9891 → `GSE9nnn`, GSE140082 → `GSE140nnn`).

Downloads need full network permission and generous timeouts for large
files.

### 4. Record

Update `docs/<topic>-datasets.md` (or equivalent inventory doc): mark each
dataset downloaded (local path) / skipped (reason), with links. If this served
the active workstream, record why a dataset was skipped or excluded as a
decision (`research.py new decision --refs <dataset-slug>`), and planned
follow-ups (e.g. "attach survival labels for GSEnnnnn") as tasks.

## Tuning

Patterns live at the top of the script: `ACCESSION_PATTERNS`,
`NAMED_RESOURCES`, `DATA_URL_DOMAINS`. Extend them when a new repository or
accession format shows up, then re-run — output is regenerated in place.
