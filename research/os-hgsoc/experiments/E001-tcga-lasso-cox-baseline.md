+++
id = "E001"
title = "TCGA-only LASSO-Cox OS signature, tested on Affymetrix cohorts"
status = "done"
priority = 1
depends_on = []
summary = "Train LASSO-Cox on TCGA-OV HiSeqV2 (500 top-variance genes), score GSE26712 and GSE14764."
hypothesis = "A TCGA-trained expression signature transfers to independent Affymetrix cohorts."
runs = ["20260824T195053Z-tcga-ov-lasso-cox"]
tags = ["lasso-cox", "transfer", "tcga-ov", "gse26712", "gse14764"]
criterion = "none"
outcome = "Transfers poorly: external C 0.560 (GSE26712) / 0.530 (GSE14764), log-rank n.s.; TCGA CV C 0.605 vs clinical 0.615."
created = "2026-08-24"
updated = "2026-08-25"
verdict = "n/a"
verdict_basis = "no success rule (criterion = \"none\")"
criterion_hash = "30a0924a3360"
+++
## Plan
Pre-workstream exploration (before the success rule existed, hence `criterion = "none"`).
LASSO-Cox on TCGA-OV Xena HiSeqV2 OS (303 primary tumours, 182 events), penalizer 0.05, top 500
variance genes (178-gene signature), then applied to GSE26712 and GSE14764 series matrices.
Notebook `notebooks/ovarian-os-lasso-cox.ipynb` was removed in the 17 Sep reorganization (D008);
recover it with `git show 6275d06:notebooks/ovarian-os-lasso-cox.ipynb`.

## Notes
Signature genes overlapped only 124/178 on the Affy platforms.

## Interpretation
Single-cohort training does not transfer (F001). This motivated pooling across platforms and a
platform-disjoint validation design (D003) instead of TCGA-only models.
