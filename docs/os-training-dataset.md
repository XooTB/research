# OS training pool: compiled dataset

**Status:** complete and verified, 27 Aug 2026. This is the M2 training-side deliverable.
**Basis:** `docs/os-train-validation-split.md` (platform-family split: pool = RNA-seq + Affymetrix; Agilent/Illumina/ABI stay held out).
**Detail docs:** `docs/os-training-labels.md` (label extraction, per-cohort traps), `docs/os-training-expression.md` (probe→gene collapse, annotation provenance). Read those before modifying anything; this page is the map.

---

## 1. What exists and where

Everything lives under `datasets/ovarian-cancer-prognosis-ml/`:

| Path | Content | Size |
|---|---|---|
| `os-training-pool/labels.csv` | 751 patients × 15 cols: cohort, ids, platform, histology, `os_time_days`, `os_event`, original time+unit, `event_definition`, age/stage/grade/residual, notes | small |
| `os-training-pool/expression_pool.csv` | **11,474 gene symbols × 751 samples**; columns are `labels.csv` `sample_id`s in row order | 76.7 MB |
| `os-training-pool/expression_pool.symbols.txt` | row order (symbols, sorted) of the pool matrix | small |
| `os-training-pool/expression/<cohort>.csv` | per-cohort collapsed symbol × sample matrices (6 files) | 6–43 MB each |
| `os-training-pool/expression_manifest.json` | machine-readable provenance: collapse rule, annotation drop counts, per-stage symbol counts | small |
| `platform-annotations/GPL96.annot.gz`, `GPL570.annot.gz` | raw GEO platform annotation (Aug 09 2016) | 4.5 / 8.5 MB |
| `platform-annotations/GPL96.probe2symbol.tsv`, `GPL570.probe2symbol.tsv` | frozen 1:1 probe→symbol maps after drop rules | small |
| `platform-annotations/REPORT.md` | download URLs, dates, row counts, spot-checks | small |

Join rule: `expression_pool.csv` columns ≡ `labels.csv` rows, same order, keyed by `sample_id` (TCGA barcode or GSM accession).

## 2. Tooling

Two stdlib-only Python 3 scripts (`/usr/bin/python3`; **no .venv, no pandas** in this workspace). Both have full pipeline documentation in their top-of-file docstrings and granular subcommands for debugging.

```bash
# Labels: extract → merge → verify against split-doc targets
python3 agent/scripts/os_pool_labels.py all       # writes labels.csv
python3 agent/scripts/os_pool_labels.py verify    # asserts 751/485, uniqueness, coding; exit 1 on failure
python3 agent/scripts/os_pool_labels.py gse30161  # any single cohort to stdout

# Expression: annotate → collapse → merge → verify
python3 agent/scripts/os_pool_expression.py all   # full pipeline
python3 agent/scripts/os_pool_expression.py verify
```

Both scripts emit what they find — no hard-coded fudges. If `verify` fails after a re-run, treat it as a real data discrepancy, not a test to silence. `expression_pool.csv` is under the 100 MB GitHub limit, so `github_pack.py` packing was not triggered; if a future change pushes it over, run `python3 agent/scripts/github_pack.py pack --path datasets/ovarian-cancer-prognosis-ml/os-training-pool`.

## 3. Final counts (verified against the split doc, exact match)

| Cohort | n / deaths | Platform | Collapsed symbols | Event definition |
|---|---|---|---|---|
| TCGA-OV HiSeqV2 | 302 / 182 | RNA-seq | 20,530 | all-cause |
| GSE26712 | 185 / 129 | GPL96 | 12,502 | DOD-flavored |
| GSE63885 | 70 / 62 | GPL570 | 20,848 | DOD-flavored |
| GSE26193 | 79 / 60 | GPL570 | 20,848 | all-cause |
| GSE30161 | 47 / 33 | GPL570 (FFPE) | 20,848 | all-cause |
| GSE14764 | 68 / 19 | GPL96 | 12,502 | all-cause |
| **Pool** | **751 / 485** | 3 families | **intersection 11,474** | mixed (disclosed in `event_definition`) |

Split doc estimated ~12k common symbols; actual is 11,474. **GPL96 is the bottleneck** (12,502 symbols after drops) — adding GPL570 cohorts cannot grow the gene set.

## 4. How it was built (the short version; details in the two detail docs)

**Labels** (`os_pool_labels.py`): per-cohort extractors → one schema. Traps handled: GSE30161 reparsed per-cell `key : value` from the raw series matrix (its converted CSV is column-shifted); GSE26712 vital status read from `status`, not the GEO date field `status_2`; GSE63885 characteristic keys matched by substring (colons/commas inside keys); serous subsetting for GSE26193/GSE30161/GSE14764/GSE63885; TCGA restricted to primary tumors with `os_time ≥ 1 day` (drops `TCGA-04-1357-01` → 302); all times normalized to days (×365.25/yr, ×365.25/12/mo) with originals preserved.

**Expression** (`os_pool_expression.py`): GPL96/GPL570 probe→symbol maps frozen from GEO annotation (drops: AFFX controls, empty/`---` symbols, `///` multi-mappers); per cohort, one probe per symbol by highest mean across that cohort's analysis samples (mean is a selector, not a transform — source values copied unchanged); HiSeqV2 rows are already symbols; final matrix = 3-family symbol intersection × 751 label samples.

## 5. Decisions a future agent must not silently undo

1. **Cohort-available covariates, no imputation.** Age exists only for TCGA (302) and GSE30161 (47). Stage/grade/residual vocabularies are **not harmonized** across cohorts (`Optimal`/`Sub-optimal` vs `R0/R1/R2` vs `0/1` vs `1-10 mm`) — recode at modelling time. Full completeness table: `docs/os-training-labels.md` §"Counts actually obtained".
2. **Multi-mapping probes dropped, not resolved.** Cost: some classic genes are absent from the Affy side (e.g. `DDR1`, `MIR4640` via `1007_s_at → MIR4640///DDR1`). This is deliberate: reproducibility over probe count.
3. **No batch correction.** `expression_pool.csv` is model-ready in *shape*, not in *scale* — Xena log2-ish RNA-seq and Affy MAS5-style values sit side by side. Harmonization (ComBat / cohort intercepts / rank-based) is an M4 modelling decision.
4. **Event-definition heterogeneity disclosed, not fixed.** GSE26712 + GSE63885 deaths are DOD (disease-specific-flavored); the rest are all-cause. Use the `event_definition` column; consider sensitivity analyses.
5. **Validation set is compiled and held out.** GSE32062/GSE53963/GSE17260/GSE140082/GSE49997 live in `os-validation/` (892/410, same 11,474 symbols) and must not leak into training. How: `docs/os-validation-dataset.md`. GSE9891 remains blocked (no survival on disk).
6. **`verify` is the contract.** Re-running either script must reproduce 751/485 and 11,474 × 751. Deviations mean the inputs changed — investigate before proceeding.

## 6. Pointers

- Labels detail (schema, per-cohort rules, covariate completeness): `docs/os-training-labels.md`
- Expression detail (annotation provenance, drop counts, collapse rationale, per-stage counts): `docs/os-training-expression.md`
- Split rationale + compiled validation roster: `docs/os-train-validation-split.md`, `docs/os-validation-dataset.md`
- Workstream + milestones: `research/os-hgsoc/workstream.md`
- Messy-field traps (source of most rules above): `docs/ovarian-cancer-prognosis-opportunities.md` Appendix B
