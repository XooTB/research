# OS validation expression

Gene-symbol expression matrix for the held-out validation cohorts (`docs/os-train-validation-split.md` §4), **in the training pool's feature space**: rows are exactly the 11,474 common symbols of `os-training-pool/expression_pool.csv`, so a model trained on the pool can be scored directly. Join to `os-validation/labels.csv` on `sample_id` (matrix columns are that file's row order).

**Script:** `agent/scripts/os_validation_expression.py` (Python 3 stdlib only). Validation-side mirror of `os_pool_expression.py` — same drop rules, same max-mean collapse.

**Outputs** (under `datasets/ovarian-cancer-prognosis-ml/`):

| File | What |
|---|---|
| `platform-annotations/GPL6480.probe2symbol.tsv` | Agilent 4x44K probe → symbol (30,679 kept) |
| `platform-annotations/GPL14951.probe2symbol.tsv` | Illumina HT-12 probe → symbol (29,377 kept) |
| `platform-annotations/GPL2986.probe2symbol.tsv` | ABI HGS V2 probe → symbol (17,772 kept) |
| `os-validation/expression/<cohort>.csv` | per-cohort collapsed symbol × sample matrices |
| `os-validation/expression_validation.csv` | 11,474 symbols × 892 samples |
| `os-validation/expression_validation.symbols.txt` | row order (copied from the training pool) |
| `os-validation/validation_manifest.json` | coverage, collapse stats, anomalies |

---

## How to run

```bash
python3 agent/scripts/os_validation_expression.py all       # annotate + collapse + merge + verify
python3 agent/scripts/os_validation_expression.py verify    # exit 1 on failure
```

Prerequisite: `os-validation/labels.csv` (run `os_validation_labels.py all` first) and `os-training-pool/expression_pool.symbols.txt`.

---

## Annotation provenance

Downloaded 27 Aug 2026 (`platform-annotations/REPORT.md`, "Validation-cohort platforms" section). GPL6480 and GPL2986 are GEO `.annot.gz` (Aug 09 2016); GPL14951 has no standalone annot — the platform table was extracted from the family SOFT (last update Dec 22 2017, symbol column `Symbol`).

Drop rules identical to the training side (exclusive priority: control, then empty/`---`, then `///` multi-mapper):

| Platform | Probe rows | Control | empty/`---` | `///` multi | kept probes | unique symbols |
|---|---:|---:|---:|---:|---:|---:|
| GPL6480 (Agilent) | 41,108 | 15 | 10,370 | 44 | 30,679 | **19,529** |
| GPL14951 (Illumina) | 29,377 | 0 | 0 | 0 | 29,377 | **20,819** |
| GPL2986 (ABI) | 32,878 | 0 | 14,962 | 144 | 17,772 | **16,072** |

## Collapse rule

Identical to the training pool: per symbol, highest-mean probe across that cohort's `labels.csv` analysis samples; ties break on lexicographically smaller probe ID; source numeric strings copied unchanged (mean is a selector, not a transform). No batch correction — values stay platform-native (Agilent log-ratios incl. two-color GSE53963 Cy5/Cy3, Illumina one-color intensities, ABI).

| Cohort | Platform | dims (symbols × samples) | notes |
|---|---|---|---|
| gse32062 | GPL6480 | 19,529 × 260 | read from `expression.csv.zip` via zipfile (never unpacked) |
| gse53963 | GPL6480 | 19,529 × 160 | 14 TCGA-duplicate columns ignored (labels join) |
| gse17260 | GPL6480 | 19,529 × 110 | |
| gse140082 | GPL14951 | 20,819 × 191 | 189 non-subset columns ignored |
| gse49997 | GPL2986 | 16,072 × 171 | 33 non-analysis columns ignored (incl. 10 `excluded=yes`) |

## Final matrix

`expression_validation.csv`: **11,474 symbols × 892 samples**, 104,610,719 bytes (99.8 MiB — under GitHub's 100 MiB blob limit, margin ~0.25 MB; `github_pack.py pack` correctly skips it, but any regeneration that adds bytes must re-check).

- Columns: `symbol`, then all 892 `sample_id`s in `labels.csv` row order (260 + 160 + 110 + 191 + 171).
- Rows: the 11,474 training symbols, sorted (`expression_validation.symbols.txt`).

### Platform coverage of the training feature space

A symbol the platform doesn't assay is an **empty cell, not a dropped row** — coverage is a property of the array, and dropping rows would break alignment with the training matrix.

| Cohort | Symbols present | Coverage |
|---|---:|---:|
| gse32062 / gse53963 / gse17260 (GPL6480) | 11,328 / 11,474 | 98.73% |
| gse140082 (GPL14951) | 11,165 / 11,474 | 97.31% |
| gse49997 (GPL2986) | 10,682 / 11,474 | 93.10% |

Empty cells total **284,536** (2.8% of the matrix): mostly the coverage gaps above (146/309/792 symbols × cohort n), plus source-missing values — notably **GSM4153781** (gse140082, in the analysis set) which has 9,440 empty probes on the source matrix, and GSE53963's ~32.8k scattered empties. Downstream models must tolerate empties (or restrict scoring to a cohort's covered symbols).

## Verification results

`python3 agent/scripts/os_validation_expression.py all` (27 Aug 2026) exited 0.

| Check | Result |
|---|---|
| dims 11,474 × 892 | OK |
| columns == labels.csv `sample_id` order | OK |
| non-finite / non-float cells | 0 |
| empty cells | 284,536 (reported, legal — platform coverage) |
| per-cohort columns 260 / 160 / 110 / 191 / 171 | OK |
| packing | skipped (99.8 MiB < 100 MiB) |

---

## Next

Scoring notebooks must tolerate empty cells (or restrict to each cohort's covered symbols). Do not drop rows from this matrix to "clean" coverage — that would desynchronize it from `expression_pool.csv`. Batch correction / rank transforms, if any, belong in M4, not in a re-run of this script. If a regeneration pushes the CSV over 100 MiB, pack with `python3 agent/scripts/github_pack.py pack --path datasets/ovarian-cancer-prognosis-ml/os-validation`.

## Pointers

- Labels: `docs/os-validation-labels.md`
- Training-side mirror: `docs/os-training-expression.md`
- Annotation downloads: `datasets/ovarian-cancer-prognosis-ml/platform-annotations/REPORT.md`
- Workstream: `docs/current-focus-overall-survival.md`
