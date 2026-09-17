+++
id = "E003"
title = "First pass: clinical Cox baselines + expression+clinical Cox (primary) + LASSO-Cox / RSF / DeepSurv on the platform-disjoint split"
status = "done"
priority = 1
depends_on = ["T001"]
summary = "Train on the 751/485 pool, score all five validators once; primary expr_clin_cox vs transported clinical (D009); gene-only models secondary."
hypothesis = "The expression + clinical model (expr_clin_cox) beats the transported residual+stage Cox by ΔC ≥ 0.03 on ≥ 2 external cohorts."
runs = ["20260917T180930Z-os-first-pass"]
tags = ["lasso-cox", "rsf", "deepsurv", "clinical-cox", "gse32062", "gse53963", "gse17260", "gse140082", "gse49997"]
validation_candidate = "os-first-pass-v1"
created = "2026-08-27"
updated = "2026-09-18"

criterion_hash = "08dd934a4a64"
outcome = "Verdict supported: expr_clin_cox beat transported clinical by ΔC ≥ 0.03 on 3/5 validators (GSE17260 +0.091, GSE32062 +0.047, GSE49997 +0.044; pooled +0.036 [0.010, 0.061]). Gene-only models did not beat clinical (pooled ≤ 0). Caveat F010: two passing cohorts may share patients (T006)."
verdict = "supported"
verdict_basis = "need 2 cohorts >= 0.03: expr_clin_cox: 3/5 (gse17260,gse32062,gse49997)"
[criterion]
metric = "delta_c_vs_clinical_transported"
split = "external"
op = ">="
threshold = 0.03
min_cohorts = 2
models = ["expr_clin_cox"]
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
  residual+stage Cox fit on the pool (stratified by training cohort) and applied to each validator.
- **Primary (D009):** `expr_clin_cox`, two-stage: LASSO-Cox expression score (OOF on pool,
  z-scored) + residual + stage, Cox fit on the pool's residual+stage complete cases, stratified by
  cohort. Same covariates and strata as the transported clinical model, plus the score.
- Secondary (reported, not judged): LASSO-Cox (penalizer by pool CV), RSF (200 trees),
  DeepSurv (500→32→1, 80 epochs), all gene-only.
- Registers validation candidate `os-first-pass-v1` before touching validation outcomes. A run
  not linked to E003 is a dry run (synthetic validation outcomes, no registration, nothing saved).
- Saves metric rows: `cindex` (+CI, n), `logrank_p`, `delta_c_vs_clinical_transported` (+paired
  bootstrap CI), `delta_c_vs_clinical_oof` per model × validator; pooled ΔC
  (`delta_c_vs_clinical_transported_pooled`, cohort `os-validation`); expression score HR/SD
  adjusted for residual + stage and LR p per validator; pool OOF C for clinical vs combined.
- Verdict: `delta_c_vs_clinical_transported >= 0.03` on ≥ 2 validators for `expr_clin_cox` only
  (E003's own criterion = D006 restricted to the primary model).

## Notes

## Interpretation
Run `20260917T180930Z-os-first-pass`, candidate `os-first-pass-v1` (scored once). Verdict
**supported**: `expr_clin_cox` cleared ΔC ≥ 0.03 vs the transported residual+stage Cox on
GSE17260 (+0.091 [0.024, 0.149]), GSE32062 (+0.047 [0.021, 0.071]) and GSE49997
(+0.044 [-0.022, 0.108]); GSE140082 +0.020 and GSE53963 +0.004 did not. Pooled ΔC
+0.036 [0.010, 0.061], I² = 0.41.

What it means, with the caveats that belong next to it:

- The gain needs the clinical model. Gene-only LASSO/RSF/DeepSurv were at or below the
  clinical baseline pooled (-0.010 / -0.041 / -0.011); RSF was worse than clinical on every
  validator. This repeats F001/F002 and confirms expression is a weak adjunct, not a
  replacement (F009).
- The expression score is consistent in direction: HR per SD adjusted for residual + stage
  1.13–1.52 on all five validators, LR p < 0.05 on four.
- **Independence is unverified.** Two of the three passing cohorts (GSE32062, GSE17260) are
  Yoshihara GPL6480 series that may share patients (F010); GSE49997's CI crosses 0 and its
  follow-up is immature (F008). T006 must settle the overlap before this is called a
  replicated result.
- The effect sizes sit inside the workstream's expected ceiling (external C 0.62–0.69 for the
  combined model vs 0.58–0.62 clinical). Nothing here supports "accurate" prediction of death.
- Internal pool CV (cohort-stratified OOF) was 0.525 clinical vs 0.539 combined on the 445
  residual+stage complete cases — lower than the external numbers, because the pool mixes
  platforms and eras. Internal CV again proved a poor guide (F002).
