# OS training-pool labels

Per-patient overall-survival (OS) labels for the RNA-seq + Affymetrix training pool defined in `docs/os-train-validation-split.md`. This is the sample × OS × covariate table that modelling notebooks should join to expression; it is **not** yet a gene-harmonized matrix.

**Script:** `agent/scripts/os_pool_labels.py` (Python 3 stdlib only: `csv`, `gzip`, `argparse`, …).
**Output:** `datasets/ovarian-cancer-prognosis-ml/os-training-pool/labels.csv`

---

## How to run

```bash
python3 agent/scripts/os_pool_labels.py all      # write merged labels.csv (default)
python3 agent/scripts/os_pool_labels.py verify   # re-read and assert n/deaths
python3 agent/scripts/os_pool_labels.py tcga     # one cohort to stdout
python3 agent/scripts/os_pool_labels.py gse30161
```

`--data-root` and `--out` override the default dataset root and output path. `verify` exits nonzero if per-cohort counts diverge from the split-doc targets, if `sample_id`s collide, if times are negative, or if `os_event` is not in `{0,1}`.

The script emits whatever the parsers find. It does not invent or drop rows to hit a target. If `verify` fails, treat that as a real discrepancy (the split doc itself warns some numbers were estimates).

---

## Schema

One row per patient/sample. Histology, stage, grade, and residual disease are **as recorded** in the source (not recoded to a common vocabulary).

| Column | Meaning |
|---|---|
| `cohort` | `tcga-ov-hiseqv2` \| `gse26712` \| `gse63885` \| `gse26193` \| `gse30161` \| `gse14764` |
| `sample_id` | TCGA barcode or GEO GSM accession |
| `geo_accession` | GSM id; empty for TCGA |
| `platform` | `rnaseq_hiseqv2` \| `GPL96` \| `GPL570` |
| `histology` | Source histotype string |
| `os_time_days` | Follow-up in days (`years * 365.25`, `months * 365.25/12`) |
| `os_event` | `1` = death, `0` = censored |
| `os_time_original` | Time string as recorded, before conversion |
| `os_time_unit` | `days` \| `months` \| `years` |
| `event_definition` | `all_cause` \| `dod_dss_flavored` |
| `age_years` | Empty if the cohort has no age field |
| `figo_stage`, `grade`, `residual_disease` | As recorded; empty if missing |
| `notes` | Extraction remarks (traps, event coding, chemoresponse) |

Cox-usable filter applied to every cohort: finite `os_time_days >= 1`.

---

## Per-cohort extraction

### 1. TCGA-OV HiSeqV2 — 302 / 182

- Expression sample list: header of `tcga-ov-xena-rna-seq-hiseqv2/csv/HiSeqV2.csv` (308 barcodes: 303 primary + 5 recurrent).
- Clinical: `tcga-ov-xena-clinical-matrix/csv/OV_clinicalMatrix.csv`.
- Keep `sample_type == "Primary Tumor"` (drops the 5 recurrent tumors that sit on the expression matrix).
- `vital_status` in `{LIVING, DECEASED}`; time = `days_to_death` if deceased else `days_to_last_followup`.
- Dropped for missing time: **`TCGA-04-1357-01`** (LIVING, both day fields empty) → 302.
- `event_definition=all_cause`. Histology = `Serous Cystadenocarcinoma` (serous by construction). Age/stage/grade/residual from Xena.

### 2. GSE26712 (Bonome, GPL96) — 185 / 129

- Source: `gse26712-ovarian-expression-series-matrix/csv/phenotype.csv`.
- **Trap:** `status_2` is GEO’s public-on date. Vital field is `status`: `DOD*` → event, `AWD*` / `NED*` → censored.
- Time: `survival years` → days. Residual: `surgery outcome` (Optimal / Suboptimal). No age/stage/grade.
- Exclude 10 HOSE normal controls (`tissue` / `source_name_ch1` / `title`). The 185 tumours have no histotype column; histology is the recorded `tissue` value (`Late-stage high-grade ovarian cancer`).
- `event_definition=dod_dss_flavored` — DOD is disease-specific, not all-cause OS. Disclose this when pooling.

### 3. GSE63885 (Lisowska, GPL570) — 70 / 62

- Source: `gse63885-ovarian-expression-series-matrix/csv/phenotype.csv`.
- **Trap:** characteristic headers contain colons, parenthetical legends, and a comma inside the platinum-sensitivity key, so that header splits into extra columns (Appendix B). Match OS / last-status / histology / grade / residual by **substring**, never exact equality. Do not use GEO `status` (public-on date).
- Histology field (`histophatological type of tumor`, source spelling): 73 serous of 101. OS-days `NA` on 3 of those → **70** serous with OS, 62 DOD.
- DOD → event, AWD/NED → censored. FIGO, grade (G2–G4), residual (R0/R1/R2) captured where present.
- `event_definition=dod_dss_flavored`.

### 4. GSE26193 (Mateescu, GPL570) — 79 / 60

- Source: `gse26193-ovarian-expression-series-matrix/csv/phenotype.csv`.
- Subset `histological type` containing “serous” (79 of 107). Time: `os time (years)` → days.
- **`os event` coding (inspected):** `1` = death, `0` = censored. Binary OS, not DOD-labelled → `event_definition=all_cause`.
- Stage and grade present; no age, no residual.

### 5. GSE30161 (Ferriss, GPL570 FFPE) — 47 / 33

- **Trap:** `csv/phenotype.csv` is column-shifted on `characteristics_1..13`. The script **ignores that CSV** and reparses `GSE30161_series_matrix.txt`: `!Sample_geo_accession` for column order; each `!Sample_characteristics_ch1` cell split as `key : value` **per sample** because keys are not in the same order across samples (one sample starts `datedx` where others have `surgtype`).
- Subset `histo == Serous` (47 of 58). Time: `overall survival days`. Event: `censoring(dead=1, alive=0)` (whitespace in the key is normalized).
- Age, grade, FIGO `Stage`, residual (`optimal`: Optimal / Sub-optimal), chemoresponse (in `notes`). One serous sample has no `optimal` key → empty residual. `event_definition=all_cause`.

### 6. GSE14764 (Denkert, GPL96) — 68 / 19

- Source: `gse14764-ovarian-expression-series-matrix/csv/phenotype.csv`.
- Subset `histological type` containing “serous” (68 of 80). Time: `overall survival time` in **months** → days.
- **`overall survival event` coding (inspected):** `1` = death, `0` = censored → `event_definition=all_cause`. Residual is `0`/`1`/`NA` as recorded (4 NA among serous become empty).

---

## Counts actually obtained

`python3 agent/scripts/os_pool_labels.py all && … verify` (27 Aug 2026):

| Cohort | n | deaths | Platform | event_definition |
|---|---:|---:|---|---|
| tcga-ov-hiseqv2 | 302 | 182 | rnaseq_hiseqv2 | all_cause |
| gse26712 | 185 | 129 | GPL96 | dod_dss_flavored |
| gse63885 | 70 | 62 | GPL570 | dod_dss_flavored |
| gse26193 | 79 | 60 | GPL570 | all_cause |
| gse30161 | 47 | 33 | GPL570 | all_cause |
| gse14764 | 68 | 19 | GPL96 | all_cause |
| **TOTAL** | **751** | **485** | | 496 all-cause / 255 DSS-flavored |

Covariate completeness (non-empty cells):

| Cohort | age | stage | grade | residual |
|---|---:|---:|---:|---:|
| tcga-ov-hiseqv2 | 302/302 | 300/302 | 300/302 | 266/302 |
| gse26712 | 0 | 0 | 0 | 185/185 |
| gse63885 | 0 | 70/70 | 70/70 | 70/70 |
| gse26193 | 0 | 79/79 | 79/79 | 0 |
| gse30161 | 47/47 | 47/47 | 47/47 | 46/47 |
| gse14764 | 0 | 68/68 | 68/68 | 64/68 |

No `sample_id` collisions across cohorts. Follow-up range after conversion: ~3 days (GSE26193) to ~20.2 years.

---

## Deviations from `docs/os-train-validation-split.md`

None on n/deaths. Every cohort matched the split-doc target exactly.

Documented choices that the split doc does not spell out, but that do not change counts:

- Year/month → day conversion uses 365.25 (Gregorian average year), not 365.
- The `os_time_days >= 1` filter is applied to every cohort, not only TCGA. No extra GEO rows were dropped by it.
- GSE26193 and GSE14764 are labelled `all_cause` because their event fields are binary dead/alive, not DOD/AWD/NED. GSE26712 and GSE63885 stay `dod_dss_flavored`.
- Residual / stage / grade strings are not harmonized (Optimal vs Sub-optimal vs R0/R1/R2 vs 0/1 vs 1-10 mm). Downstream clinical models must recode.

---

## Pointers

- Split decision: `docs/os-train-validation-split.md`
- Messy-field traps: `docs/ovarian-cancer-prognosis-opportunities.md` Appendix B
- Validation-side mirror: `docs/os-validation-labels.md`
