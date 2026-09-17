# Dataset verification report

**Location:** `datasets/ovarian-cancer-prognosis-ml/tcga-cdr-pancanatlas`

- Files: 3
- Total size: 5.8 MB
- Tabular files profiled: 2

## `TCGA-CDR-SupplementalTableS1.xlsx`  (2.8 MB, .xlsx)

## `ov_subset.csv`  (58.0 KB, .csv)
- Columns (14): bcr_patient_barcode, type, age_at_initial_pathologic_diagnosis, ajcc_pathologic_tumor_stage, clinical_stage, histological_type, histological_grade, residual_tumor, OS, OS.time, DSS, DSS.time, PFI, PFI.time
- Rows: 587 (stdlib-csv)

## `tcga-cdr.csv`  (2.9 MB, .csv)
- Columns (34): , bcr_patient_barcode, type, age_at_initial_pathologic_diagnosis, gender, race, ajcc_pathologic_tumor_stage, clinical_stage, histological_type, histological_grade, initial_pathologic_dx_year, menopause_status, birth_days_to, vital_status, tumor_status, last_contact_days_to, death_days_to, cause_of_death, new_tumor_event_type, new_tumor_event_site, new_tumor_event_site_other, new_tumor_event_dx_days_to, treatment_outcome_first_course, margin_status, residual_tumor, OS, OS.time, DSS, DSS.time, DFI, DFI.time, PFI, PFI.time, Redaction
- Rows: 11160 (stdlib-csv)

## Usability verdict

**Usable.** Standardized PanCanAtlas Clinical Data Resource (Liu et al. 2018, Cell), downloaded
from GDC (`https://api.gdc.cancer.gov/data/1b5f413e-a8d1-4d10-92eb-7c4ae739ed81`), verified as a
genuine `.xlsx` with a `TCGA-CDR` sheet before conversion. Converted with
`agent/scripts/xlsx_to_csv.py` (stdlib zipfile + ElementTree; no pandas in this venv) and subset to
`type == "OV"` (587 patients) with `agent/scripts/tcga_cdr_ov_compare.py`.

Compared against the current TCGA-OV training-pool labels
(`datasets/ovarian-cancer-prognosis-ml/os-training-pool/labels.csv`, `cohort ==
"tcga-ov-hiseqv2"`, 302 patients), matched by 12-character `bcr_patient_barcode`:

- 302/302 pool patients found in CDR OV.
- 1 OS event disagreement: `TCGA-29-A5NZ` — pool (Xena) has `os_event=0` (censored) at 984 days;
  CDR has `OS=1` (dead) at 1088 days. All other 301 patients agree exactly (`OS.time` diff: median
  0, IQR 0, max 104 days — that one patient).
- All 302 matched patients gain a usable `PFI` (`PFI.time > 0`, event non-missing); the pool
  currently has no PFI at all.
- CDR OV has 285 more patients (587 total) than the current 302-patient pool.

See F011 (`research.py show F011`) for the full comparison; the labels.csv switch decision is for
the main agent (T003), not made here.
