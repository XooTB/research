# OS workstream: train/validation split (decided 27 Aug 2026)

**Parent doc:** `docs/current-focus-overall-survival.md`
**Basis:** data audit `docs/ovarian-cancer-prognosis-opportunities.md` §5–6 + Appendix B, verified against files on disk (phenotype CSVs and gzipped series matrices), 27 Aug 2026.

---

## 1. The deciding argument

The best cohorts (GSE32062, GSE53963) are simultaneously the best training material and the only validators with enough deaths to be decisive. **Validation power is scarcer than training power**: the pool reaches ~750 patients / ~485 deaths without them, but without the Agilent block no held-out cohort can convict or acquit a model (next-best is immature GSE140082, then GSE49997 with 48 events).

Therefore the split is by **platform family**: pool = RNA-seq + Affymetrix; validators = Agilent, Illumina, ABI. This satisfies the audit non-negotiable ("external cohort, preferably a different platform") by construction, and keeps a within-platform replication arm (GSE17260 vs GSE32062) that isolates cohort effects from platform effects.

Consciously accepted tradeoff: keeping the Agilent trio out costs ~30% of potential training events. The alternative (maximal pool, validate only on GSE140082 + GSE49997 + later GSE9891) has no validator capable of delivering the replicated ΔC ≥ 0.03 verdict this workstream is graded on.

## 2. Fitness criteria (used for the assignment)

**Fit for the training pool** if a cohort has:

1. **Events, not just samples** — penalized Cox on ~10–15k gene features needs deaths; floor ≈ 40–50 events to contribute meaningfully (smaller cohorts may still be pooled as minor rows if they could never validate alone).
2. **Population match** — HGSOC/advanced by construction, or cleanly subsettable via a histotype column.
3. **Mature follow-up and verified OS coding** (traps: `status` vs `status_2` in GSE26712, channel-2 phenotypes in GSE53963, column-shifted characteristics in GSE30161).
4. **Clinical covariates** (age, stage, residual) for the baseline and combined model.
5. **Platform harmony with the pool** — fewer platform families in the pool means less gene-collapse/batch-correction noise.
6. **No identity leakage** into validation (TCGA barcodes in GSE53963, GSE51088).

**Reserved for validation** if a cohort:

1. **Has enough deaths to decide** — ≥ ~90–100 events for a tight external C-index CI (GSE14764's 21 deaths are why it produced a meaningless 0.53/0.505 in the first runs).
2. **Is a different platform family from the pool.**
3. **Has independent patients** after dedupe.
4. **Has mature OS** so KM log-rank separation is a fair test (argues against immature GSE140082 as a *primary* validator).
5. **Has covariates** so ΔC-index vs the clinical baseline can be computed on it.

**Fit for neither:** wrong population (GSE8842, all stage I), wrong endpoint (GSE13876, DSS-like on a custom array), unverifiable labels (GSE18520), unusable feature space (GSE19161, 658 probes), no OS at all (GSE51373, GSE131978, GSE9891 today, GSE14407, GSE154600).

## 3. Training pool — RNA-seq + Affy family

**751 patients, 485 deaths** (HGSOC-subsetted where applicable).

| Cohort | n / deaths | Platform | Why it trains | Caveats |
|---|---|---|---|---|
| TCGA-OV HiSeqV2 | 302 / 182 | RNA-seq | Anchor; only cohort with complete age+stage+residual+grade; serous by construction | Cox-usable n is **302**, not 303 (`TCGA-04-1357-01` has vital status but no time); Xena OS, not PanCanAtlas CDR |
| GSE26712 | 185 / 129 | Affy GPL96 | Second-biggest event count in the library; validator role already spent (weak 0.560 in run `20260824T195053Z`) | No age/stage/grade columns; `status`=DOD is DSS-flavored — disclose event-definition heterogeneity |
| GSE63885 | 70 serous / 62 | Affy GPL570 | Highest event rate in pool; mature (to 4080 d); BRCA1 labels a bonus | 26/101 missing OS; CSVs converted 27 Aug; labels from `csv/phenotype.csv` via substring-matched characteristic keys |
| GSE26193 | 79 serous / 60 | Affy GPL570 | 20-year follow-up | Subset serous; no age, no residual |
| GSE30161 | 47 serous / 33 | Affy GPL570 (FFPE) | Full covariates; too few events to ever validate alone | FFPE; CSV characteristics column-shifted — reparse per-sample key:value |
| GSE14764 | 68 serous / 19 | Affy GPL96 | Proven incapable of deciding anything as a validator (coin-flip 0.53/0.505); events aggregate in pool | Weakest contributor; drop if harmonization diagnostics look bad |

## 4. Held-out validation — 3 non-Affy platform families, **410 events** (disk-verified)

| Cohort | n / deaths | Platform | Role | Caveats |
|---|---|---|---|---|
| **GSE32062** | 260 / 121 | Agilent GPL6480 | **Flagship.** Pure HGSOC, uniform platinum+taxane, mature (128 mo); cleanest possible external test | No age → clinical baseline is stage+residual only; expression streamed from `expression.csv.zip` |
| **GSE53963** | **160 / 139** | Agilent GPL6480 | Second flagship; 139/160 event rate = strongest KM-separation test in library; has all covariates incl. age | **14 TCGA barcodes dropped** (all deaths; 13 overlap HiSeq). Converter `phenotype.csv` is ch1-only — labels reparse ch2 of the gzipped matrix |
| **GSE17260** | 110 / 46 | Agilent GPL6480 | Within-platform replication arm vs GSE32062 (same lab+platform: isolates cohort effect from platform effect) | No age; 26 grade-1 serous retained (split-doc target includes them) |
| GSE140082 | 191 HGSOC III/IV / 56 | Illumina GPL14951 (FFPE) | Secondary, **flagged immature** (max ~3.6 y OS); bev-vs-standard arm enables a predictive side check | CSVs converted; subset = serous + high.grade + FIGO III/IV |
| GSE49997 | 171 serous / 48 | ABI GPL2986 | Tertiary; platform breadth; supportive only (below conviction threshold) | Short follow-up (max 49 mo); 10 rows `excluded=yes` dropped; `figo grade` column is stage |
| GSE9891 | 285 | Affy GPL570 | **Blocked — confirmed no survival on disk.** Once curatedOvarianData/Tothill survival lands: premier validator and large same-platform (Affy) external control | Also drop 18 LMP samples when unblocked |

## 5. Excluded from both

| Cohort | Reason |
|---|---|
| GSE51088 | Optional tier-3 validator only after CSV conversion + dropping 23 TCGA barcodes; two-color |
| GSE13876 | DSS-like endpoint (status 1 = OC death), custom GPL7759 array, technical replicates — endpoint mismatch with all-cause OS |
| GSE18520 | Survival coding unverifiable (`150 (A)` vs bare numbers) without adopting the paper's coding |
| GSE19161 | 658 probes — cannot validate a genome-wide signature |
| GSE8842 | All FIGO stage I — wrong population for advanced-HGSOC OS |
| GSE51373, GSE131978, GSE14407, GSE154600 | No OS labels |

## 6. Validation of the reasoning (disk check, 27 Aug 2026)

Every criterion above was checked against the actual files; five findings mattered:

1. **Event-count criterion held.** Every ≥ ~45-death cohort with clean labels got a role; sub-40-event cohorts (GSE14764: 19, GSE30161: 33) were pooled as minor rows or excluded. No exceptions needed.
2. **Platform purity is enforceable.** Pool = {RNA-seq, GPL96, GPL570}; validators = {GPL6480 ×3, GPL14951, GPL2986}. Zero overlap.
3. **Covariate criterion partially failed → downgraded to a design note.** GSE26712, GSE26193, GSE63885, GSE14764 lack age; flagship Agilent validators also lack age. Consequence: the pooled clinical+expression model cannot assume complete covariates — use cohort-available covariates or imputation; flagship baseline is stage+residual. Weakens, does not break, the assignment.
4. **Disk state (27 Aug morning) vs compiled (27 Aug evening):** the morning check found TCGA Cox-usable n = 302 (not 303) and missing phenotype CSVs for GSE53963 / GSE140082 / GSE63885. All three CSVs now exist; GSE53963's converter CSV is still unusable for labels (ch1 only) and the labels script reparses ch2. GSE32062 expression is streamed from `expression.csv.zip`.
5. **Leakage confirmed:** 13 of GSE53963's 14 TCGA barcodes overlap HiSeq training rows (the 14th, `TCGA-25-1878-01`, is in the clinical matrix only).

## 7. Pre-pooling checklist (blocks M2)

- [x] Convert phenotype CSVs for GSE53963 (ch2), GSE140082, GSE63885 (§4 of focus doc) — all done 27 Aug; GSE53963's converter CSV is ch1-only/unusable, labels reparse ch2 in `agent/scripts/os_validation_labels.py`
- [x] Reparse GSE30161 phenotype (column-shifted characteristics) — done in `agent/scripts/os_pool_labels.py`
- [x] Dedupe GSE53963 × TCGA (14 barcodes) — done in `os_validation_labels.py` via ch2 `tcga_sampleid`; result **160/139** (all 14 dropped were deaths)
- [x] Gene-symbol collapse plan: HiSeq 20,530 symbols ∩ GPL96 22,283 probes ∩ GPL570 54,675 probes (~12k expected) — done: **11,474 common symbols**, GPL96 bottleneck; `agent/scripts/os_pool_expression.py`
- [x] Decide covariate strategy for age-missing pool cohorts — cohort-available, no imputation (training doc, 27 Aug)
- [x] Read GSE32062 expression from zip — `os_validation_expression.py` streams it via zipfile. (GSE9891 expression still zip-only, cohort remains blocked on survival labels.)

**Validation set compiled 27 Aug 2026** — `datasets/ovarian-cancer-prognosis-ml/os-validation/` (892 patients / 410 deaths; expression in the 11,474-symbol training space). Tooling: `agent/scripts/os_validation_labels.py`, `agent/scripts/os_validation_expression.py`. How + next: `docs/os-validation-dataset.md`. M2 done on both sides.

## 8. What was compiled, how, and what is next

**Training pool** (`docs/os-training-dataset.md`): `os_pool_labels.py` + `os_pool_expression.py` → 751 / 485, 11,474 symbols. GPL96 is the gene-set bottleneck. Covariates: cohort-available, no imputation.

**Validation set** (`docs/os-validation-dataset.md`): `os_validation_labels.py` + `os_validation_expression.py` → 892 / 410, same 11,474 rows so a trained model scores without remapping. GSE53963 labels come from a ch2 series-matrix reparse (converter CSV discarded); 14 TCGA `tcga_sampleid` samples dropped (all deaths → 160/139). `verify` asserts train/validation `sample_id` disjointness.

**Next (does not change this split):**
1. **M3** — clinical-only Cox baselines on every compiled cohort (flagship validators: stage+residual, no age).
2. **M4** — expression models trained on the pool, scored on all five validators. Handle empty cells (validation matrix 2.8% empty: platform coverage, worst on ABI). No batch correction yet — that is an M4 modelling choice.
3. GSE9891 survival, PanCanAtlas CDR, TCGA U133A remain optional acquisitions (focus doc §4); they do not unblock M3.
