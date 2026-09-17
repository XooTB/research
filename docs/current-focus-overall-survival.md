# Current focus: Overall survival from tumor gene expression (HGSOC)

**Status:** active workstream — this is the project's single focus until the milestones below are done.
**Source decision:** `docs/ovarian-cancer-prognosis-opportunities.md` §7.1 (selected 27 Aug 2026).
**Now:** first-pass Colab notebook ready (`notebooks/ovarian-os-first-pass.ipynb`) covering M3 clinical Cox + M4 LASSO-Cox / RSF / DeepSurv on the compiled tables. **Next: the agent runs it on Colab itself** — `colab_sync.py start --dataset os-training-pool --dataset os-validation`, `run notebooks/ovarian-os-first-pass.ipynb`, `stop` (colab-compute skill). Results are not in yet — do not treat this as a completed M3/M4.
**Note from the audit:** §7.3 (PFS/PFI) was rated the higher-value endpoint and §7.1 the "secondary, literature-comparable" one. We are deliberately running OS anyway; treat PFS as the follow-on, not a distraction.

---

## 1. The product, in one paragraph

At diagnosis, given the primary tumor's bulk gene expression plus age, FIGO stage, and residual disease, rank a high-grade serous ovarian cancer patient by hazard of death. Output is a **risk rank / risk group**, not a calibrated personal survival probability. The model must beat a clinical-only baseline by a *replicated* ΔC-index ≥ 0.03 on external cohorts to count as a result.

## 2. Non-negotiables (from the audit)

- **HGSOC / serous, advanced-stage** is the analysis population. Mixed-histotype series get subsetted, not pooled whole.
- Always report the **clinical-only baseline** (residual disease + stage + age where present) next to every model.
- Internal CV is not evidence. Every claim needs an **external cohort, preferably a different platform**, with C-index **and** KM log-rank.
- Expected ceiling: expression-only C-index ~0.58–0.65; clinical-only ~0.60–0.65. Do not promise "accurate" death prediction anywhere in the write-up.
- Exclude the 14 GSE53963 samples that are TCGA duplicates whenever TCGA is in the same analysis.

## 3. Data in hand (OS-labelled)

**Train/validation split is decided** — full reasoning, fitness criteria, and disk-verified numbers in `docs/os-train-validation-split.md`. Principle: pool = RNA-seq + Affymetrix; validation = Agilent/Illumina/ABI (platform families fully disjoint).

**Training pool — compiled** (`datasets/.../os-training-pool/`, 751 patients / 485 deaths, 11,474 symbols). How: `docs/os-training-dataset.md`.

| Cohort | n / deaths | Platform | Source |
|---|---|---|---|
| TCGA-OV HiSeqV2 | 302 / 182 | RNA-seq | `tcga-ov-xena-rna-seq-hiseqv2` + `tcga-ov-xena-clinical-matrix` |
| GSE26712 | 185 / 129 | Affy GPL96 | `gse26712-ovarian-expression-series-matrix` |
| GSE63885 | 70 serous / 62 | Affy GPL570 | `gse63885-ovarian-expression-series-matrix` (CSVs converted) |
| GSE26193 | 79 serous / 60 | Affy GPL570 | `gse26193-ovarian-expression-series-matrix` |
| GSE30161 | 47 serous / 33 | Affy GPL570 (FFPE) | `gse30161-ovarian-expression-series-matrix` (labels reparsed from series matrix) |
| GSE14764 | 68 serous / 19 | Affy GPL96 | `gse14764-ovarian-expression-series-matrix` |

**Held-out validation — compiled** (`datasets/.../os-validation/`, 892 patients / 410 deaths, same 11,474 training symbols). How: `docs/os-validation-dataset.md`.

| Cohort | n / deaths | Platform | Role | Source |
|---|---|---|---|---|
| GSE32062 | 260 / 121 | Agilent GPL6480 | Flagship | `gse32062-gpl6480-ovarian-expression-series-matrix` |
| GSE53963 | **160 / 139** after dropping 14 TCGA dups | Agilent GPL6480 | Second flagship | `gse53963-ovarian-expression-series-matrix` (labels from ch2 series-matrix reparse) |
| GSE17260 | 110 / 46 | Agilent GPL6480 | Within-platform replication | `gse17260-ovarian-expression-series-matrix` |
| GSE140082 | 191 HGSOC III/IV / 56 | Illumina GPL14951 | Secondary, flag immaturity | `gse140082-ovarian-expression-series-matrix` (CSVs converted) |
| GSE49997 | 171 serous / 48 | ABI GPL2986 | Tertiary, supportive only | `gse49997-ovarian-expression-series-matrix` |
| GSE9891 | 285 | Affy GPL570 | **Blocked — no survival on disk**; premier validator once attached | `gse9891-ovarian-expression-series-matrix` |

Excluded from both (reasons in split doc §5): GSE51088, GSE13876, GSE18520, GSE19161, GSE8842, GSE51373, GSE131978, GSE14407, GSE154600.

## 4. Acquisitions (not blocking M3)

M2 tables exist; M3 clinical baselines can run on `os-training-pool/` + `os-validation/` as-is. These acquisitions improve later runs, they are not a prerequisite for the first baseline notebook.

- [ ] **GSE9891 survival** via `curatedOvarianData` (Bioconductor) or Tothill supplements — the field's favorite validator is currently dead weight (119 MB of expression, no outcome). Would add a same-platform (Affy) external control, not a substitute for the Agilent flagships.
- [ ] **PanCanAtlas CDR** (`TCGA-CDR-SupplementalTableS1.xlsx`) — standardized TCGA OS/DSS; also unlocks honest PFI later. Easy, public. Current TCGA labels are Xena OS.
- [ ] **TCGA-OV Affymetrix U133A** (Xena) — raises TCGA OS n from 302 to ~550 and puts more of the pool on GPL96. Large file: pack with `agent/scripts/github_pack.py`.
- [x] Phenotype CSVs needed for M2: GSE63885, GSE140082, GSE53963 — converted 27 Aug. GSE53963 converter CSV is ch1-only and unused for labels (ch2 reparse in `os_validation_labels.py`). Remaining unconverted series (GSE51088, GSE8842, GSE13876) are excluded from both sides (split doc §5).

## 5. Modelling plan

1. **Baselines first, on every cohort:** clinical-only Cox (residual + stage + age). Any expression model that can't beat this on external data is a negative result — say so.
2. **Model classes:** LASSO-Cox (existing baseline), random survival forest, one DeepSurv-style net at most. No deep-learning heroics on n=751 train / n=892 val.
3. **Train/validate split by platform (compiled, see §3 and the split doc):** train on `os-training-pool/` (751 / 485), score on `os-validation/` (892 / 410) — **all five validators**, not just the flagship. Expression is already in a shared 11,474-symbol space; values are **not** batch-corrected (platform-native). Empty cells on the validation matrix (~2.8%) are platform-coverage gaps — models must tolerate them or score on each cohort's covered symbols.
4. **Metrics:** external C-index with CI, KM log-rank p for high/low split, ΔC-index vs clinical baseline. Report all three per validator.
5. **Existing numbers to beat** (audit Appendix A): expression LASSO-Cox external C-index 0.560 (GSE26712) / 0.530 (GSE14764); clinical OOF 0.615. 3-year classifier external AUC 0.615 / 0.505.

## 6. Milestones

- [ ] M1: Acquisitions in §4 done; GSE9891 + CDR + U133A on disk and packed
- [x] M2: Unified OS analysis table (sample × covariates × OS) across all cohorts, HGSOC-subsetted, dedupe applied — training pool 751/485 + validation set 892/410, both with expression in the 11,474-symbol space (27 Aug)
- [ ] M3: Clinical baselines on all cohorts (notebook written: `notebooks/ovarian-os-first-pass.ipynb`; **not done until the Colab run is imported**)
- [ ] M4: Expression models trained, cross-platform validation matrix filled (same notebook: LASSO-Cox, RSF, DeepSurv; same caveat)
- [ ] M5: Write-up: internal vs external performance, honest ceiling discussion, comparison to Riester/Waldron-era signatures

## 7. Status log

- **27 Aug 2026** — Workstream opened. Prior state: first LASSO-Cox + 3-year classifier already run (runs `20260824T195053Z`, `20260825T034757Z`); external performance weak (C-index 0.53–0.56). Next action: acquisitions in §4.
- **27 Aug 2026** — Train/validation split decided and disk-verified: `docs/os-train-validation-split.md`. §3 roles updated (pool = TCGA + 5 Affy cohorts, 751 pts / 485 deaths; validation = Agilent trio + GSE140082 + GSE49997, ~410 events). Corrections folded in: TCGA Cox-usable n is 302; GSE53963/GSE140082/GSE63885 still lack phenotype CSVs. Next action unchanged: acquisitions in §4, then pre-pooling checklist (split doc §7).
- **27 Aug 2026** — Training pool compiled: `datasets/ovarian-cancer-prognosis-ml/os-training-pool/` (`labels.csv` 751/485 exact match to split doc; `expression_pool.csv` 11,474 symbols × 751 samples). Tooling: `agent/scripts/os_pool_labels.py`, `agent/scripts/os_pool_expression.py` (both with `verify` subcommands). Docs: `docs/os-training-dataset.md` (+ labels/expression detail docs). GSE63885 CSVs converted; GSE30161 reparsed from raw matrix; GPL96/GPL570 GEO annotations in `platform-annotations/`. Covariate strategy: cohort-available, no imputation. M2 training side done; validation-side conversions + GSE53963 dedupe still open.
- **27 Aug 2026** — Validation set compiled: `datasets/ovarian-cancer-prognosis-ml/os-validation/` (`labels.csv` 892/410 — GSE53963 disk-verified at 160/139 after dropping 14 TCGA duplicates via ch2 `tcga_sampleid`; `expression_validation.csv` 11,474 training symbols × 892 samples, platform coverage 93–99%). Tooling: `agent/scripts/os_validation_labels.py` (ch2 series-matrix reparse for GSE53963; leakage check vs training pool in `verify`), `agent/scripts/os_validation_expression.py`. Docs: `docs/os-validation-dataset.md` (+ detail docs). GSE53963/GSE140082 CSVs converted; GPL6480/GPL14951/GPL2986 annotations in `platform-annotations/`. **M2 done both sides.** Next: M3 clinical baselines on all cohorts.
- **27 Aug 2026** — First-pass modelling notebook: `notebooks/ovarian-os-first-pass.ipynb`. Recoding in `agent/scripts/os_clinical.py` (GOG residual; FIGO 1–4; `verify` covers every source string). Preprocess: within-sample ranks, top 500 train-variance genes, z-score on the pool, validation coverage gaps → mid-rank. Classes: per-cohort clinical Cox + transported residual+stage Cox, LASSO-Cox, RSF, one DeepSurv net. Metrics: bootstrap C-index, KM log-rank, ΔC vs clinical, all five validators. **Not run yet.** Next: commit/push compiled tables + notebook, then Colab Run All.
- **15 Sep 2026** — Colab workflow is now agent-driven through Google's `colab` CLI: `agent/scripts/colab_sync.py` uploads code + datasets from the working tree into a persistent session (incremental; no GitHub clone or push), runs scripts/notebooks, and pulls run records back. `colab_check.py`, the clone bootstrap and `colab_env.push_runs` removed; first-pass notebook bootstrap updated; `agent/experiments/colab_smoke.py` added. Next action unchanged: run the first-pass notebook (now the agent's step).
- **17 Sep 2026** — Workspace bookkeeping. Library DB cleaned: 13 blank dataset rows and the superseded GSE131978 candidate removed, workspace-relative paths, `os-training-pool` / `os-validation` / `platform-annotations` registered, REPORT.md datasets marked verified. The upsert bug that created the blank rows (NULL `source_id` never matched) is fixed, and `datasets_verify.py` now keeps hand-written verdicts. New `agent/scripts/workspace_check.py` checks DB vs disk, packed files, OS verifies, doc numbers, run provenance, and the ledger. Run records now carry provenance (code snapshot commit under `refs/runs/` + dataset sha256). External scoring goes through `.research/validation-ledger.jsonl` (`colab_env.register_validation`); the first-pass notebook registers candidate `os-first-pass-v1` before touching validation outcomes. Next action unchanged: run the first-pass notebook.

## 8. Pointers

- **Train/validation split (roles, criteria, disk verification, M2 checklist):** `docs/os-train-validation-split.md`
- **Compiled training pool:** `docs/os-training-dataset.md` → `docs/os-training-labels.md`, `docs/os-training-expression.md`; scripts `agent/scripts/os_pool_labels.py`, `agent/scripts/os_pool_expression.py`
- **Compiled validation set (start here for M3/M4 scoring):** `docs/os-validation-dataset.md` → `docs/os-validation-labels.md`, `docs/os-validation-expression.md`; scripts `agent/scripts/os_validation_labels.py`, `agent/scripts/os_validation_expression.py`
- Opportunity analysis: `docs/ovarian-cancer-prognosis-opportunities.md` §7.1, data audit §5–6, gotchas Appendix B
- First-pass M3+M4 notebook: `notebooks/ovarian-os-first-pass.ipynb`; recoding `agent/scripts/os_clinical.py`
- Existing notebooks: `notebooks/ovarian-os-lasso-cox.ipynb`, `notebooks/ovarian-3yr-mortality-classifier.ipynb`
- Run records: `.research/colab/runs/`
- Colab workflow: `.cursor/skills/colab-compute/SKILL.md` (agent-driven `colab_sync.py start` → `run` → `stop`; no push needed)
