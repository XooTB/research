# Journal

Append-only session handoffs (`research.py log`): what was done, where it stopped, what's next and why.

## 2026-08-27 · workstream opened
Selected OS (§7.1). Prior state: E001 and E002 already run, external performance weak. Train/validation
split decided and disk-verified (D003). Training pool compiled, then validation set (T001, M2 done).
First-pass notebook written (E003), not run.

## 2026-09-15 · Colab via CLI
Colab is now agent-driven through Google's `colab` CLI (`colab_sync.py`): working-tree uploads, no
GitHub clone/push. First-pass notebook bootstrap updated. Next unchanged: run E003.

## 2026-09-17 · workspace bookkeeping + research tracker
Library DB cleaned; `workspace_check.py`; run provenance (code snapshot + dataset hashes); validation
ledger. Then the tracker: focus doc migrated into research/os-hgsoc (workstream, E001–E004,
T001–T005, F001–F008, D001–D008); legacy runs backfilled with metric rows; first-pass notebook now
saves metric rows; legacy notebooks and abandoned dataset topics removed (D008). Success rule
pre-registered (D006). Next: run E003 on Colab with `--experiment E003`, then plan follow-ups from
its verdict (E004 PFS, T002/T003 acquisitions are ready in parallel).

## 2026-09-18 00:11 · E003 first pass: expr+clinical beats clinical on 3/5
Did: added the primary expression+clinical model to E003 before running it (D009: two-stage LASSO score + residual + stage, pool-fit, cohort-stratified; E003 criterion restricted to expr_clin_cox to avoid best-of-four multiplicity); switched LASSO stage 1 from lifelines L1 (did not finish in 1 h on 500 genes) to sksurv Coxnet; added paired-bootstrap ΔC CIs, DL pooled ΔC, adjusted HR/SD + LR test per validator, KM figure saved with the run, and a dry-run mode (a run not linked to E003 uses synthetic validation outcomes and registers nothing). Ran E003 once on Colab T4: verdict supported, 3/5 validators, F009. Filed F010 + T006 on validator independence.
State: E003 done, run 20260917T180930Z-os-first-pass, candidate os-first-pass-v1 in the ledger (spent). Colab session stopped. First Colab session of the night was reclaimed mid-run; nothing was registered then.
Next: T006 first (p1) — if GSE17260 overlaps GSE32062 the replication is one cohort, not three, and that changes what can be claimed; then T003 (CDR labels) which also unblocks E004 PFS; T002/T004 in parallel. T005 write-up only after T006.
Watch: gene-only models are at or below the clinical baseline (RSF worse everywhere) — the claim is expression as an adjunct. GSE53963, the second flagship, showed nothing (+0.004) while its clinical baseline is the strongest (0.624); GSE49997's CI crosses 0. Pooled I2=0.41.

## 2026-09-18 01:14 · T006 independence + T003 CDR labels
Did: closed T006 (GSE17260 shares 26-41 of 110 patients with GSE32062: 7-field clinical fingerprint p=0.005, 21/28 pairs mutual top-1 expression match; GSE53963 independent — F012 supersedes F010, D010 sets how we count independent replications). Closed T003 via sub-agent (PanCanAtlas CDR: 587 OV patients, all 302 pool patients matched, 1 event disagreement, median OS diff 0 d, PFI now available — F011; stdlib xlsx converter added as agent/scripts/xlsx_to_csv.py). Updated E003's outcome and interpretation with the independence result.
State: E003 done (verdict supported, unchanged — the rule was applied to the rows as recorded). Sensitivity re-aggregation of those rows without GSE17260: pooled dC +0.030 [+0.007, +0.052] vs +0.036 [+0.010, +0.061]. Independent cohorts clearing the bar: GSE32062 (CI excludes 0) and GSE49997 (CI crosses 0, immature). Colab session stopped. T006's four runs are orphan warnings in check: they belong to a task, and only experiments take --experiment.
Next: E004 raised to p1 — PFI labels exist now, so the platform-disjoint design on progression-free survival is the strongest available supporting evidence and it needs no new data. Then T002 (GSE9891) as a genuinely independent same-platform validator, then T005 write-up.
Watch: os-validation/expression_validation.csv is 99.8 MiB, just under the GitHub limit. Any new validator cohort must be overlap-checked before scoring (D010). GSE53963, the highest-event validator, still shows nothing (+0.004).

## 2026-09-21 22:36 · E004 PFS: not supported
Did: ran E004 end to end. Pre-registered the stricter compound rule (≥2 of 3 independent validators at ΔC ≥ 0.03 AND pooled CI > 0) as a computed indicator before any label table existed; user chose native per-cohort event definitions. Sub-agent built pfs-training-pool (472/356) and pfs-validation (732/512) via agent/scripts/pfs_labels.py, reusing the OS sample sets and expression matrices (F013 on definition heterogeneity; GSE30161 kept after its precomputed pfi-days field checked out against raw dates; GSE26712, GSE14764, GSE53963 have no progression fields and drop out). Tuned on pool CV only (gene count x l1_ratio; best 500 genes, l1 0.5, pool CV 0.552), dry-ran the scoring path, then scored once.
State: E004 done, not-supported (F014). 0/3 validators cleared 0.03: GSE32062 +0.020, GSE140082 +0.018, GSE49997 −0.051; pooled +0.001 [−0.034, +0.037], I²=0.73. The score still carries pool signal (HR 1.175/SD, p=0.008) and won in 2 of 3 cohorts, so this is a null, not a reversal. Candidate pfs-first-pass-v1 is spent. Colab session stopped.
Next: T002 (GSE9891) matters more now — the OS result rests on 2 independent cohorts and PFS did not corroborate it, so a fresh independent OS cohort is the highest-value evidence left. Then T005, which must report E004's null beside E003's positive. T004 (bigger TCGA pool) would help both.
Watch: residual disease barely predicts progression (p=0.23 vs 0.004 for death) — the endpoint may be noisier, not the signal weaker. I²=0.73 means one cohort (GSE49997, n=171) decides the pooled PFS result; a 3-cohort rule is fragile. D001's premise that PFS was the higher-value endpoint is now contradicted.
