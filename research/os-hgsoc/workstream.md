+++
id = "os-hgsoc"
title = "Overall survival from tumour gene expression (HGSOC)"
status = "active"
summary = "Rank high-grade serous ovarian cancer patients by hazard of death from primary-tumour expression + age, FIGO stage, residual disease; must beat a clinical-only baseline on external cohorts."
question = "Does bulk tumour expression add replicated, cross-platform prognostic value for OS over residual disease + stage + age?"
created = "2026-08-27"
updated = "2026-09-17"

# Pre-registered success rule (D006). An experiment inherits it unless it declares its own
# [criterion] or criterion = "none". Verdicts are computed from metric rows, never judged.
[criterion]
metric = "delta_c_vs_clinical_transported"
split = "external"
op = ">="
threshold = 0.03
min_cohorts = 2

[[milestones]]
id = "M1"
title = "Acquisitions: GSE9891 survival, PanCanAtlas CDR, TCGA U133A on disk and packed"
items = ["T002", "T003", "T004"]

[[milestones]]
id = "M2"
title = "Unified OS tables: training pool 751/485 + validation 892/410 in the 11,474-symbol space"
items = ["T001"]

[[milestones]]
id = "M3"
title = "Clinical baselines on all cohorts"
items = ["E003"]

[[milestones]]
id = "M4"
title = "Expression models trained; cross-platform validation matrix filled"
items = ["E003"]

[[milestones]]
id = "M5"
title = "Write-up: internal vs external, honest ceiling, comparison to Riester/Waldron-era signatures"
items = ["T005"]
+++
# Overall survival from tumour gene expression (HGSOC)

Stable reference for this workstream: the product, the rules, the data. What is happening
now, what's next, what was tried and what it showed live in the tracker. Query it
(`research.py next`, `list`, `show`, `results`) or read `research/NOW.md`.

**Source decision:** `docs/ovarian-cancer-prognosis-opportunities.md` §7.1 (selected 27 Aug 2026).
The audit rated PFS/PFI (§7.3) the higher-value endpoint; OS is pursued first on purpose and
PFS is the follow-on (D001, E004).

## Product

At diagnosis, given the primary tumour's bulk gene expression plus age, FIGO stage, and residual
disease, rank a high-grade serous ovarian cancer patient by hazard of death. Output is a **risk
rank / risk group**, not a calibrated personal survival probability. The model must beat a
clinical-only baseline by a *replicated* ΔC-index ≥ 0.03 on external cohorts to count as a result
(the success rule above).

## Non-negotiables

- **HGSOC / serous, advanced-stage** is the analysis population. Mixed-histotype series get subsetted, not pooled whole.
- Always report the **clinical-only baseline** (residual disease + stage + age where present) next to every model.
- Internal CV is not evidence. Every claim needs an **external cohort, preferably a different platform**, with C-index **and** KM log-rank.
- Expected ceiling: expression-only C-index ~0.58–0.65; clinical-only ~0.60–0.65. Do not promise "accurate" death prediction anywhere in the write-up.
- Exclude the 14 GSE53963 samples that are TCGA duplicates whenever TCGA is in the same analysis.
- External validation cohorts are scored once per frozen candidate (`colab_env.register_validation`); tune on training-pool CV only.

## Data in hand (OS-labelled)

Train/validation split is decided (D003). Full reasoning, fitness criteria and disk-verified
numbers: `docs/os-train-validation-split.md`. Principle: pool = RNA-seq + Affymetrix; validation =
Agilent/Illumina/ABI (platform families fully disjoint).

**Training pool** (`datasets/ovarian-cancer-prognosis-ml/os-training-pool/`, 751 patients / 485 deaths, 11,474 symbols). How: `docs/os-training-dataset.md`.

| Cohort | n / deaths | Platform | Source |
|---|---|---|---|
| TCGA-OV HiSeqV2 | 302 / 182 | RNA-seq | `tcga-ov-xena-rna-seq-hiseqv2` + `tcga-ov-xena-clinical-matrix` |
| GSE26712 | 185 / 129 | Affy GPL96 | `gse26712-ovarian-expression-series-matrix` |
| GSE63885 | 70 serous / 62 | Affy GPL570 | `gse63885-ovarian-expression-series-matrix` |
| GSE26193 | 79 serous / 60 | Affy GPL570 | `gse26193-ovarian-expression-series-matrix` |
| GSE30161 | 47 serous / 33 | Affy GPL570 (FFPE) | `gse30161-ovarian-expression-series-matrix` |
| GSE14764 | 68 serous / 19 | Affy GPL96 | `gse14764-ovarian-expression-series-matrix` |

**Held-out validation** (`datasets/ovarian-cancer-prognosis-ml/os-validation/`, 892 patients / 410 deaths, same 11,474 symbols). How: `docs/os-validation-dataset.md`.

| Cohort | n / deaths | Platform | Role |
|---|---|---|---|
| GSE32062 | 260 / 121 | Agilent GPL6480 | Flagship |
| GSE53963 | 160 / 139 (14 TCGA dups dropped, F005) | Agilent GPL6480 | Second flagship |
| GSE17260 | 110 / 46 | Agilent GPL6480 | Within-platform replication |
| GSE140082 | 191 HGSOC III/IV / 56 | Illumina GPL14951 | Secondary, immature follow-up (F008) |
| GSE49997 | 171 serous / 48 | ABI GPL2986 | Tertiary, supportive only (F008) |
| GSE9891 | 285 | Affy GPL570 | Blocked: no survival on disk (F006, T002) |

Excluded from both (D004): GSE51088, GSE13876, GSE18520, GSE19161, GSE8842, GSE51373, GSE131978, GSE14407, GSE154600.

## Modelling protocol

1. **Baselines first, on every cohort:** clinical-only Cox (residual + stage + age). An expression model that can't beat it on external data is a negative result; say so.
2. **Model classes:** LASSO-Cox, random survival forest, one DeepSurv-style net at most. No deep-learning heroics on n=751 train / n=892 val.
3. **Train on `os-training-pool/`, score on `os-validation/`, all five validators.** Expression is in a shared 11,474-symbol space, platform-native (not batch-corrected; D005). Validation empty cells (~2.8%) are platform-coverage gaps; models must tolerate them.
4. **Metrics per validator:** external C-index with CI, KM log-rank p (median split), ΔC vs clinical. Save them as metric rows (`colab_env.metric_row`) so verdicts can be computed.
5. **Numbers to beat** (pre-workstream runs, F001/F002): expression LASSO-Cox external C 0.560 (GSE26712) / 0.530 (GSE14764); TCGA clinical CV C 0.615; 3-year classifier external AUC 0.615 / 0.505.

## Pointers

- Split: `docs/os-train-validation-split.md`
- Training pool: `docs/os-training-dataset.md` → `docs/os-training-labels.md`, `docs/os-training-expression.md`; `agent/scripts/os_pool_labels.py`, `agent/scripts/os_pool_expression.py`
- Validation set: `docs/os-validation-dataset.md` → `docs/os-validation-labels.md`, `docs/os-validation-expression.md`; `agent/scripts/os_validation_labels.py`, `agent/scripts/os_validation_expression.py`
- Opportunity analysis: `docs/ovarian-cancer-prognosis-opportunities.md` §7.1, data audit §5–6, gotchas Appendix B
- Clinical recoding: `agent/scripts/os_clinical.py`
- Colab workflow: `.cursor/skills/colab-compute/SKILL.md`
