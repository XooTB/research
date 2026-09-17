+++
id = "T001"
title = "Compile the OS training pool and validation set"
status = "done"
priority = 1
depends_on = []
summary = "Unified sample × covariates × OS tables, HGSOC-subsetted, TCGA dedupe, expression in a shared symbol space."
tags = ["tcga-ov", "gse53963", "os-training-pool", "os-validation"]
outcome = "Pool 751 patients / 485 deaths, validation 892 / 410, 11,474 symbols; all verify commands pass."
created = "2026-08-27"
updated = "2026-08-27"
+++
## Plan
Labels and expression for both sides, platform annotations, GSE53963 ch2 reparse, leakage check.
Tooling: `agent/scripts/os_pool_labels.py`, `os_pool_expression.py`, `os_validation_labels.py`,
`os_validation_expression.py` (each has `verify`). Docs: `docs/os-training-dataset.md`,
`docs/os-validation-dataset.md`.

## Notes
Findings from this work: F003, F004, F005, F006, F007, F008.
