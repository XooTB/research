# Decisions

Append-only. Add with `research.py new decision`; reverse one with a new entry that `supersedes:` it.

## D001 · 2026-08-27 · Pursue overall survival first; PFS/PFI is the follow-on
refs: docs/ovarian-cancer-prognosis-opportunities.md, E004
tags: scope, endpoint
The audit rated PFS/PFI (§7.3) higher-value and OS (§7.1) secondary but literature-comparable. OS
first on purpose, for comparability with published signatures; PFS is not a distraction but E004.

## D002 · 2026-08-27 · Analysis population is HGSOC / serous, advanced stage
refs: docs/os-train-validation-split.md
tags: population
Mixed-histotype series are subsetted, not pooled whole. TCGA duplicates are dropped whenever TCGA
is in the same analysis.

## D003 · 2026-08-27 · Split by platform family, not at random
refs: docs/os-train-validation-split.md, T001, os-training-pool, os-validation
tags: split, validation
Train on RNA-seq + Affymetrix (751 / 485), validate on Agilent / Illumina / ABI (892 / 410), with
platform families fully disjoint. Rejected: random or single-cohort splits, which give no
cross-platform evidence (see F001, F002).

## D004 · 2026-08-27 · Exclude nine series from both sides
refs: docs/os-train-validation-split.md
tags: cohorts
GSE51088, GSE13876, GSE18520, GSE19161, GSE8842, GSE51373, GSE131978, GSE14407, GSE154600: DSS
endpoint, unverifiable coding, too few probes, stage I only, or no OS labels (split doc §5).

## D005 · 2026-08-27 · No batch correction; rank-transform instead; no clinical imputation
refs: E003, agent/scripts/os_clinical.py
tags: preprocessing
Within-sample percentile ranks put RNA-seq and microarray on one scale; top 500 genes by training
variance, z-scored on the pool; validation coverage gaps set to mid-rank. Clinical covariates are
used where each cohort has them, never imputed.

## D006 · 2026-09-17 · Success rule: ΔC vs transported clinical Cox ≥ 0.03 on ≥ 2 external cohorts
refs: E003, research/os-hgsoc/workstream.md
tags: success-rule, validation
Pre-registered before any first-pass result. Baseline is the residual+stage Cox fit on the pool and
transported to each validator (same train→score protocol as the expression models). The per-cohort
CV clinical Cox is still reported (`delta_c_vs_clinical_oof`) but does not decide: it is fit on the
target cohort itself, so it is not a like-for-like comparison. "Replicated" = the same model on ≥ 2
validators; the latest run per model × cohort counts.

## D007 · 2026-09-17 · Track research in markdown + TOML with a computed index (research.py)
refs: agent/scripts/research.py
tags: tooling
Chosen after hands-on trials of Beads, Backlog.md, MLflow and DVC on this workstream's questions:
none covered both planning and queryable results with computed verdicts; each added a second
system, heavy installs or telemetry, and non-text or collision-prone storage.

## D008 · 2026-09-17 · Remove legacy notebooks and abandoned dataset topics
refs: E001, E002
tags: cleanup
Deleted `notebooks/ovarian-os-lasso-cox.ipynb` and `notebooks/ovarian-3yr-mortality-classifier.ipynb`
(recoverable from commit 6275d06; their run records stay, linked from E001/E002) and 19 candidate
dataset rows from four abandoned topics (adverse drug reactions, antibiotic resistance, chemotherapy
response, drug-drug interactions). From now on nothing is deleted: close items as abandoned instead.

## D009 · 2026-09-17 · E003 primary model is two-stage expression + clinical Cox; verdict on it alone
refs: E003, D006, notebooks/ovarian-os-first-pass.ipynb
tags: success-rule, model, pre-registration
The product is expression + age/stage/residual, but E003 only had gene-only models, which the workstream's expected ceiling (expr-only C 0.58–0.65 vs clinical 0.60–0.65) makes unlikely to clear ΔC ≥ 0.03, and the ledger allows one scoring. Added expr_clin_cox before any E003 result: stage 1 LASSO-Cox expression score (OOF on pool, z-scored), stage 2 Cox on residual + stage + score fit on the pool's residual+stage complete cases (n=445), stratified by training cohort; the transported clinical Cox uses the same covariates and strata, so ΔC isolates expression. E003's criterion is D006's rule restricted to models=[expr_clin_cox]; gene-only LASSO/RSF/DeepSurv are secondary and reported, not judged, to avoid best-of-four multiplicity. Also reported (not in the rule): paired-bootstrap ΔC CIs, DerSimonian-Laird pooled ΔC over validators, per-validator HR/SD of the expression score adjusted for residual + stage with an LR test. Rejected: single-stage Cox with unpenalized clinical + L1 genes (fits on n=445 complete cases only, loses 306 expression-only patients in stage 1); adding age (absent in 4/6 pool cohorts); judging any-of-four models (multiplicity); running gene-only first and a combined candidate later (spends a validation scoring on a comparison that doesn't test the product).
