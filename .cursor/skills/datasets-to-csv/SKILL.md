---
name: datasets-to-csv
description: >-
  Convert collected research datasets from GEO series matrices, UCSC Xena
  matrices, TSV/TXT, Parquet, or Excel into CSV under each dataset's csv/
  folder. Use when the user asks to convert datasets to CSV, normalize
  downloaded data formats, export expression/phenotype tables, or prepare
  tracked datasets for analysis.
---

# Datasets to CSV

Converts files under `datasets/<topic>/<slug>/` into CSV. Writes outputs to
`<slug>/csv/` by default. Leaves originals untouched.

## Setup

- Python: `.venv/bin/python` · Script: `agent/scripts/datasets_to_csv.py`
- Stdlib handles GEO / Xena / TSV / CSV / gzip. Parquet and Excel need
  `pandas` (+ `pyarrow` for parquet).

## Workflow

```
- [ ] 1. Confirm target (topic, dataset dir, or single file)
- [ ] 2. Run conversion
- [ ] 3. Validate losslessness (validate_csv_conversion.py)
- [ ] 4. Spot-check outputs (row/col counts, phenotype columns)
- [ ] 5. Summarize what was written / skipped / failed
```

### Convert a whole topic

```bash
.venv/bin/python agent/scripts/datasets_to_csv.py --topic "<topic-slug>"
```

### Convert one dataset folder

```bash
.venv/bin/python agent/scripts/datasets_to_csv.py --path datasets/<topic>/<slug>
```

### Convert one file

```bash
.venv/bin/python agent/scripts/datasets_to_csv.py --path datasets/<topic>/<slug>/<file>
```

Flags:

| Flag | Effect |
|---|---|
| `--force` | Overwrite existing CSVs |
| `--expression-only` | GEO: skip `phenotype.csv` |
| `--out-dir <dir>` | Write all CSVs here instead of `<slug>/csv/` |

Large expression matrices (tens of thousands of rows) can take a minute; use a
generous command timeout. Conversion then packs any output **> 100 MB**
(`github_pack.py`); keep the unpacked CSV on disk and do not git-add it.

## Format rules

| Input | Detection | Output |
|---|---|---|
| GEO `*_series_matrix.txt` (`.gz` ok) | `!Series_` / `!Sample_` headers or filename | `expression.csv` + `phenotype.csv` |
| UCSC Xena / tab matrix (often extensionless, e.g. `HiSeqV2`, `OV_clinicalMatrix`) | Tab-delimited content | `<stem>.csv` |
| `.tsv` / `.txt` / `.csv` (+ `.gz`) | Extension / delimiter sniff | `<stem>.csv` |
| `.parquet` | Extension | `<stem>.csv` (needs pandas) |
| `.xlsx` / `.xls` | Extension | `<stem>.csv` or `<stem>_<sheet>.csv` (needs pandas) |

### GEO split

- **expression.csv** — probe/gene × sample matrix from
  `!series_matrix_table_begin` … `end`
- **phenotype.csv** — one row per sample; expands
  `!Sample_characteristics_ch1` `Key : Value` fields into columns; keeps
  accession, title, source, description, and other `!Sample_*` fields

Skip non-data files (`REPORT.md`, PDFs, `.soft`, archives) and anything
already under a `csv/` folder.

## After conversion

### Validate losslessness (required for TSV/Xena-style conversions)

After converting tabular files (TSV / Xena matrices), always verify no data
was lost or altered:

```bash
# Whole dataset dir (auto-pairs each original with csv/<stem>.csv)
.venv/bin/python agent/scripts/validate_csv_conversion.py --path datasets/<topic>/<slug>

# Single original file, or an explicit pair
.venv/bin/python agent/scripts/validate_csv_conversion.py --path datasets/<topic>/<slug>/<file>
.venv/bin/python agent/scripts/validate_csv_conversion.py --original <file> --csv <file>
```

Checks per pair: identical row counts, identical per-row column counts, and
byte-for-byte string equality of every cell. The original is parsed
independently of the converter (plain delimiter split), so converter bugs
can't mask themselves. Exit code 0 = lossless, 1 = any mismatch; the JSON
report samples up to 25 mismatches with row/col location and values.

Not applicable to GEO splits (expression.csv + phenotype.csv restructure the
data by design) or Parquet/Excel (type coercion is expected) — spot-check
those instead.

Read the JSON summary (`converted` / `skipped` / `errors`). For a quick check:

```bash
.venv/bin/python -c "import csv; p='datasets/<topic>/<slug>/csv/phenotype.csv'; \
  r=list(csv.reader(open(p))); print(len(r)-1, 'rows', len(r[0]), 'cols', r[0][:8])"
```

If the user still needs ML-ready joins (expression ↔ survival labels), do that
as a separate step — this skill only normalizes formats to CSV.

## Related

- Download / verify datasets: [research-datasets](../research-datasets/SKILL.md)
