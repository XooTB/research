# OS validation labels

Per-patient overall-survival (OS) labels for the held-out validation cohorts defined in `docs/os-train-validation-split.md` §4: the Agilent GPL6480 trio (GSE32062, GSE53963, GSE17260), Illumina GPL14951 (GSE140082), and ABI GPL2986 (GSE49997). Schema is identical to the training-pool labels (`docs/os-training-labels.md`); join to `os-validation/expression_validation.csv` on `sample_id`.

**Script:** `agent/scripts/os_validation_labels.py` (Python 3 stdlib only).
**Output:** `datasets/ovarian-cancer-prognosis-ml/os-validation/labels.csv`

---

## How to run

```bash
python3 agent/scripts/os_validation_labels.py all       # write merged labels.csv (default)
python3 agent/scripts/os_validation_labels.py verify    # re-read and assert n/deaths + leakage
python3 agent/scripts/os_validation_labels.py gse53963  # one cohort to stdout
```

`--data-root`, `--out`, `--train-labels` override defaults. `verify` exits nonzero if per-cohort counts diverge from the targets below, if `sample_id`s collide, if times are negative, if event/platform coding is off, **or if any validation `sample_id` appears in the training-pool labels** (leakage check against `os-training-pool/labels.csv`).

---

## Per-cohort extraction

### 1. GSE32062 (Yoshihara 2012, GPL6480) — flagship — 260 / 121

- Source: `gse32062-gpl6480-ovarian-expression-series-matrix/csv/phenotype.csv`.
- Pure HGSOC — all 260 rows kept, no histology filter. Time: `os (m)` in months → days. Event: `death (1)` (1=dead, 0=censored; deaths have shorter follow-up, verified by cross-tab).
- **Trap:** `status` is GEO's public-on date, not vital status (same trap class as GSE26712's `status_2`).
- Stage `Stage`, grade `grading` (2/3 only), residual `surgery status` (casefold — one row is `Optimal`). No age. Uniform platinum+taxane (both flags 1 for all 260).

### 2. GSE53963 (Yoshihara, GPL6480 two-color) — 160 / 139

- **Trap (two traps, actually):** phenotypes are on **channel 2** of the gzipped series matrix, and ch2 keys are **column-shifted** across samples (optional `substage` and `tcga_sampleid` keys). The converter's `csv/phenotype.csv` is unusable for labels (ch1 only). The script reparses `GSE53963_series_matrix.txt.gz` per-sample key:value, same strategy as GSE30161 but on `!Sample_characteristics_ch2`.
- **Mandatory dedupe:** the 14 samples with a non-empty ch2 `tcga_sampleid` are dropped (13 overlap the TCGA HiSeqV2 training rows; the 14th is in the clinical matrix only). All 14 are deaths → 174−14 = **160 patients**, 153−14 = **139 deaths**. The split doc's "~160/~140" estimate resolves to 160/139 on disk.
- Time: `time_fu_months` (months → days). Event: `vital_status` (Dead=1, Alive=0). All 174 are `morphology=Serous`.
- Age `age_at_dx`, stage `Stage` (one sample is the literal `III/IV`, kept as recorded), grade `grade` (**note: scale includes 4** — not a FIGO 1–3 scale), residual `debulking` (Optimal/Sub-optimal/Unknown).

### 3. GSE17260 (Yoshihara 2010, GPL6480) — 110 / 46

- Source: `gse17260-ovarian-expression-series-matrix/csv/phenotype.csv`.
- All 110 serous. Time: `overall survival (m)` (months → days). Event: `death (1)`.
- **The 110/46 target includes 26 grade-1 serous samples** (7 deaths) — do not grade-filter. Flagged because grade-1 serous may include LGSOC; keep for the split-doc target, disclose downstream.
- Stage `Stage`, grade `tumor grade`, residual `cytoreductive surgery` (`optimal` / `not optimal`). No age.

### 4. GSE140082 (ICON7, GPL14951 FFPE) — 191 / 56

- Source: `gse140082-ovarian-expression-series-matrix/csv/phenotype.csv` (converter output correct, ch1, keys aligned).
- Subset: `histology.serous == serous` **and** `newgrade == high.grade` **and** `figo_stage` in {III, IV} → 191/56 exactly. (Without the stage filter: 212/56.)
- Time: `final_ostm` in **days** (1–1326). Event: `final_osid` (1=dead, 0=censored). **Trap:** `newgrade` missingness is the literal string `NA`.
- Age `age`, residual `debulking_status`, treatment arm `treatment` (bevacizumab 96 / standard 95 in the subset) recorded in `notes`.
- **Flagged immature:** max OS ~3.6 years — KM log-rank on this cohort is a weaker test (split doc §4).

### 5. GSE49997 (Pils, GPL2986) — 171 / 48

- Source: `gse49997-ovarian-expression-series-matrix/csv/phenotype.csv`.
- Drop `excluded == yes` (10 rows; their clinical fields are empty but **their GSMs remain as expression columns**). Keep `histology == Serous` → 171/48.
- Time: `os month` (months → days; NA is the empty string). Event: `os event` (1=dead).
- **Trap:** `figo grade` is FIGO **stage** (II/III/IV), not grade. Real grade is `grade` (`3` / `1&2` / `#NULL!`; `#NULL!` → empty). One kept row (GSM1211626) has `#NULL!` grade — kept, grade empty.
- Age `age` (26–85, complete), residual `residual tumor` (Yes/No). Short follow-up (max ~49 months) — supportive only.

---

## Counts actually obtained

`python3 agent/scripts/os_validation_labels.py all && … verify` (27 Aug 2026):

| Cohort | n | deaths | Platform | Role |
|---|---:|---:|---|---|
| gse32062 | 260 | 121 | GPL6480 | Flagship |
| gse53963 | 160 | 139 | GPL6480 | Second flagship (TCGA-deduped) |
| gse17260 | 110 | 46 | GPL6480 | Within-platform replication |
| gse140082 | 191 | 56 | GPL14951 | Secondary, immature |
| gse49997 | 171 | 48 | GPL2986 | Tertiary, supportive |
| **TOTAL** | **892** | **410** | | |

All cohorts `event_definition=all_cause` (binary dead/alive vital status). No `sample_id` collisions; zero overlap with the training pool (leakage check in `verify`). Follow-up after conversion: ~1 day (GSE17260 / GSE32062) to ~201 months (GSE53963).

Covariate completeness (non-empty cells):

| Cohort | age | stage | grade | residual |
|---|---:|---:|---:|---:|
| gse32062 | 0/260 | 260/260 | 260/260 | 260/260 |
| gse53963 | 160/160 | 160/160 | 160/160 | 157/160 (3 Unknown → empty after `clean`) |
| gse17260 | 0/110 | 110/110 | 110/110 | 110/110 |
| gse140082 | 191/191 | 191/191 | 191/191 | 191/191 |
| gse49997 | 171/171 | 171/171 | 170/171 | 171/171 |

Flagship clinical baseline is therefore **stage + residual only**. Age-complete validators: GSE53963, GSE140082, GSE49997. Three GSE53963 residual values are the source string `Unknown` and become empty via the shared NA cleaner. One GSE49997 grade is `#NULL!` → empty.

## Deviations from `docs/os-train-validation-split.md`

- **GSE53963 is 160/139, not ~160/~140.** Every dropped TCGA duplicate is a death (153−14). Split doc marked its numbers as estimates; this is the disk-verified value.
- **GSE17260 grade-1 serous retained** (26 samples) — required to hit the 110/46 target.
- Residual vocabularies are not harmonized (`optimal`/`suboptimal` vs `not optimal` vs `Sub-optimal` vs Yes/No). Stage vocab differs too (`IIIc` vs `III`). Downstream clinical models must recode.
- Age exists only for GSE53963, GSE140082, GSE49997; flagship baseline is stage+residual only (per split doc §6 finding 3).
- Three GSE53963 `debulking=Unknown` values are treated as missing residual (157/160 filled), which does not change n/deaths.

---

## Next

M3 clinical baselines consume this file as-is. Recode stage/residual at modelling time; do not edit the extractors to invent a common vocabulary. GSE140082 treatment arm is already in `notes` if a predictive (bev vs standard) side check is wanted.

## Pointers

- Split decision: `docs/os-train-validation-split.md`
- Training-side mirror: `docs/os-training-labels.md`
- Expression: `docs/os-validation-expression.md`
- Workstream: `docs/current-focus-overall-survival.md`
