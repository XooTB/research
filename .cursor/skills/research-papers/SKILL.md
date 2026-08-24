---
name: research-papers
description: >-
  Find, filter, download, and organize academic/research papers across PubMed,
  Semantic Scholar, arXiv, and OpenAlex. Use when the user wants to search for
  papers by topic/author/category, screen papers against criteria, download
  PDFs, build a BibTeX bibliography, or ask what papers are in their library.
---

# Research Papers

A local research library lives in this workspace. Python scripts fetch and
organize; **you (the agent) do the reasoning** — ranking relevance, applying
the user's criteria to abstracts, and summarizing. Scripts print JSON to stdout
(progress goes to stderr).

## Setup (run once)

Interpreter and scripts:
- Python: `.venv/bin/python`
- Scripts: `agent/scripts/`

If `.venv` is missing: `python3 -m venv .venv && .venv/bin/pip install requests`.
Optional extras from `agent/requirements.txt` improve things but aren't required.

## Workflow

```
- [ ] 1. Search sources for the topic/author
- [ ] 2. Rank + apply the user's criteria to the returned abstracts
- [ ] 3. Present a shortlist; let the user pick
- [ ] 4. Add picks (download PDF + record + BibTeX)
```

### 1. Search

```bash
.venv/bin/python agent/scripts/papers_search.py --query "<topic>" [--author "<name>"] [--sources pubmed,arxiv] [--limit 15]
```

Returns merged, de-duplicated results with `title, authors, year, venue,
abstract, doi, url, pdf_url, found_in`. Read the JSON yourself.

### 2. Rank + filter (this is your job, not the script's)

- Rank by relevance to the user's actual intent, not keyword overlap.
- Apply requested criteria against `abstract` + metadata (e.g. "uses patient
  data", "deep learning", "released code", "n > 1000"). State for each shortlisted
  paper *why* it matches. Criteria depth is abstract-level by default; if a
  criterion truly needs full text, say so rather than guessing.
- Note which sources each paper was `found_in`.

### 3. Present

Show a concise shortlist (title, authors et al., year, venue, one-line why).
Ask which to add, or add all if the user already said so.

### 4. Add to library

Write the chosen paper dicts (verbatim from the search JSON) to a temp JSON
file, then:

```bash
.venv/bin/python agent/scripts/papers_add.py --input /tmp/picks.json --topic "<topic-slug>"
```

This downloads the PDF when a usable `pdf_url` exists (open-access only —
report `pdf_ok:false` honestly when it doesn't), files it under
`papers/<topic>/<year>-<author>-<title>/paper.pdf`, records it in the SQLite
DB, and refreshes `.research/references.bib`. Use `--no-pdf` to record metadata
only.

When at least one paper got a PDF, the add also re-runs dataset extraction +
paper↔dataset linking for that topic automatically (see the
paper-dataset-extractor skill; links land in the DB's `paper_datasets`
table). Manual fallback if needed:

```bash
.venv/bin/python agent/scripts/paper_dataset_links.py --topic <slug>
```

## Inspecting the library

```bash
.venv/bin/python agent/scripts/library.py                 # summary counts
.venv/bin/python agent/scripts/library.py --papers --topic <slug>
```

## Notes

- No API keys required. Add `ncbi_email` / `semantic_scholar_api_key` in
  `.research/config.yaml` to raise rate limits.
- Downloads need real network egress; when running download steps request full
  network permission for that command.
- PDFs over 100 MB are zipped for GitHub (`github_pack.py`); the unpacked
  `paper.pdf` stays on disk. After a clone, run `github_pack.py unpack`.
