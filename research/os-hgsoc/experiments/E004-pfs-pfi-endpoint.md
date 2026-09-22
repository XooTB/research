+++
id = "E004"
title = "PFS/PFI endpoint follow-on"
status = "done"
priority = 1
depends_on = ["E003", "T003"]
summary = "Repeat the platform-disjoint design for progression-free survival / PFI once OS first pass is in and CDR labels exist."
hypothesis = "Expression adds more to clinical factors for progression than for death: expr_clin_pfs_cox clears ΔC ≥ 0.03 on ≥ 2 of the three independent validators AND the pooled ΔC CI excludes zero."
runs = ["20260921T163118Z-e004-pfs-tune", "20260921T163220Z-e004-pfs-tune", "20260921T163531Z-e004-pfs-first-pass"]
tags = ["pfs", "pfi", "endpoint"]
created = "2026-09-17"
updated = "2026-09-21"

validation_candidate = "pfs-first-pass-v1"
criterion_hash = "a0a5ec89a2e3"
outcome = "Not supported: no validator cleared ΔC ≥ 0.03 (GSE32062 +0.020, GSE140082 +0.018, GSE49997 −0.051); pooled +0.001 [−0.034, +0.037], I²=0.73. Expression score still carries pool signal (HR 1.175/SD, p=0.008), but progression transfers worse than death (F014)."
verdict = "not-supported"
verdict_basis = "need 1 cohorts >= 1.0: expr_clin_pfs_cox: 0/1"
[criterion]
metric = "e004_success_indicator"
split = "external"
op = ">="
threshold = 1.0
min_cohorts = 1
models = ["expr_clin_pfs_cox"]
+++
## Plan

### Data (audited 2026-09-21, before any modelling)
Progression fields exist for fewer cohorts than OS, but with far more events (61-75% vs ~55%).

**Pool** (labels built by `agent/scripts/pfs_labels.py` into `pfs-training-pool/`): TCGA-OV
(302, CDR `PFI`/`PFI.time`, 209 events), GSE26193 (79, pfs years), GSE63885 (70, DFS days),
GSE30161 (47, relapse dates - excluded if censoring times cannot be derived). GSE26712 and
GSE14764 carry no progression fields and drop out.

**Validation** (`pfs-validation/`): GSE32062 (260, 74% events), GSE140082 (191), GSE49997 (171).
GSE53963 has no progression fields and drops out. GSE17260 is scored but stays redundant with
GSE32062 (D010) and is excluded from the rule, exactly as in E003.

So there are **three** independent validators. Two of them, GSE140082 and GSE49997, were weak for
OS because their follow-up is immature (F008); that objection largely disappears here, because
progression happens early.

Expression is reused unchanged from the OS tables (same samples, same 11,474-symbol space),
subset by `sample_id`. No new expression matrices.

### Endpoint definition
Each cohort keeps its **native** definition, recorded per patient in `event_definition`
(user decision, 2026-09-21). TCGA's CDR PFI counts death without progression as an event; the
GEO recurrence flags generally do not; GSE63885 is disease-free survival. This is the same
choice E003 made for OS (F007) and the heterogeneity belongs in the limitations, not in a
silent harmonisation. Rejected: approximating a recurrence-only TCGA endpoint (the CDR table
does not record the reason for the event, so it can only be guessed, and it discards real events).

### Model
Identical in shape to E003 so the two endpoints are comparable:
- Primary `expr_clin_pfs_cox`: stage 1 a Coxnet expression score, stage 2 a Cox on
  residual + stage + that score, fit on pool complete cases, stratified by cohort.
- Baseline `clinical_transported`: the same Cox on residual + stage alone.
- Secondary, reported not judged: gene-only Coxnet, RSF, DeepSurv.
- Tuning happens on **training-pool CV only**: gene count (250/500/1000), the Coxnet alpha
  path, and l1_ratio (1.0 vs 0.5). Validators are scored once, candidate `pfs-first-pass-v1`.

### Success rule (pre-registered 2026-09-21, before any label table was finished)
Both conditions must hold, on the three independent validators (GSE17260 excluded):
1. `delta_c_vs_clinical_transported >= 0.03` for `expr_clin_pfs_cox` on **at least 2** of them, and
2. the DerSimonian-Laird **pooled** delta-C across them has a 95% CI whose lower bound is **> 0**.

The tracker holds one condition per criterion table, so the run computes the conjunction as a
single row and the criterion is set on it:

    e004_success_indicator = 1 if (cohorts_passing >= 2 and pooled_ci_lo > 0) else 0

Its inputs are saved as ordinary rows too (`delta_c_vs_clinical_transported` per cohort,
`delta_c_vs_clinical_transported_pooled` with `ci_lo`/`ci_hi` on cohort `pfs-validation`), so the
indicator can be checked by hand from `research.py results --experiment E004`. This is stricter
than E003's rule: E003 met condition 1 and, on its independent cohorts, would also have met
condition 2 (+0.030 [0.007, 0.052]) - but only just.

## Notes
The audit (`docs/ovarian-cancer-prognosis-opportunities.md` §7.3) rated this the higher-value
endpoint; deliberately second (D001).

## Interpretation
Run `20260921T163531Z-e004-pfs-first-pass`, candidate `pfs-first-pass-v1`, scored once.
Verdict **not-supported**: 0 of 3 independent validators cleared ΔC ≥ 0.03 and the pooled
estimate straddles zero (+0.001 [−0.034, +0.037], I² = 0.73).

| Validator | n / events | Clinical C | Combined C | ΔC |
|---|---|---|---|---|
| GSE32062 | 260 / 193 | 0.594 | 0.614 | +0.020 |
| GSE140082 | 191 / 135 | 0.582 | 0.600 | +0.018 |
| GSE49997 | 171 / 108 | 0.611 | 0.560 | −0.051 |
| GSE17260 (redundant, D010) | 110 / 76 | 0.638 | 0.629 | −0.009 |

Read carefully, this is a null rather than a refutation:

- The expression score is not noise. On the pool it kept an adjusted HR of 1.175 per SD
  (p = 0.008) and the combined model beat clinical in two of three validators — just not by
  the pre-registered margin.
- What changed versus E003 is **consistency**, not average size: I² went from 0.27 to 0.73
  because GSE49997 reversed. One cohort of 171 decides the pooled result, which is exactly the
  fragility a 3-cohort design carries.
- The endpoint itself looks noisier. Residual disease, the strongest clinical predictor of
  death, barely predicts progression (p = 0.23 on the pool vs p = 0.004 for OS), and the
  progression definitions are heterogeneous across cohorts (F013): RECIST progression in a
  trial cohort, source-coded recurrence in the GEO series, death-with-tumour in TCGA's PFI,
  and a status-derived flag in GSE63885. Progression also depends on imaging and follow-up
  schedules, not tumour biology alone.
- Gene-only pool CV was weaker than for OS (0.552 vs 0.580) despite a higher event fraction
  (356/472 = 75%), so the loss is not a power problem.

**Consequence for the workstream.** D001 rated PFS/PFI the higher-value endpoint; that
expectation is now contradicted by data (F014). The positive result stays confined to overall
survival, and the OS write-up (T005) should report this negative PFS replication beside it —
it is evidence about the scope of the claim, not a failure to hide.

**What would change the answer**, none of which is a re-score of this candidate: more
independent PFS cohorts (the rule rests on three); a harmonised recurrence-only endpoint, which
needs source data the CDR table does not carry; or restricting to trial cohorts with protocol
imaging, where progression is measured consistently.
