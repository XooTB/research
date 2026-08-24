# Dataset verification report

**Location:** `/home/xoot/Projects/research/datasets/ovarian-cancer-prognosis-ml/tcga-ov-xena-clinical-matrix`

- Files: 1
- Total size: 574.8 KB
- Tabular files profiled: 0

## `OV_clinicalMatrix`  (574.8 KB, )

## Usability verdict
**Usable survival labels** for TCGA-OV.

- 630 samples × 102 clinical fields
- Has `vital_status`, `days_to_death`, `days_to_last_followup`, stage, grade, residual disease
- Construct OS time as death days or last follow-up for censored cases
