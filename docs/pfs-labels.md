# PFS/PFI labels (E004)

Per-patient progression-free-survival (PFS/PFI) labels for the same cohorts and the same
patients as the OS tables (`docs/os-training-labels.md`, `docs/os-validation-labels.md`).
This table does **not** re-decide cohort or patient inclusion: the sample sets are taken
verbatim from `os-training-pool/labels.csv` and `os-validation/labels.csv`, then intersected
with PFS availability in each cohort's raw source. Built for E004 (`research.py show E004`),
the PFS/PFI follow-on to E003.

**Script:** `agent/scripts/pfs_labels.py` (Python 3 stdlib only; imports the parsing helpers
from `os_pool_labels.py` directly rather than duplicating them).

**Output:**
- `datasets/ovarian-cancer-prognosis-ml/pfs-training-pool/labels.csv`
- `datasets/ovarian-cancer-prognosis-ml/pfs-validation/labels.csv`

---

## How to run

```bash
python3 agent/scripts/pfs_labels.py all         # write both labels.csv
python3 agent/scripts/pfs_labels.py pool        # pool only
python3 agent/scripts/pfs_labels.py validation  # validation only
python3 agent/scripts/pfs_labels.py verify      # re-read both and assert n/events + checks
python3 agent/scripts/pfs_labels.py gse63885    # one cohort to stdout
```

`verify` exits nonzero if per-cohort/total counts diverge from the disk-verified targets
below, if `sample_id`s collide, if `pfs_time_days < 1`, if `pfs_event` is not in `{0,1}`,
if `event_definition` is empty or inconsistent within a cohort, if any sample_id appears in
both the pool and validation output, or if a pfs sample_id is not present in the
corresponding OS table (no invented rows).

---

## Schema

One row per patient/sample. `cohort`, `sample_id`, `geo_accession`, `platform`, `histology`,
`age_years`, `figo_stage`, `grade`, `residual_disease` are copied **verbatim** from the
matching OS-table row (same patient, same covariates) — they are not re-extracted.

| Column | Meaning |
|---|---|
| `cohort` | source cohort slug (same slugs as the OS tables) |
| `sample_id` | TCGA barcode or GEO GSM accession (identical to the OS table) |
| `geo_accession` | GSM id; empty for TCGA |
| `platform` | as in the OS table |
| `histology` | as in the OS table |
| `age_years`, `figo_stage`, `grade`, `residual_disease` | as in the OS table |
| `notes` | PFS-specific extraction remark (which raw field(s) were used) |
| `pfs_time_days` | follow-up in days (`years * 365.25`, `months * 365.25/12`) |
| `pfs_event` | `1` = event (definition varies by cohort, see below), `0` = censored |
| `pfs_time_original` | time string as recorded, before conversion |
| `pfs_time_unit` | `days` \| `months` \| `years` |
| `event_definition` | verbatim per-cohort description of what counts as an event |

Cox-usable filter applied to every cohort: finite `pfs_time_days >= 1` (same floor as
`os_time_days >= 1` in the OS tables).

---

## Event definitions differ across cohorts (read before pooling)

Exactly as with OS (`F007`), **the PFS/PFI event definitions are heterogeneous and this
matters for anything that pools cohorts.** Summary (full text is in each row's
`event_definition`):

- **TCGA-OV (CDR PFI)** counts a new tumour event (progression, locoregional recurrence,
  distant metastasis, new primary) **or death with tumour present** as an event — this is
  the broadest definition and is the only one in this table that turns a death into a PFS
  event without a documented progression.
- **GSE26193, GSE32062, GSE49997, GSE17260** use a source-coded binary recurrence/
  progression flag with no further clinical definition published by GEO beyond the field
  name (`pfs event`, `rec (1)`, `pfs event`, `recurrence (1)` respectively).
- **GSE140082 (ICON7 trial)** uses the trial's own PFS definition (RECIST progression or
  death, whichever first) — closer in spirit to TCGA's CDR PFI than to the other GEO
  cohorts, but not verified against the trial protocol here.
- **GSE63885** has no recurrence-flag field at all. Its PFS-analog is *derived* from
  `clinical status at last follow-up` (NED = censored, AWD/DOD = event) paired with the
  source's own `dfs - disease-free survival [days]` field — a judgment call, not a
  published event flag (see below).

A recorded finding documents this heterogeneity (`research.py find pfi heterogeneity` or
`research.py show <F###>` — see the finding created alongside this doc).

---

## Per-cohort extraction

### POOL (source: `os-training-pool/labels.csv`)

#### 1. tcga-ov-hiseqv2 — 302 / 209 (302 of 302 OS samples usable)

- `PFI` / `PFI.time` from the PanCanAtlas CDR (`tcga-cdr-pancanatlas/csv/ov_subset.csv`,
  T003/F011), joined on the 12-char `bcr_patient_barcode` prefix of `sample_id`. All 302
  pool patients matched and all 302 have a usable (binary PFI, finite PFI.time >= 1) row.

#### 2. gse26193 (Mateescu, GPL570) — 79 / 63 (79 of 79 usable)

- `pfs event` / `pfs time (years)` → days. Source-coded 1=progression/0=censored (same
  coding convention as its own `os event`). No finer definition published.

#### 3. gse63885 (Lisowska, GPL570) — 47 / 43 (47 of **70** OS samples usable — 23 dropped)

- **Trap / judgment call:** the source's own `dfs - disease-free survival [days]` field is
  exactly **0** for every one of the 23 patients whose `clinical status post 1st line
  chemotherapy` was not `CR` (complete response) — i.e. 13 `PR`, 7 `P`, 3 `SD`, 0 exceptions
  (verified within the 70-sample OS pool subset: all 47 `CR` patients have `dfs > 0`, all 23
  non-`CR` patients have `dfs == 0`).
  The source defines disease-free survival only from the point of remission; patients who
  never remitted get `t=0` by convention. That fails the `>= 1` Cox-usable floor, so those
  23 are **dropped and reported**, not harmonised or assigned an arbitrary nonzero time.
- **Event is derived, not source-coded:** there is no explicit recurrence-date or
  recurrence-flag field in this cohort. Event is derived from `clinical status at last
  follow-up`: `NED` (no evidence of disease) → censored (0); `AWD` (alive with disease) or
  `DOD` (dead of disease) → event (1). This is a judgment call, documented verbatim in
  `event_definition`, not a published PFS/DFS flag.

#### 4. gse30161 (Ferriss, GPL570 FFPE) — 44 / 41 (44 of 47 OS samples usable — 3 dropped)

- **Trap (same as OS extraction):** `csv/phenotype.csv` is column-shifted; the script
  reparses `GSE30161_series_matrix.txt` the same way `os_pool_labels.py` does for this
  cohort's OS fields.
- The raw matrix carries a **precomputed** `pfi days` field alongside
  `relapse(1=yes, 0=no)`. This was checked against the raw dates before trusting it: for
  all 41 events, `pfi days` equals `datedx`-to-`date.of.relapse` exactly (`datedx` is the
  reference date, not `surgdate` — the two differ by days to weeks per patient and only
  `datedx` reproduces `pfi days` for every event); for all 3 censored (`relapse=0`),
  `pfi days` equals `surgdate`-to-`date.last.follow.up` exactly. **This directly supersedes
  the assumption that this cohort lacks censoring times for progression** — it doesn't; the
  source already computed and shipped a progression-free-interval field, so it is used
  directly rather than re-derived from the raw dates.
- 3/47 serous samples (`GSM746875`, `GSM746878`, `GSM746882`) have `relapse` coded
  `UNKnown` and are dropped (reported).

#### gse26712, gse14764 — EXCLUDED from the PFS pool

- Both confirmed by header inspection of `csv/phenotype.csv`: neither cohort has any
  progression/recurrence/relapse/DFS field. (GSE26712's columns are `tissue`,
  `surgery outcome`, `status`, `survival years`, …; GSE14764's are `figo stage`, `grade`,
  `histological type`, `residual tumor`, `overall survival time`, `overall survival
  event`, …. No PFS-analog in either.)

### VALIDATION (source: `os-validation/labels.csv`)

#### 1. gse32062 (Yoshihara 2012, GPL6480) — 260 / 193 (260 of 260 usable)

- `rec (1)` / `pfs (m)` → days. Source-coded, no finer definition published.

#### 2. gse140082 (ICON7, GPL14951) — 191 / 135 (191 of 191 usable)

- `final_pfsid` / `final_pfstm`. **Unit checked, not assumed:** `final_pfstm` values run up
  to 1240 within this 191-patient subset; confirmed to already be in **days** (not months)
  by comparing against `final_ostm` (already known to be days from the OS extraction) —
  `pfs <= os` holds for all 191/191 rows, and the two fields' ranges are consistent with a
  shared day-scale (`final_ostm` max 1281 in the same subset). Trial-defined PFS (RECIST
  progression or death, whichever first) per ICON7, not re-verified against the protocol.

#### 3. gse49997 (Pils, GPL2986) — 171 / 108 (171 of 171 usable)

- `pfs event` / `pfs month` → days. Source-coded, no finer definition published.

#### 4. gse17260 (Yoshihara 2010, GPL6480) — 110 / 76 (110 of 110 usable)

- `recurrence (1)` / `progression-free survival (m)` → days. Source-coded, no finer
  definition published.

#### gse53963 — EXCLUDED from the PFS validation set

- Confirmed: no progression field on either `!Sample_characteristics_ch1` or `_ch2` of the
  series matrix (ch2 keys are `Stage`, `age_at_dx`, `debulking`, `grade`, `morphology`,
  `stage_#`, `substage`, `tcga_sampleid`, `time_fu_months`, `vital_status` — OS-only; ch1
  is `tissue` only).

---

## Counts actually obtained

`python3 agent/scripts/pfs_labels.py all && … verify` (2026-09-21):

**Pool**

| Cohort | n | events | Platform | OS n (for comparison) | dropped (OS→no PFS) |
|---|---:|---:|---|---:|---:|
| tcga-ov-hiseqv2 | 302 | 209 | rnaseq_hiseqv2 | 302 | 0 |
| gse26193 | 79 | 63 | GPL570 | 79 | 0 |
| gse63885 | 47 | 43 | GPL570 | 70 | 23 (dfs=0, non-CR) |
| gse30161 | 44 | 41 | GPL570 | 47 | 3 (relapse=UNKnown) |
| **TOTAL** | **472** | **356** | | 498 (of 751 OS pool) | 26 |
| gse26712 | — | — | — | 185 | excluded cohort (no field) |
| gse14764 | — | — | — | 68 | excluded cohort (no field) |

**Validation**

| Cohort | n | events | Platform | OS n (for comparison) | dropped |
|---|---:|---:|---|---:|---:|
| gse32062 | 260 | 193 | GPL6480 | 260 | 0 |
| gse140082 | 191 | 135 | GPL14951 | 191 | 0 |
| gse49997 | 171 | 108 | GPL2986 | 171 | 0 |
| gse17260 | 110 | 76 | GPL6480 | 110 | 0 |
| **TOTAL** | **732** | **512** | | 732 (of 892 OS validation) | 0 |
| gse53963 | — | — | — | 160 | excluded cohort (no field) |

No `sample_id` collisions within or across the two output files.

---

## Deviations from the brief that shaped this table

The task brief for this extraction assumed GSE30161 would need to be excluded because
censoring times for progression looked underivable from `date.of.relapse` +
`datedx`/`surgdate` alone. On inspection, the raw series matrix already carries a
precomputed `pfi days` field (verified consistent with the raw dates for both events and
censored cases — see above), so the cohort **is** included, using that field directly. This
is the only deviation from the brief's per-cohort expectations; everything else (GSE63885's
derived event flag, GSE26712/GSE14764/GSE53963 exclusions, GSE140082's day-unit
verification) matched the brief's guidance.

---

## Pointers

- OS-side mirror: `docs/os-training-labels.md`, `docs/os-validation-labels.md`
- Split decision: `docs/os-train-validation-split.md`
- CDR provenance: T003, F011
- E004 plan: `research/os-hgsoc/experiments/E004-pfs-pfi-endpoint.md` (`research.py show E004`)
