# Findings

Append-only. Add with `research.py new finding`; replace with a new entry that `supersedes:` the old one.

## F001 · 2026-08-25 · TCGA-trained LASSO-Cox transfers poorly to Affymetrix cohorts
refs: E001, run:20260824T195053Z-tcga-ov-lasso-cox, gse26712, gse14764
tags: transfer, lasso-cox
External C-index 0.560 (GSE26712, log-rank p 0.68) and 0.530 (GSE14764, p 0.88), against a TCGA
clinical CV C-index of 0.615. The internal expression CV C-index (0.605) did not predict transfer.

## F002 · 2026-08-25 · Internal AUC gains of the 3-year classifier vanish externally
refs: E002, run:20260825T034757Z-tcga-ov-3yr-mortality-clf, gse26712, gse14764
tags: transfer, classifier
Expr+clin ENET CV AUC 0.695 vs clinical LR 0.646 on TCGA, but external AUC 0.615 (GSE26712)
and 0.505 (GSE14764).

## F003 · 2026-08-27 · GSE14764 is too small to decide anything as a validator
refs: docs/os-train-validation-split.md, gse14764
tags: cohort-quality
68 serous / 19 deaths; coin-flip results in E001/E002 (0.53 C, 0.505 AUC). Pooled into training
instead, where its events still count.

## F004 · 2026-08-27 · TCGA Cox-usable n is 302, not 303
refs: T001, tcga-ov-xena-clinical-matrix, docs/os-training-labels.md
tags: tcga-ov, labels
TCGA-04-1357-01 has a vital status but no survival time.

## F005 · 2026-08-27 · GSE53963 contains 14 TCGA duplicates; its ch1 phenotype CSV is unusable
refs: T001, gse53963, docs/os-validation-labels.md
tags: leakage, gse53963, labels
14 TCGA barcodes (all deaths) dropped → 160 patients / 139 deaths. Survival lives in channel 2 of
the series matrix; labels come from a ch2 reparse in os_validation_labels.py.

## F006 · 2026-08-27 · GSE9891 has no survival data on disk
refs: T002, gse9891
tags: gse9891, blocked
The field's usual validator is dead weight until outcomes are attached from curatedOvarianData
or the Tothill supplements.

## F007 · 2026-08-27 · Event definitions are heterogeneous across cohorts
refs: docs/os-train-validation-split.md, gse26712, gse13876
tags: endpoint, labels
GSE26712 `status` = DOD (disease-specific flavour) is kept in the pool with disclosure; GSE13876
is DSS-like and excluded from all-cause OS.

## F008 · 2026-08-27 · Two validators have immature follow-up
refs: docs/os-train-validation-split.md, gse140082, gse49997
tags: follow-up, validation
GSE140082 max OS ~3.6 years; GSE49997 max 49 months. Treat as secondary/supportive, not
deciding, cohorts.

## F009 · 2026-09-18 · Expression adds replicated prognostic value over clinical only when combined with it; gene-only models do not transfer
refs: E003, run:20260917T180930Z-os-first-pass, gse32062, gse17260, gse53963, gse140082, gse49997
tags: transfer, primary-result, expr-clin
E003, candidate os-first-pass-v1, scored once. expr_clin_cox (LASSO score + residual + stage) beat the transported residual+stage Cox by ΔC ≥ 0.03 on 3/5 validators: GSE17260 +0.091 [0.024, 0.149], GSE32062 +0.047 [0.021, 0.071], GSE49997 +0.044 [-0.022, 0.108]; GSE140082 +0.020, GSE53963 +0.004. Pooled (DL random effects) +0.036 [0.010, 0.061], I2=0.41. Absolute external C 0.62-0.69 vs clinical 0.58-0.62. The gene-only models were all at or below the clinical baseline pooled: lasso_cox -0.010, deepsurv -0.011, rsf -0.041 [-0.080, -0.003], i.e. RSF was worse than clinical everywhere. The LASSO score's HR per SD adjusted for residual + stage was above 1 in all five (1.13-1.52), LR p < 0.05 in 4/5 (GSE49997 p=0.094). So the expression signal is real but small, and only visible when clinical factors carry the baseline ranking.

## F010 · 2026-09-18 · Two of the three validators that passed are Yoshihara GPL6480 series that may share patients
refs: E003, gse32062, gse17260, docs/os-train-validation-split.md, docs/os-validation-labels.md
tags: validation, independence, leakage-risk
GSE32062 (Yoshihara 2012, 260), GSE17260 (Yoshihara 2010, 110) and GSE53963 (Yoshihara) are all from the same group on GPL6480. The leakage checks so far (docs/os-validation-labels.md, verify) only tested sample_id collisions with the TRAINING pool; GSM ids differ between series even for a re-hybridised patient, so they cannot rule out patient overlap between GSE17260 and GSE32062. E003's verdict rests on those two plus GSE49997 (short follow-up, F008, CI crosses 0). If GSE17260 is a subset of GSE32062, the replication is effectively one cohort plus one immature one. Must be checked (T006) before the result is presented as replicated.

## F011 · 2026-09-18 · PanCanAtlas CDR agrees with Xena TCGA-OV OS labels and adds PFI
refs: T003, tcga-cdr-pancanatlas, os-training-pool, datasets/ovarian-cancer-prognosis-ml/tcga-cdr-pancanatlas/csv/ov_subset.csv, datasets/ovarian-cancer-prognosis-ml/tcga-cdr-pancanatlas/REPORT.md
tags: tcga-ov, pfi, labels
Downloaded TCGA-CDR-SupplementalTableS1.xlsx from GDC (verified TCGA-CDR sheet), converted to CSV with a new stdlib xlsx parser (agent/scripts/xlsx_to_csv.py; no pandas in this venv), and subset to type==OV (587 patients, agent/scripts/tcga_cdr_ov_compare.py). Compared against the current 302-patient tcga-ov-hiseqv2 training-pool labels (os-training-pool/labels.csv, Xena-derived) matched by 12-char bcr_patient_barcode: 302/302 matched; only 1 OS event disagreement (TCGA-29-A5NZ: pool censored at 984d, CDR dead at 1088d); OS.time diff is 0 for 301/302 and 104 days for that one patient (median/IQR 0, max 104). All 302 gain a usable PFI (PFI.time>0, event present) that the pool currently lacks entirely. CDR OV also has 285 more patients than the current pool (587 vs 302), i.e. a much larger TCGA-OV cohort is available if the pool is rebuilt on GPL-agnostic clinical data rather than restricted to the HiSeqV2 expression sample list. Xena OS labels are essentially confirmed correct (near-zero disagreement); switching to CDR would mainly unlock PFI and a larger n, not fix a labeling problem. Did not modify labels.csv, os-validation/, notebooks, or research/os-hgsoc/experiments/ — that switch decision belongs to the main agent.

## F012 · 2026-09-18 · GSE17260 shares at least a quarter of its patients with GSE32062; GSE53963 is independent
refs: T006, E003, gse17260, gse32062, gse53963, run:20260917T191134Z-t006-validator-overlap, agent/experiments/t006_geo_fingerprint.py
tags: validation, independence, cohort-quality
supersedes: F010
Both Japanese series record stage, residual, grade, PFS months, recurrence, OS months and death. 26 of 110 GSE17260 patients match a GSE32062 patient on all seven fields; permutation null (fields shuffled within GSE32062, 200 draws) gives median 0, max 3, p=0.005. Expression confirms them: for 21 of 28 such pairs the GSE32062 partner is the single best-correlating sample out of 260 (median rank 1; chance 1/260). Mutual-best-match analysis independently flags 22 of 110 (0.4 expected by chance). Union of both criteria: 41 of 110 (37%). The 7-field key misses any patient whose follow-up was updated between the 2010 and 2012 papers, so 26 is a lower bound and the true overlap is plausibly 25-50%. This is NOT train/test leakage — the pool contains no Agilent data — but GSE17260 and GSE32062 are not independent replications of each other. GSE53963 shows no duplicate signal against either (max cross-cohort r 0.137 and 0.457, no fingerprint matches; different collection with fractional follow-up months and TCGA ids, F005) and stays an independent validator.

## F013 · 2026-09-21 · PFS/PFI event definitions are heterogeneous across cohorts
refs: docs/pfs-labels.md, pfs-training-pool, pfs-validation, gse63885, gse30161, tcga-cdr-pancanatlas, F007
tags: pfs, pfi, endpoint, labels
Mirrors F007 (OS event heterogeneity) for the PFS/PFI endpoint built for E004.

- **tcga-ov-hiseqv2**: PFI from the PanCanAtlas CDR counts a new tumour event
  (progression/recurrence/metastasis/new primary) OR death with tumour present as an
  event -- the broadest definition here, since it can register an event from death alone
  with no documented progression.
- **gse26193, gse32062, gse49997, gse17260**: source-coded binary recurrence/progression
  flags (`pfs event`, `rec (1)`, `pfs event`, `recurrence (1)`) with no further clinical
  definition published by GEO beyond the field name.
- **gse140082 (ICON7 trial)**: trial-defined PFS (RECIST progression or death, whichever
  first) -- closer to TCGA's CDR PFI than to the other GEO cohorts, not re-verified against
  the trial protocol here.
- **gse63885**: has no recurrence-flag field at all. Its PFS-analog is *derived* --
  `clinical status at last follow-up` in {AWD, DOD} -> event, NED -> censored -- paired with
  the source's own `dfs - disease-free survival [days]` field, which is defined only from
  the point of remission (0 for all 23 patients whose 1st-line response was not CR; those
  23 fail the >=1 day Cox-usable floor and are excluded, not harmonised).
- **gse26712, gse14764** (pool) and **gse53963** (validation) have no progression field at
  all and drop out of the PFS tables entirely (confirmed by header inspection).

Any model or verdict that pools PFS/PFI across cohorts, or compares a PFI-trained model's
external transfer, must account for this the same way E003 accounted for F007: TCGA's
event is not the same clinical event as most of the GEO cohorts'.

Full per-cohort text: docs/pfs-labels.md. Tables:
datasets/ovarian-cancer-prognosis-ml/pfs-training-pool/labels.csv,
datasets/ovarian-cancer-prognosis-ml/pfs-validation/labels.csv.

## F014 · 2026-09-21 · Expression adds less to clinical factors for progression than for death; E004 not supported
refs: E004, E003, run:20260921T163531Z-e004-pfs-first-pass, gse32062, gse140082, gse49997, F013
tags: pfs, transfer, negative-result
E004 scored pfs-first-pass-v1 once on the three independent PFS validators. No cohort cleared ΔC ≥ 0.03: GSE32062 +0.020, GSE140082 +0.018, GSE49997 −0.051; pooled +0.001 [−0.034, +0.037], I²=0.73. The redundant GSE17260 gave −0.009. Verdict not-supported, against a rule requiring ≥2 cohorts and a pooled CI above zero. The signal is not absent: the expression score kept an adjusted HR of 1.175 per SD (p=0.008) on the pool, and the combined model beat clinical in 2 of 3 validators, just below the bar. What differs from E003 is consistency: I² rose from 0.27 (OS) to 0.73 (PFS), driven by GSE49997 reversing. Pool CV was also weaker for genes alone (0.552 at best vs 0.580 for OS) even though the pool has a higher event fraction (356/472 = 75%). Plausible causes, not tested here: progression is recorded with heterogeneous definitions (F013) and depends on treatment response and imaging schedules rather than tumour biology alone; residual disease barely predicts progression at all (p=0.23 on the pool, vs p=0.004 for OS), so the endpoint itself may be noisier. This contradicts E004's hypothesis (D001 rated PFS the higher-value endpoint) and means the workstream's positive result stays confined to overall survival.
