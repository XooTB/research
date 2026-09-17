+++
id = "T006"
title = "Check patient overlap between GSE17260 and GSE32062 (and GSE53963)"
status = "done"
priority = 1
depends_on = ["E003"]
summary = "Cross-correlate GPL6480 expression profiles between the three Yoshihara validators; duplicates show near-1 correlation. Decide whether E003's replication is on independent patients."
tags = ["validation", "independence", "leakage-risk"]
created = "2026-09-18"
updated = "2026-09-18"
outcome = "Confirmed: 26/110 GSE17260 patients match GSE32062 on all 7 clinical fields (p=0.005), 21/28 are each other's best expression match, union of criteria 41/110 (37%). GSE53963 independent. Not train/test leakage; GSE17260 is a redundant replication (F012, D010)."
+++
## Plan
On Colab: load os-validation expression, restrict to the three GPL6480 cohorts, compute the cross-cohort Spearman/Pearson correlation matrix between samples (11,474 symbols, or the top-variance subset), flag pairs > 0.95 and compare their clinical fields (age, stage, residual, OS time/event) for identity. Report n overlapping pairs per cohort pair. If GSE17260 overlaps GSE32062, record a finding and re-state E003's replication count in its Interpretation (do NOT re-score: the ledger entry stands; this changes how many independent cohorts the existing numbers represent).

## Notes
