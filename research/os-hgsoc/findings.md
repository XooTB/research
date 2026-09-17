# Findings

Append-only. Add with `research.py new finding`; replace with a new entry that `supersedes:` the old one.

## F001 · 2026-08-25 · TCGA-trained LASSO-Cox transfers poorly to Affymetrix cohorts
refs: E001, run:20260824T195053Z-tcga-ov-lasso-cox, gse26712, gse14764
tags: transfer, lasso-cox
External C-index 0.560 (GSE26712, log-rank p 0.68) and 0.530 (GSE14764, p 0.88), against a TCGA
clinical CV C-index of 0.615. The internal expression CV C-index (0.605) did not predict transfer.

## F002 · 2026-08-25 · Internal AUC gains of the 3-year classifier vanish externally
refs: E002, run:20260825T034757Z-tcga-ov-3yr-mortality-clf, gse26712, gse14764
tags: transfer, classifier
Expr+clin ENET CV AUC 0.695 vs clinical LR 0.646 on TCGA, but external AUC 0.615 (GSE26712)
and 0.505 (GSE14764).

## F003 · 2026-08-27 · GSE14764 is too small to decide anything as a validator
refs: docs/os-train-validation-split.md, gse14764
tags: cohort-quality
68 serous / 19 deaths; coin-flip results in E001/E002 (0.53 C, 0.505 AUC). Pooled into training
instead, where its events still count.

## F004 · 2026-08-27 · TCGA Cox-usable n is 302, not 303
refs: T001, tcga-ov-xena-clinical-matrix, docs/os-training-labels.md
tags: tcga-ov, labels
TCGA-04-1357-01 has a vital status but no survival time.

## F005 · 2026-08-27 · GSE53963 contains 14 TCGA duplicates; its ch1 phenotype CSV is unusable
refs: T001, gse53963, docs/os-validation-labels.md
tags: leakage, gse53963, labels
14 TCGA barcodes (all deaths) dropped → 160 patients / 139 deaths. Survival lives in channel 2 of
the series matrix; labels come from a ch2 reparse in os_validation_labels.py.

## F006 · 2026-08-27 · GSE9891 has no survival data on disk
refs: T002, gse9891
tags: gse9891, blocked
The field's usual validator is dead weight until outcomes are attached from curatedOvarianData
or the Tothill supplements.

## F007 · 2026-08-27 · Event definitions are heterogeneous across cohorts
refs: docs/os-train-validation-split.md, gse26712, gse13876
tags: endpoint, labels
GSE26712 `status` = DOD (disease-specific flavour) is kept in the pool with disclosure; GSE13876
is DSS-like and excluded from all-cause OS.

## F008 · 2026-08-27 · Two validators have immature follow-up
refs: docs/os-train-validation-split.md, gse140082, gse49997
tags: follow-up, validation
GSE140082 max OS ~3.6 years; GSE49997 max 49 months. Treat as secondary/supportive, not
deciding, cohorts.

## F009 · 2026-09-18 · Expression adds replicated prognostic value over clinical only when combined with it; gene-only models do not transfer
refs: E003, run:20260917T180930Z-os-first-pass, gse32062, gse17260, gse53963, gse140082, gse49997
tags: transfer, primary-result, expr-clin
E003, candidate os-first-pass-v1, scored once. expr_clin_cox (LASSO score + residual + stage) beat the transported residual+stage Cox by ΔC ≥ 0.03 on 3/5 validators: GSE17260 +0.091 [0.024, 0.149], GSE32062 +0.047 [0.021, 0.071], GSE49997 +0.044 [-0.022, 0.108]; GSE140082 +0.020, GSE53963 +0.004. Pooled (DL random effects) +0.036 [0.010, 0.061], I2=0.41. Absolute external C 0.62-0.69 vs clinical 0.58-0.62. The gene-only models were all at or below the clinical baseline pooled: lasso_cox -0.010, deepsurv -0.011, rsf -0.041 [-0.080, -0.003], i.e. RSF was worse than clinical everywhere. The LASSO score's HR per SD adjusted for residual + stage was above 1 in all five (1.13-1.52), LR p < 0.05 in 4/5 (GSE49997 p=0.094). So the expression signal is real but small, and only visible when clinical factors carry the baseline ranking.

## F010 · 2026-09-18 · Two of the three validators that passed are Yoshihara GPL6480 series that may share patients
refs: E003, gse32062, gse17260, docs/os-train-validation-split.md, docs/os-validation-labels.md
tags: validation, independence, leakage-risk
GSE32062 (Yoshihara 2012, 260), GSE17260 (Yoshihara 2010, 110) and GSE53963 (Yoshihara) are all from the same group on GPL6480. The leakage checks so far (docs/os-validation-labels.md, verify) only tested sample_id collisions with the TRAINING pool; GSM ids differ between series even for a re-hybridised patient, so they cannot rule out patient overlap between GSE17260 and GSE32062. E003's verdict rests on those two plus GSE49997 (short follow-up, F008, CI crosses 0). If GSE17260 is a subset of GSE32062, the replication is effectively one cohort plus one immature one. Must be checked (T006) before the result is presented as replicated.
