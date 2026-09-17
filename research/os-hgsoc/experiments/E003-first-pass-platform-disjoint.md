+++
id = "E003"
title = "First pass: clinical Cox baselines + LASSO-Cox / RSF / DeepSurv on the platform-disjoint split"
status = "planned"
priority = 1
depends_on = ["T001"]
summary = "Train on the 751/485 pool, score all five validators once; clinical baselines per cohort + transported; ΔC vs transported clinical."
hypothesis = "At least one expression model beats the transported residual+stage Cox by ΔC ≥ 0.03 on ≥ 2 external cohorts."
runs = []
tags = ["lasso-cox", "rsf", "deepsurv", "clinical-cox", "gse32062", "gse53963", "gse17260", "gse140082", "gse49997"]
validation_candidate = "os-first-pass-v1"
created = "2026-08-27"
updated = "2026-09-17"
+++
## Plan
Run `notebooks/ovarian-os-first-pass.ipynb` on Colab:

```bash
.venv/bin/python agent/scripts/colab_sync.py start --dataset os-training-pool --dataset os-validation
.venv/bin/python agent/scripts/colab_sync.py run --experiment E003 notebooks/ovarian-os-first-pass.ipynb
.venv/bin/python agent/scripts/colab_sync.py stop
```

- Preprocess (D005): within-sample ranks, top 500 train-variance genes, z-score on the pool,
  validation coverage gaps → mid-rank 0.5.
- Clinical: per-cohort Cox (cohort-available residual/stage/age, 5-fold CV) and a transported
  residual+stage Cox fit on the pool and applied to each validator.
- Expression: LASSO-Cox (penalizer by pool CV), RSF (200 trees), DeepSurv (500→32→1, 80 epochs).
- Registers validation candidate `os-first-pass-v1` before touching validation outcomes.
- Saves metric rows: `cindex` (+CI, n), `logrank_p`, `delta_c_vs_clinical_transported`,
  `delta_c_vs_clinical_oof` per model × validator. The verdict is computed from
  `delta_c_vs_clinical_transported` (workstream rule, D006).

## Notes

## Interpretation
<!-- when done: what the computed verdict means; numbers come from `research.py results --experiment E003` -->
