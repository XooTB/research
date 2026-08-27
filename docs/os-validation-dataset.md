# OS validation set: compiled dataset

**Status:** complete and verified, 27 Aug 2026. This is the M2 validation-side deliverable (held out from training).
**Basis:** `docs/os-train-validation-split.md` §4 (platform-family split: validators = Agilent / Illumina / ABI; RNA-seq + Affymetrix stay in the training pool).
**Detail docs:** `docs/os-validation-labels.md` (label extraction, per-cohort traps, TCGA dedupe), `docs/os-validation-expression.md` (probe→gene collapse into the training feature space). Read those before modifying anything; this page is the map.
**Training-side mirror:** `docs/os-training-dataset.md`.

---

## 1. What exists and where

Everything lives under `datasets/ovarian-cancer-prognosis-ml/`:

| Path | Content | Size |
|---|---|---|
| `os-validation/labels.csv` | 892 patients × 15 cols (same schema as the training labels): cohort, ids, platform, histology, `os_time_days`, `os_event`, original time+unit, `event_definition`, age/stage/grade/residual, notes | small |
| `os-validation/expression_validation.csv` | **11,474 training-pool symbols × 892 samples**; columns are `labels.csv` `sample_id`s in row order | 99.8 MiB |
| `os-validation/expression_validation.symbols.txt` | row order of the matrix (= training pool `expression_pool.symbols.txt`) | small |
| `os-validation/expression/<cohort>.csv` | per-cohort collapsed symbol × sample matrices (5 files) | 23–51 MB each |
| `os-validation/validation_manifest.json` | machine-readable provenance: collapse rule, platform coverage, empty-cell counts | small |
| `platform-annotations/GPL6480.annot.gz`, `GPL2986.annot.gz` | raw GEO platform annotation (Aug 09 2016) | 7.4 / 4.0 MB |
| `platform-annotations/GPL14951.platform_table.soft.gz` | Illumina platform table extracted from family SOFT (no standalone `.annot.gz`) | 11 MB |
| `platform-annotations/GPL6480\|GPL14951\|GPL2986.probe2symbol.tsv` | frozen 1:1 probe→symbol maps after drop rules | small |
| `platform-annotations/REPORT.md` | download URLs, dates, row counts, spot-checks (validation-cohort section) | small |

Join rule: `expression_validation.csv` columns ≡ `labels.csv` rows, same order, keyed by `sample_id` (GSM accession). Rows are the same 11,474 symbols as `os-training-pool/expression_pool.csv`, so a model trained on the pool scores without remapping.

## 2. Tooling

Two stdlib-only Python 3 scripts (`/usr/bin/python3`; **no .venv, no pandas**). Full pipeline documentation is in the top-of-file docstrings; per-cohort / per-stage subcommands exist for debugging.

```bash
# Labels: extract → merge → verify against split-doc targets + leakage
python3 agent/scripts/os_validation_labels.py all       # writes labels.csv
python3 agent/scripts/os_validation_labels.py verify    # asserts 892/410, uniqueness, coding, train/validation disjointness
python3 agent/scripts/os_validation_labels.py gse53963  # any single cohort to stdout

# Expression: annotate → collapse → merge into training feature space → verify
python3 agent/scripts/os_validation_expression.py all
python3 agent/scripts/os_validation_expression.py verify
```

Prerequisites for expression: `os-validation/labels.csv` and `os-training-pool/expression_pool.symbols.txt`. Both scripts emit what they find — no hard-coded fudges. `expression_validation.csv` is 104,610,719 bytes (99.8 MiB): under GitHub's 100 MiB blob limit with ~0.25 MB margin. `github_pack.py pack --path …/os-validation` currently skips it; **any regeneration that adds bytes must re-check**.

## 3. Final counts (verified 27 Aug 2026)

| Cohort | n / deaths | Platform | Role | Collapsed symbols | Event definition |
|---|---|---|---|---|---|
| GSE32062 | 260 / 121 | GPL6480 | Flagship | 19,529 | all-cause |
| GSE53963 | **160 / 139** | GPL6480 | Second flagship (TCGA-deduped) | 19,529 | all-cause |
| GSE17260 | 110 / 46 | GPL6480 | Within-platform replication | 19,529 | all-cause |
| GSE140082 | 191 / 56 | GPL14951 | Secondary, immature | 20,819 | all-cause |
| GSE49997 | 171 / 48 | GPL2986 | Tertiary, supportive | 16,072 | all-cause |
| **Set** | **892 / 410** | 3 families | | rows = **11,474 training symbols** | all all-cause |

GSE53963's split-doc estimate "~160/~140" resolved to **160/139**: every one of the 14 dropped TCGA duplicates was a death (174−14, 153−14). All other n/deaths matched the split doc exactly. `verify` confirmed zero `sample_id` overlap with the training pool.

Coverage of the 11,474 training symbols (empty cells, not dropped rows): GPL6480 98.73%, GPL14951 97.31%, GPL2986 93.10%. Total empty cells: 284,536 (2.8% of the matrix).

## 4. How it was built

**Labels** (`os_validation_labels.py`), one extractor per cohort, shared schema with the training pool:

1. **GSE32062** — `csv/phenotype.csv`. All 260 HGSOC. Time `os (m)` months; event `death (1)`. Ignore GEO `status` (public-on date). Residual `surgery status` (one row is `Optimal`).
2. **GSE53963** — converter `phenotype.csv` is **unusable** (ch1 only; duplicate ch2 lines overwrite). Reparse `GSE53963_series_matrix.txt.gz` `!Sample_characteristics_ch2` as per-sample `key : value` (optional `substage` / `tcga_sampleid` shift columns — never index by line). Drop any sample with a non-empty `tcga_sampleid` (14 barcodes, listed at extraction time). Time `time_fu_months`; event `vital_status` Dead/Alive.
3. **GSE17260** — `csv/phenotype.csv`. All 110 serous **including 26 grade-1** (required for the 110/46 target). Time `overall survival (m)`; event `death (1)`.
4. **GSE140082** — `csv/phenotype.csv` (converter correct). Subset `histology.serous==serous` AND `newgrade==high.grade` AND `figo_stage` in {III,IV}. Time `final_ostm` **days**; event `final_osid`. Treatment arm in `notes`.
5. **GSE49997** — drop `excluded==yes` (10 rows; GSMs remain on the expression matrix). Keep `histology==Serous`. Time `os month`; event `os event`. **`figo grade` is FIGO stage**; real grade is `grade`.

Times converted to days with 365.25 / 12; originals preserved. Cox-usable filter: finite `os_time_days >= 1`.

**Expression** (`os_validation_expression.py`): GPL6480 / GPL14951 / GPL2986 probe→symbol maps with the same drop rules as the training pool (control probes, empty/`---` symbols, `///` multi-mappers). Per cohort, max-mean collapse on that cohort's analysis samples. GSE32062 expression is streamed from `expression.csv.zip` (never unpacked). Merge writes **training-symbol rows** (not a new intersection): a symbol the platform does not assay is an empty cell.

**Supporting conversions (27 Aug):** `datasets_to_csv.py` produced GSE53963 and GSE140082 `csv/` folders. GSE53963 phenotype CSV is kept for provenance only. Platform annotations: see `platform-annotations/REPORT.md` (GPL14951 had no `.annot.gz`; table extracted from family SOFT).

## 5. Decisions a future agent must not silently undo

1. **Empty cells are legal on the validation matrix** (unlike the training pool, which has none). `verify` asserts finite-or-empty, not no-empty. Scoring must tolerate NAs or restrict to each cohort's covered symbols (ABI is the worst: 792 of 11,474 symbols absent).
2. **TCGA dedupe is by ch2 `tcga_sampleid`, not titles.** Titles contain no barcodes. All 14 dropped samples are deaths; changing the rule changes 160/139.
3. **GSE17260 grade-1 serous stays.** Filtering grade ≥2 yields 84/39, not the split-doc 110/46. Possible LGSOC contamination is disclosed in notes, not filtered.
4. **No batch correction, no residual/stage recode.** Values stay platform-native (Agilent log-ratios including two-color GSE53963 Cy5/Cy3, Illumina intensities, ABI). Residual vocabularies differ (`optimal`/`suboptimal` vs `not optimal` vs `Sub-optimal` vs Yes/No). Recode at modelling time.
5. **GSE32062 expression stays zipped.** Stream it; do not unpack `expression.csv.zip` onto disk.
6. **`verify` is the contract.** Re-running must reproduce 892/410 and 11,474 × 892, plus zero leakage into `os-training-pool/labels.csv`.

## 6. Next steps (this dataset is an input, not the model)

1. **M3** — clinical-only Cox on every compiled cohort. Flagship GSE32062 / GSE17260 have **no age** → baseline is stage + residual. Age exists for GSE53963, GSE140082, GSE49997. See covariate completeness in `docs/os-validation-labels.md`.
2. **M4** — train on `os-training-pool/`, score on all five validators. Fill C-index + KM log-rank + ΔC vs clinical baseline per cohort. Handle empties; decide (or not) on batch correction / rank features.
3. GSE9891 survival, PanCanAtlas CDR, TCGA U133A remain optional (focus doc §4) and do not change this table.

## 7. Pointers

- Labels detail (schema, traps, completeness): `docs/os-validation-labels.md`
- Expression detail (annotation, coverage, empty-cell policy): `docs/os-validation-expression.md`
- Training pool (the feature space this matrix is aligned to): `docs/os-training-dataset.md`
- Split rationale: `docs/os-train-validation-split.md`
- Workstream + milestones: `docs/current-focus-overall-survival.md`
- Messy-field traps: `docs/ovarian-cancer-prognosis-opportunities.md` Appendix B
