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
