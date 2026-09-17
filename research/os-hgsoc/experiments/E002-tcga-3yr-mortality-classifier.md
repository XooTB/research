+++
id = "E002"
title = "TCGA 3-year mortality classifier (binary), tested on Affymetrix cohorts"
status = "done"
priority = 1
depends_on = []
summary = "Binary 3-year death classifiers (clinical LR, expression ENET, expr+clin ENET/HGB) on TCGA; best model scored on GSE26712/GSE14764."
hypothesis = "A binary 3-year framing with expression + clinical features transfers better than a Cox signature."
runs = ["20260825T034757Z-tcga-ov-3yr-mortality-clf"]
tags = ["classifier", "transfer", "tcga-ov", "gse26712", "gse14764"]
criterion = "none"
outcome = "CV AUC 0.695 (expr+clin ENET) vs clinical 0.646 on TCGA, but external AUC 0.615 (GSE26712) / 0.505 (GSE14764)."
created = "2026-08-25"
updated = "2026-08-25"
verdict = "n/a"
verdict_basis = "no success rule (criterion = \"none\")"
criterion_hash = "30a0924a3360"
+++
## Plan
Pre-workstream exploration. 223 evaluable TCGA patients (80 censored before 3 years dropped),
prevalence 0.43. Notebook `notebooks/ovarian-3yr-mortality-classifier.ipynb` was removed in the
17 Sep reorganization (D008); recover with `git show 6275d06:notebooks/ovarian-3yr-mortality-classifier.ipynb`.

## Notes
Dropping early-censored patients discards 26% of the cohort; a survival framing keeps them.

## Interpretation
Same transfer failure as E001 (F002); internal CV gains do not survive a platform change.
