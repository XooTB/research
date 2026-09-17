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
