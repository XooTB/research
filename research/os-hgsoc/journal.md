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
