---
name: medical-dataset-finder
description: Searches Kaggle, Hugging Face Datasets, the UCI ML Repository, PhysioNet, data.gov (including data.cdc.gov), the WHO Global Health Observatory, and Zenodo for the top 5 most popular publicly available medical datasets on a research topic the user supplies, then produces an organized Excel spreadsheet listing each dataset's name, source, link, columns, description, file format, size, license, last-updated date, and popularity metric. Use this skill whenever the user asks to find or compile medical, clinical, biomedical, epidemiological, or public-health datasets for a research topic — including phrasings like "find datasets on X," "what data is available for X research," "I need data for a study on X," "look up data on X disease/condition," or asks for a curated list of medical data sources, even when they don't explicitly say "Excel" or name a specific repository.
---

# Medical Dataset Finder

Find the top 5 most popular publicly available medical datasets for a research topic the user provides, gather metadata for each, and emit a single Excel spreadsheet listing them.

## Inputs

The user supplies one research topic per invocation, e.g. "diabetes prediction," "chest X-ray pneumonia detection," "EHR mortality prediction," "skin lesion classification," "COVID-19 hospitalizations." Treat the topic as the user wrote it, but expand it mentally with synonyms when searching (e.g. "heart attack" → also try "myocardial infarction"). If the topic is ambiguous (e.g. just "cancer"), ask one clarifying question before starting; otherwise proceed.

## Output

A single `.xlsx` file with one worksheet ("Datasets"), 5 data rows, and these columns in this order:

| # | Column | What goes in it |
|---|---|---|
| 1 | Topic | The user's research topic, repeated on every row |
| 2 | Dataset Name | The dataset's title as listed on the source page |
| 3 | Source | Exactly one of: `Kaggle`, `Hugging Face`, `UCI ML`, `PhysioNet`, `data.gov`, `WHO GHO`, `Zenodo` |
| 4 | Link | Direct file download URL if publicly accessible without auth; otherwise the dataset page URL |
| 5 | Link Type | `direct file` or `page` — so the user knows what they'll click into |
| 6 | File Format | `CSV`, `Parquet`, `JSON`, `DICOM`, `NIfTI`, `multi-file`, etc. |
| 7 | Columns | Comma-separated list of column names. For image/audio/multi-file datasets, list field types or the main file types. Use `Not listed on source` if truly unavailable — never fabricate. |
| 8 | Description | 1–3 sentence paraphrase of what the dataset contains. Do not copy more than ~14 words verbatim from the source. |
| 9 | File Size | Approximate total size with units (e.g. `1.2 GB`, `45 MB`). Use `Unknown` if not listed. |
| 10 | License | E.g. `CC0`, `CC BY 4.0`, `Open Data Commons`, `Restricted (DUA required)`. Use `Unknown` if not listed. |
| 11 | Last Updated | `YYYY-MM-DD` if known, else `YYYY`, else `Unknown`. |
| 12 | Popularity | Source-native metric, e.g. `12,400 upvotes` (Kaggle), `3.2k likes / 180k downloads` (HF), `850 citations` (PhysioNet), `45 views` (Zenodo). Use `Unknown` if not listed. |

## Workflow

### Step 1 — Search every source

Run the agent's web search tool (`web_search` in Cursor, `WebSearch` in Claude Code) once per source. Do **not** use bash `curl` / `wget` for this — the bash environment usually can't reach kaggle.com, huggingface.co, physionet.org, etc. directly.

Use these query templates as a starting point (substitute the topic):

- Kaggle: `site:kaggle.com/datasets <topic>`
- Hugging Face: `site:huggingface.co/datasets <topic>`
- UCI ML: `site:archive.ics.uci.edu <topic>` or `UCI ML repository <topic>`
- PhysioNet: `site:physionet.org <topic>`
- data.gov: `site:catalog.data.gov <topic>` AND `site:data.cdc.gov <topic>`
- WHO GHO: `site:who.int "Global Health Observatory" <topic>`
- Zenodo: `site:zenodo.org <topic> medical`

Detailed per-source extraction tips live in `references/sources.md` — read that file before pulling detail pages.

If a source returns nothing relevant for the topic, that's fine — note it mentally and move on. The output should still aim for 5 datasets total, drawn from whichever sources do have good matches.

### Step 2 — Triage and pick the top 5

You'll usually have 15–30 candidates. Pick the **5 most popular overall**, judging across sources. Popularity signals differ — see `references/sources.md` — so this is partly judgment:

- A Kaggle dataset with 20K downloads and a PhysioNet dataset with 200 citations are both "very popular" — both can win.
- Avoid duplicate uploads of the same underlying dataset (Kaggle especially has many copies of e.g. the Wisconsin Breast Cancer set). Pick the most-upvoted variant.
- When two candidates are tied on popularity, prefer source diversity — don't return 5 Kaggle datasets if a PhysioNet or UCI dataset is comparably useful and adds variety.
- For epidemiology topics (COVID, flu, dengue), prefer datasets updated within the last ~12 months unless the user is clearly asking for historical data.

### Step 3 — Fetch each winner's detail page

For each of the 5, `web_fetch` the dataset's page and extract every field in the output schema. `references/sources.md` has source-specific pointers for where each field lives.

For column names specifically, follow the source-specific guidance in the references file. If columns truly aren't recoverable (e.g. an imaging dataset with no schema, or a Zenodo deposit with only PDFs), write `Not listed on source` rather than guessing.

### Step 4 — Build the Excel via the bundled script

Stage a JSON file with the gathered metadata, then run the bundled builder. It produces a polished, hyperlinked spreadsheet with a frozen header row, sized columns, and consistent formatting — far more reliable than re-deriving openpyxl details every time.

```bash
# from the skill directory
python3 scripts/build_excel.py \
    --input /home/claude/datasets.json \
    --output /mnt/user-data/outputs/<topic_slug>_datasets.xlsx
```

Where `<topic_slug>` is the topic lowercased with spaces replaced by underscores, e.g. `diabetes_prediction_datasets.xlsx`.

The JSON must look like:

```json
{
  "topic": "diabetes prediction",
  "datasets": [
    {
      "name": "Pima Indians Diabetes Database",
      "source": "Kaggle",
      "link": "https://www.kaggle.com/datasets/uciml/pima-indians-diabetes-database",
      "link_type": "page",
      "file_format": "CSV",
      "columns": "Pregnancies, Glucose, BloodPressure, SkinThickness, Insulin, BMI, DiabetesPedigreeFunction, Age, Outcome",
      "description": "A binary classification dataset of 768 female patients of Pima Indian heritage, used to predict diabetes onset from diagnostic measurements.",
      "file_size": "9 KB",
      "license": "CC0",
      "last_updated": "2016-10-06",
      "popularity": "12,400 upvotes"
    }
  ]
}
```

If `openpyxl` isn't installed, the script tells you the install command (`pip install openpyxl --break-system-packages`).

### Step 5 — Present the file

After the script writes the file, call `present_files` with the .xlsx path so the user can download it. Keep the chat reply short: a one-line summary plus a brief recap of the 5 datasets is enough — the spreadsheet itself is the deliverable.

## Things to watch for

- **Sponsored / duplicate uploads on Kaggle** — many medical reference datasets (Wisconsin Breast Cancer, Heart Disease UCI, Pima Diabetes) have 10–30 reuploads. Keep one per topic, prefer the most-upvoted.
- **DUA-locked PhysioNet datasets** (MIMIC-III, MIMIC-IV, eICU, Chest X-ray 14) — still include them when they're the canonical resource for the topic. Set Link Type to `page` and put `Restricted (DUA required)` in the License column.
- **WHO GHO entries are indicators, not files** — treat the indicator URL as the link, set File Format to `CSV (export)`, and use the indicator's standard schema (`Country`, `Year`, `Sex`, `Indicator`, `Value`, etc.) for Columns.
- **Zenodo is broad** — most of it is not medical. If a Zenodo result is a single PDF or a code release rather than a real dataset, drop it.
- **Don't fabricate fields** — if you can't find the license, write `Unknown`; if columns aren't documented, write `Not listed on source`. Made-up metadata is worse than admitting ignorance.

## Edge cases

- **Topic returns fewer than 5 plausible datasets across all 7 sources** — return what you have (could be 3 or 4) and note in your chat reply that fewer than 5 strong matches were found. Don't pad with weak datasets.
- **User asks for a non-medical topic** — the source list is medical-tilted; still try, but tell the user the sources may be a poor fit and suggest they confirm or pick a domain-appropriate skill.
- **User provides multiple topics in one message** — ask whether they want one combined file or one file per topic before proceeding. Default to one file per topic if they don't clarify.
