#!/usr/bin/env python3
"""Compile progression-free-survival (PFS/PFI) label tables for HGSOC.

Mirrors ``os_pool_labels.py`` / ``os_validation_labels.py`` (E003) for the
follow-on PFS endpoint (E004). Stdlib only; reuses their parsing helpers by
importing the modules directly (same directory, no package install needed).

Unlike the OS tables, this script does **not** re-decide cohort inclusion.
The sample sets are taken verbatim from the existing OS tables:

    datasets/ovarian-cancer-prognosis-ml/os-training-pool/labels.csv
    datasets/ovarian-cancer-prognosis-ml/os-validation/labels.csv

For each sample already in those tables, this script looks up a
progression-free time + event in that cohort's raw source and keeps the row
only if it is Cox-usable (finite ``pfs_time_days >= 1``, binary event). Any
OS sample that lacks usable PFS is *reported*, not silently dropped: see the
``dropped`` list in the ``all``/``pool``/``validation`` stderr summary and
``docs/pfs-labels.md``.

    python3 agent/scripts/pfs_labels.py all         # write both labels.csv
    python3 agent/scripts/pfs_labels.py pool        # pool only
    python3 agent/scripts/pfs_labels.py validation  # validation only
    python3 agent/scripts/pfs_labels.py verify      # re-read + assert counts
    python3 agent/scripts/pfs_labels.py gse63885    # one cohort to stdout

Default output:
    datasets/ovarian-cancer-prognosis-ml/pfs-training-pool/labels.csv
    datasets/ovarian-cancer-prognosis-ml/pfs-validation/labels.csv

Schema (column order)
----------------------
cohort, sample_id, geo_accession, platform, histology, age_years,
figo_stage, grade, residual_disease, notes    -- copied verbatim from the
                                                  matching OS-table row
pfs_time_days      follow-up in days (years*365.25, months*365.25/12)
pfs_event          1 = progression/recurrence/relapse (definition varies
                    by cohort, see event_definition), 0 = censored
pfs_time_original  time string as recorded, before conversion
pfs_time_unit      days | months | years
event_definition   verbatim per-cohort description of what counts as an
                    event (see EVENT_DEFINITIONS below and docs/pfs-labels.md)

Cox-usable rows require a finite pfs_time_days >= 1 (same floor as the OS
tables' os_time_days >= 1).

Per-cohort rules, traps, and exclusions
----------------------------------------
POOL (source sample set: os-training-pool/labels.csv)

1. tcga-ov-hiseqv2 (302 of 302 OS samples usable)
   PFI / PFI.time from the PanCanAtlas CDR (T003, F011), joined on the
   12-char bcr_patient_barcode prefix of sample_id. CDR's PFI counts a new
   tumor event (progression/recurrence/metastasis/new primary) *or* death
   with tumor present as an event -- broader than the GEO cohorts' plain
   recurrence flags (see the F0xx heterogeneity finding).

2. gse26193 (79 of 79 usable)
   ``pfs event`` / ``pfs time (years)`` -> days. Source-coded; GEO does not
   publish a finer clinical definition than the field name.

3. gse63885 (47 of 70 OS samples usable; 23 dropped)
   TRAP: the source's own ``dfs - disease-free survival [days]`` field is
   exactly 0 for every one of the 23 patients whose ``clinical status post
   1st line chemotherapy`` was not CR (complete response) -- i.e. DFS is
   defined only from the point of remission, so non-responders get t=0 by
   the source's own convention. Those 23 fail the ``>= 1`` Cox-usable floor
   and are dropped (reported, not silently discarded). Event is *derived*
   (no explicit recurrence-date field exists): ``clinical status at last
   follow-up`` in {AWD, DOD} -> event=1, NED -> event=0.

4. gse30161 (44 of 47 OS samples usable; 3 dropped)
   TRAP: same shifted csv/phenotype.csv as the OS extraction -- reparse
   GSE30161_series_matrix.txt (os_pool_labels.parse_gse30161_matrix). The
   raw matrix already carries a precomputed ``pfi days`` field alongside
   ``relapse(1=yes, 0=no)``; spot-checked against ``datedx``/``surgdate``
   and ``date.of.relapse``/``date.last.follow.up`` and found internally
   consistent (matches datedx-to-relapse for events, surgdate-to-last-
   follow-up for the 3 censored) -- so the precomputed field is used
   directly rather than re-derived from the raw dates. 3/47 serous samples
   have ``relapse`` coded ``UNKnown`` and are dropped.

5. gse26712, gse14764 -- EXCLUDED. Confirmed by header inspection of
   csv/phenotype.csv: neither has any progression/recurrence/relapse/DFS
   field. They drop out of the PFS pool entirely.

VALIDATION (source sample set: os-validation/labels.csv)

1. gse32062 (260 of 260 usable) -- ``rec (1)`` / ``pfs (m)`` -> days.
2. gse140082 (191 of 191 usable) -- ``final_pfsid`` / ``final_pfstm``.
   TRAP checked: final_pfstm is already in DAYS (max 1240 in this subset,
   vs max 1281 for final_ostm; 0/191 rows have pfs > os), not months --
   confirmed by comparing against the OS field before treating it as days.
3. gse49997 (171 of 171 usable) -- ``pfs event`` / ``pfs month`` -> days.
4. gse17260 (110 of 110 usable) -- ``recurrence (1)`` / ``progression-free
   survival (m)`` -> days.
5. gse53963 -- EXCLUDED. Confirmed: no progression field on either
   !Sample_characteristics_ch1 or _ch2 of the series matrix.

References: docs/pfs-labels.md, docs/os-training-labels.md,
docs/os-validation-labels.md, agent/scripts/os_pool_labels.py,
agent/scripts/os_validation_labels.py.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

# Reuse the OS scripts' stdlib-only parsing helpers instead of duplicating
# them (same directory; no package install needed).
from os_pool_labels import (
    clean,
    fmt_float,
    is_serous,
    lookup_char,
    months_to_days,
    parse_float,
    parse_gse30161_matrix,
    read_csv_dicts,
    years_to_days,
)

# ---------------------------------------------------------------------------
# Paths / schema
# ---------------------------------------------------------------------------
WORKSPACE = Path(__file__).resolve().parents[2]
DATA_ROOT = WORKSPACE / "datasets" / "ovarian-cancer-prognosis-ml"

POOL_OS_LABELS = DATA_ROOT / "os-training-pool" / "labels.csv"
VALIDATION_OS_LABELS = DATA_ROOT / "os-validation" / "labels.csv"
CDR_CSV = DATA_ROOT / "tcga-cdr-pancanatlas" / "csv" / "ov_subset.csv"

DEFAULT_OUT_POOL = DATA_ROOT / "pfs-training-pool" / "labels.csv"
DEFAULT_OUT_VALIDATION = DATA_ROOT / "pfs-validation" / "labels.csv"

MIN_PFS_DAYS = 1.0

LABEL_FIELDS = [
    "cohort",
    "sample_id",
    "geo_accession",
    "platform",
    "histology",
    "age_years",
    "figo_stage",
    "grade",
    "residual_disease",
    "notes",
    "pfs_time_days",
    "pfs_event",
    "pfs_time_original",
    "pfs_time_unit",
    "event_definition",
]

COHORT_ORDER_POOL = ["tcga-ov-hiseqv2", "gse26193", "gse63885", "gse30161"]
COHORT_ORDER_VALIDATION = ["gse32062", "gse140082", "gse49997", "gse17260"]

# Disk-verified acceptance targets (n, events). verify() asserts these.
EXPECTED_POOL = {
    "tcga-ov-hiseqv2": (302, 209),
    "gse26193": (79, 63),
    "gse63885": (47, 43),
    "gse30161": (44, 41),
}
EXPECTED_POOL_TOTAL = (472, 356)

EXPECTED_VALIDATION = {
    "gse32062": (260, 193),
    "gse140082": (191, 135),
    "gse49997": (171, 108),
    "gse17260": (110, 76),
}
EXPECTED_VALIDATION_TOTAL = (732, 512)

# Cohorts confirmed to have NO progression field at all; they never appear
# in the output. Kept here so `all` reports them explicitly.
EXCLUDED_POOL = {
    "gse26712": "no progression/recurrence/relapse/DFS field in csv/phenotype.csv (header-checked)",
    "gse14764": "no progression/recurrence/relapse/DFS field in csv/phenotype.csv (header-checked)",
}
EXCLUDED_VALIDATION = {
    "gse53963": "no progression field on !Sample_characteristics_ch1 or _ch2 of the series matrix",
}

EVENT_DEFINITIONS = {
    "tcga-ov-hiseqv2": (
        "TCGA-CDR PFI: new tumour event (progression, locoregional recurrence, "
        "distant metastasis, or new primary) OR death with tumour present, "
        "whichever occurs first; alive-and-tumour-free censored at last contact "
        "(Liu et al. 2018 Cell). Broader than the GEO cohorts below -- counts "
        "death without progression as an event."
    ),
    "gse26193": (
        "source-coded `pfs event` / `pfs time (years)` (Mateescu et al., GSE26193); "
        "GEO publishes no finer clinical definition than the field name."
    ),
    "gse63885": (
        "derived from `clinical status at last follow-up`: event=1 if AWD (alive "
        "with disease) or DOD (dead of disease), 0 if NED (no evidence of disease); "
        "time is the source's own `dfs - disease-free survival [days]` field, which "
        "is 0 for every 1st-line non-CR responder (23/70) and is therefore excluded "
        "by the >=1 day Cox-usable floor, not harmonised."
    ),
    "gse30161": (
        "source-provided `pfi days` + `relapse(1=yes, 0=no)` fields (verified "
        "against datedx/surgdate and date.of.relapse/date.last.follow.up: "
        "consistent for both events and the 3 censored cases). 3/47 serous samples "
        "have `relapse` coded UNKnown and are excluded."
    ),
    "gse32062": (
        "source-coded `rec (1)` / `pfs (m)` (Yoshihara et al. 2012, GSE32062); "
        "GEO publishes no finer clinical definition than the field name."
    ),
    "gse140082": (
        "source-coded `final_pfsid` / `final_pfstm` (ICON7 trial, GSE140082); "
        "trial PFS per RECIST progression or death, whichever occurs first."
    ),
    "gse49997": (
        "source-coded `pfs event` / `pfs month` (Pils et al., GSE49997); GEO "
        "publishes no finer clinical definition than the field name."
    ),
    "gse17260": (
        "source-coded `recurrence (1)` / `progression-free survival (m)` "
        "(Yoshihara et al. 2010, GSE17260); GEO publishes no finer clinical "
        "definition than the field name."
    ),
}


def eprint(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------
def load_reference(path: Path, cohort: str) -> list[dict[str, str]]:
    """Rows of an OS labels.csv restricted to one cohort."""
    if not path.exists():
        raise FileNotFoundError(f"OS reference table not found: {path}")
    _, rows = read_csv_dicts(path)
    return [r for r in rows if r.get("cohort") == cohort]


def build_row(
    ref: dict[str, str],
    *,
    pfs_time_days: float,
    pfs_event: int,
    pfs_time_original: str,
    pfs_time_unit: str,
    event_definition: str,
    notes: str,
) -> dict[str, str]:
    """Combine an OS-table reference row's covariates with new PFS fields."""
    return {
        "cohort": ref["cohort"],
        "sample_id": ref["sample_id"],
        "geo_accession": ref.get("geo_accession", ""),
        "platform": ref.get("platform", ""),
        "histology": ref.get("histology", ""),
        "age_years": ref.get("age_years", ""),
        "figo_stage": ref.get("figo_stage", ""),
        "grade": ref.get("grade", ""),
        "residual_disease": ref.get("residual_disease", ""),
        "notes": notes,
        "pfs_time_days": fmt_float(pfs_time_days),
        "pfs_event": str(int(pfs_event)),
        "pfs_time_original": pfs_time_original,
        "pfs_time_unit": pfs_time_unit,
        "event_definition": event_definition,
    }


def write_labels(path: Path, rows: Sequence[dict[str, str]]) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=LABEL_FIELDS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in LABEL_FIELDS})


def write_labels_fh(fh, rows: Sequence[dict[str, str]]) -> None:
    import csv

    writer = csv.DictWriter(fh, fieldnames=LABEL_FIELDS, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in LABEL_FIELDS})


def count_events(rows: Sequence[dict[str, str]]) -> tuple[int, int]:
    n = len(rows)
    events = sum(1 for r in rows if r.get("pfs_event") == "1")
    return n, events


def summary_table(rows: Sequence[dict[str, str]], cohort_order: Sequence[str], expected: dict, expected_total) -> str:
    by: dict[str, list[dict[str, str]]] = {c: [] for c in cohort_order}
    extra: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        c = row.get("cohort", "")
        if c in by:
            by[c].append(row)
        else:
            extra.setdefault(c, []).append(row)
    lines = [f"{'cohort':<18} {'n':>5} {'events':>7}  platform", "-" * 52]
    for cohort in cohort_order:
        chunk = by[cohort]
        n, e = count_events(chunk)
        plat = chunk[0]["platform"] if chunk else ""
        exp_n, exp_e = expected[cohort]
        flag = "" if (n, e) == (exp_n, exp_e) else f"  (expected {exp_n}/{exp_e})"
        lines.append(f"{cohort:<18} {n:>5} {e:>7}  {plat}{flag}")
    for cohort, chunk in extra.items():
        n, e = count_events(chunk)
        plat = chunk[0]["platform"] if chunk else ""
        lines.append(f"{cohort:<18} {n:>5} {e:>7}  {plat}  (unexpected cohort)")
    n, e = count_events(rows)
    flag = "" if (n, e) == expected_total else f"  (expected {expected_total[0]}/{expected_total[1]})"
    lines.append("-" * 52)
    lines.append(f"{'TOTAL':<18} {n:>5} {e:>7}{flag}")
    return "\n".join(lines)


def dropped_table(dropped: dict[str, list[dict[str, str]]]) -> str:
    lines = []
    for cohort, items in dropped.items():
        if not items:
            continue
        lines.append(f"{cohort}: {len(items)} OS sample(s) with no usable PFS:")
        for d in items:
            lines.append(f"  - {d['sample_id']}: {d['reason']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# POOL extractors
# ---------------------------------------------------------------------------
def extract_tcga(data_root: Path, ref_rows: list[dict[str, str]]):
    cdr_path = data_root / "tcga-cdr-pancanatlas" / "csv" / "ov_subset.csv"
    _, cdr_rows = read_csv_dicts(cdr_path)
    cdr = {clean(r.get("bcr_patient_barcode")): r for r in cdr_rows}
    edef = EVENT_DEFINITIONS["tcga-ov-hiseqv2"]
    out: list[dict[str, str]] = []
    dropped: list[dict[str, str]] = []
    for ref in ref_rows:
        sid = ref["sample_id"]
        barcode = sid[:12]
        c = cdr.get(barcode)
        if c is None:
            dropped.append({"sample_id": sid, "reason": "no CDR row for this barcode"})
            continue
        pfi = clean(c.get("PFI"))
        raw_time = clean(c.get("PFI.time"))
        days = parse_float(raw_time)
        if pfi not in ("0", "1") or days is None or days < MIN_PFS_DAYS:
            dropped.append(
                {"sample_id": sid, "reason": f"CDR PFI={pfi!r} PFI.time={raw_time!r} not Cox-usable"}
            )
            continue
        out.append(
            build_row(
                ref,
                pfs_time_days=days,
                pfs_event=int(pfi),
                pfs_time_original=raw_time,
                pfs_time_unit="days",
                event_definition=edef,
                notes="PFI/PFI.time from PanCanAtlas CDR (T003, F011), joined on 12-char barcode prefix",
            )
        )
    return out, dropped


def extract_gse26193(data_root: Path, ref_rows: list[dict[str, str]]):
    path = data_root / "gse26193-ovarian-expression-series-matrix" / "csv" / "phenotype.csv"
    _, rows = read_csv_dicts(path)
    by_gsm = {clean(r.get("geo_accession")): r for r in rows}
    edef = EVENT_DEFINITIONS["gse26193"]
    out: list[dict[str, str]] = []
    dropped: list[dict[str, str]] = []
    for ref in ref_rows:
        sid = ref["sample_id"]
        r = by_gsm.get(sid)
        if r is None:
            dropped.append({"sample_id": sid, "reason": "GSM not found in phenotype.csv"})
            continue
        event_raw = clean(r.get("pfs event"))
        years = parse_float(r.get("pfs time (years)"))
        if event_raw not in ("0", "1") or years is None:
            dropped.append({"sample_id": sid, "reason": f"pfs event={event_raw!r} pfs time (years)={r.get('pfs time (years)')!r} not usable"})
            continue
        days = years_to_days(years)
        if days < MIN_PFS_DAYS:
            dropped.append({"sample_id": sid, "reason": f"pfs_time_days={days:.2f} < {MIN_PFS_DAYS}"})
            continue
        out.append(
            build_row(
                ref,
                pfs_time_days=days,
                pfs_event=int(event_raw),
                pfs_time_original=clean(r.get("pfs time (years)")),
                pfs_time_unit="years",
                event_definition=edef,
                notes="pfs event coding: 1=progression, 0=censored (as recorded)",
            )
        )
    return out, dropped


def extract_gse63885(data_root: Path, ref_rows: list[dict[str, str]]):
    from os_pool_labels import find_columns, require_column

    path = data_root / "gse63885-ovarian-expression-series-matrix" / "csv" / "phenotype.csv"
    fields, rows = read_csv_dicts(path)
    dfs_col = require_column(fields, "dfs", context="GSE63885 DFS")
    laststatus_col = require_column(fields, "last follow-up", context="GSE63885 status")
    by_gsm = {clean(r.get("geo_accession")): r for r in rows}
    edef = EVENT_DEFINITIONS["gse63885"]
    out: list[dict[str, str]] = []
    dropped: list[dict[str, str]] = []
    for ref in ref_rows:
        sid = ref["sample_id"]
        r = by_gsm.get(sid)
        if r is None:
            dropped.append({"sample_id": sid, "reason": "GSM not found in phenotype.csv"})
            continue
        raw = clean(r.get(dfs_col))
        days = parse_float(raw)
        status = clean(r.get(laststatus_col))
        if days is None or status not in ("DOD", "AWD", "NED"):
            dropped.append({"sample_id": sid, "reason": f"dfs={raw!r} last-follow-up-status={status!r} not usable"})
            continue
        if days < MIN_PFS_DAYS:
            dropped.append(
                {
                    "sample_id": sid,
                    "reason": f"dfs_days={days:.0f} < {MIN_PFS_DAYS} (source sets DFS=0 for non-CR "
                    "1st-line responders; not a Cox-usable time)",
                }
            )
            continue
        event = 1 if status in ("DOD", "AWD") else 0
        out.append(
            build_row(
                ref,
                pfs_time_days=days,
                pfs_event=event,
                pfs_time_original=raw,
                pfs_time_unit="days",
                event_definition=edef,
                notes="dfs days; event derived from last-follow-up status (NED=0, AWD/DOD=1)",
            )
        )
    return out, dropped


def extract_gse30161(data_root: Path, ref_rows: list[dict[str, str]]):
    matrix = data_root / "gse30161-ovarian-expression-series-matrix" / "GSE30161_series_matrix.txt"
    if not matrix.exists():
        gz = matrix.with_suffix(matrix.suffix + ".gz")
        matrix = gz if gz.exists() else matrix
    pairs = dict(parse_gse30161_matrix(matrix))
    edef = EVENT_DEFINITIONS["gse30161"]
    out: list[dict[str, str]] = []
    dropped: list[dict[str, str]] = []
    for ref in ref_rows:
        sid = ref["sample_id"]
        chars = pairs.get(sid)
        if chars is None:
            dropped.append({"sample_id": sid, "reason": "GSM not found in series matrix"})
            continue
        raw_time = lookup_char(chars, "pfi", "days")
        raw_event = clean(chars.get("relapse(1=yes, 0=no)", ""))
        days = parse_float(raw_time)
        if raw_event not in ("0", "1") or days is None:
            dropped.append({"sample_id": sid, "reason": f"pfi days={raw_time!r} relapse={raw_event!r} not usable"})
            continue
        if days < MIN_PFS_DAYS:
            dropped.append({"sample_id": sid, "reason": f"pfs_time_days={days:.0f} < {MIN_PFS_DAYS}"})
            continue
        out.append(
            build_row(
                ref,
                pfs_time_days=days,
                pfs_event=int(raw_event),
                pfs_time_original=raw_time,
                pfs_time_unit="days",
                event_definition=edef,
                notes="reparsed from series matrix (CSV characteristics are shifted, same trap as OS)",
            )
        )
    return out, dropped


POOL_EXTRACTORS = {
    "tcga-ov-hiseqv2": extract_tcga,
    "gse26193": extract_gse26193,
    "gse63885": extract_gse63885,
    "gse30161": extract_gse30161,
}
POOL_CLI_ALIASES = {"tcga": "tcga-ov-hiseqv2", **{k: k for k in POOL_EXTRACTORS}}


# ---------------------------------------------------------------------------
# VALIDATION extractors
# ---------------------------------------------------------------------------
def _months_extractor(cohort: str, rel_path: str, time_col: str, event_col: str):
    edef = EVENT_DEFINITIONS[cohort]

    def _extract(data_root: Path, ref_rows: list[dict[str, str]]):
        path = data_root / rel_path
        _, rows = read_csv_dicts(path)
        by_gsm = {clean(r.get("geo_accession")): r for r in rows}
        out: list[dict[str, str]] = []
        dropped: list[dict[str, str]] = []
        for ref in ref_rows:
            sid = ref["sample_id"]
            r = by_gsm.get(sid)
            if r is None:
                dropped.append({"sample_id": sid, "reason": "GSM not found in phenotype.csv"})
                continue
            event_raw = clean(r.get(event_col))
            months = parse_float(r.get(time_col))
            if event_raw not in ("0", "1") or months is None:
                dropped.append(
                    {"sample_id": sid, "reason": f"{event_col}={event_raw!r} {time_col}={r.get(time_col)!r} not usable"}
                )
                continue
            days = months_to_days(months)
            if days < MIN_PFS_DAYS:
                dropped.append({"sample_id": sid, "reason": f"pfs_time_days={days:.2f} < {MIN_PFS_DAYS}"})
                continue
            out.append(
                build_row(
                    ref,
                    pfs_time_days=days,
                    pfs_event=int(event_raw),
                    pfs_time_original=clean(r.get(time_col)),
                    pfs_time_unit="months",
                    event_definition=edef,
                    notes=f"`{event_col}`/`{time_col}` as recorded",
                )
            )
        return out, dropped

    return _extract


def extract_gse140082(data_root: Path, ref_rows: list[dict[str, str]]):
    path = data_root / "gse140082-ovarian-expression-series-matrix" / "csv" / "phenotype.csv"
    _, rows = read_csv_dicts(path)
    by_gsm = {clean(r.get("geo_accession")): r for r in rows}
    edef = EVENT_DEFINITIONS["gse140082"]
    out: list[dict[str, str]] = []
    dropped: list[dict[str, str]] = []
    for ref in ref_rows:
        sid = ref["sample_id"]
        r = by_gsm.get(sid)
        if r is None:
            dropped.append({"sample_id": sid, "reason": "GSM not found in phenotype.csv"})
            continue
        event_raw = clean(r.get("final_pfsid"))
        raw_time = clean(r.get("final_pfstm"))
        days = parse_float(raw_time)
        if event_raw not in ("0", "1") or days is None:
            dropped.append({"sample_id": sid, "reason": f"final_pfsid={event_raw!r} final_pfstm={raw_time!r} not usable"})
            continue
        if days < MIN_PFS_DAYS:
            dropped.append({"sample_id": sid, "reason": f"pfs_time_days={days:.0f} < {MIN_PFS_DAYS}"})
            continue
        out.append(
            build_row(
                ref,
                pfs_time_days=days,
                pfs_event=int(event_raw),
                pfs_time_original=raw_time,
                pfs_time_unit="days",
                event_definition=edef,
                notes="final_pfstm confirmed in days (checked pfs<=os for all 191, max 1240 vs os max 1281)",
            )
        )
    return out, dropped


VALIDATION_EXTRACTORS = {
    "gse32062": _months_extractor(
        "gse32062", "gse32062-gpl6480-ovarian-expression-series-matrix/csv/phenotype.csv", "pfs (m)", "rec (1)"
    ),
    "gse140082": extract_gse140082,
    "gse49997": _months_extractor(
        "gse49997", "gse49997-ovarian-expression-series-matrix/csv/phenotype.csv", "pfs month", "pfs event"
    ),
    "gse17260": _months_extractor(
        "gse17260",
        "gse17260-ovarian-expression-series-matrix/csv/phenotype.csv",
        "progression-free survival (m)",
        "recurrence (1)",
    ),
}
VALIDATION_CLI_ALIASES = {k: k for k in VALIDATION_EXTRACTORS}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def extract_all_pool(data_root: Path):
    rows: list[dict[str, str]] = []
    dropped_by_cohort: dict[str, list[dict[str, str]]] = {}
    for slug in COHORT_ORDER_POOL:
        ref_rows = load_reference(POOL_OS_LABELS, slug)
        chunk, dropped = POOL_EXTRACTORS[slug](data_root, ref_rows)
        dropped_by_cohort[slug] = dropped
        n, e = count_events(chunk)
        exp_n, exp_e = EXPECTED_POOL[slug]
        note = "" if (n, e) == (exp_n, exp_e) else f" (expected {exp_n}/{exp_e})"
        eprint(f"{slug}: {n} patients / {e} events, {len(dropped)} OS sample(s) dropped{note}")
        rows.extend(chunk)
    for slug, reason in EXCLUDED_POOL.items():
        eprint(f"{slug}: EXCLUDED -- {reason}")
    return rows, dropped_by_cohort


def extract_all_validation(data_root: Path):
    rows: list[dict[str, str]] = []
    dropped_by_cohort: dict[str, list[dict[str, str]]] = {}
    for slug in COHORT_ORDER_VALIDATION:
        ref_rows = load_reference(VALIDATION_OS_LABELS, slug)
        chunk, dropped = VALIDATION_EXTRACTORS[slug](data_root, ref_rows)
        dropped_by_cohort[slug] = dropped
        n, e = count_events(chunk)
        exp_n, exp_e = EXPECTED_VALIDATION[slug]
        note = "" if (n, e) == (exp_n, exp_e) else f" (expected {exp_n}/{exp_e})"
        eprint(f"{slug}: {n} patients / {e} events, {len(dropped)} OS sample(s) dropped{note}")
        rows.extend(chunk)
    for slug, reason in EXCLUDED_VALIDATION.items():
        eprint(f"{slug}: EXCLUDED -- {reason}")
    return rows, dropped_by_cohort


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------
def _verify_one(
    path: Path,
    cohort_order: Sequence[str],
    expected: dict,
    expected_total,
    valid_platforms: set[str],
) -> tuple[int, list[str], list[dict[str, str]]]:
    if not path.exists():
        eprint(f"FAIL: {path} does not exist")
        return 1, [], []
    fields, rows = read_csv_dicts(path)
    errors: list[str] = []
    missing = [c for c in LABEL_FIELDS if c not in fields]
    if missing:
        errors.append(f"missing columns: {missing}")

    print(summary_table(rows, cohort_order, expected, expected_total))
    print()

    by: dict[str, list[dict[str, str]]] = {c: [] for c in cohort_order}
    unknown: list[str] = []
    for i, row in enumerate(rows, start=2):
        c = row.get("cohort", "")
        if c in by:
            by[c].append(row)
        else:
            unknown.append(c)

        event = clean(row.get("pfs_event"))
        if event not in {"0", "1"}:
            errors.append(f"line {i}: pfs_event={event!r} not in {{0,1}}")
        days = parse_float(row.get("pfs_time_days"))
        if days is None:
            errors.append(f"line {i}: non-numeric pfs_time_days={row.get('pfs_time_days')!r}")
        elif days < MIN_PFS_DAYS:
            errors.append(f"line {i} {row.get('sample_id')}: pfs_time_days={days} < {MIN_PFS_DAYS}")
        unit = clean(row.get("pfs_time_unit"))
        if unit not in {"days", "months", "years"}:
            errors.append(f"line {i}: bad pfs_time_unit={unit!r}")
        if not clean(row.get("event_definition")):
            errors.append(f"line {i}: empty event_definition")
        plat = clean(row.get("platform"))
        if valid_platforms and plat not in valid_platforms:
            errors.append(f"line {i}: unexpected platform={plat!r}")

    if unknown:
        errors.append(f"unexpected cohort values: {sorted(set(unknown))}")

    for slug in cohort_order:
        edefs = {clean(r.get("event_definition")) for r in by[slug]}
        if len(edefs) > 1:
            errors.append(f"{slug}: inconsistent event_definition values: {edefs}")

    seen: dict[str, str] = {}
    dups: list[str] = []
    for row in rows:
        sid = row.get("sample_id", "")
        if not sid:
            errors.append("empty sample_id")
            continue
        if sid in seen:
            dups.append(f"{sid} ({seen[sid]} and {row.get('cohort')})")
        else:
            seen[sid] = row.get("cohort", "")
    if dups:
        errors.append(f"{len(dups)} duplicate sample_id(s): {dups[:8]}")

    for slug, (exp_n, exp_e) in expected.items():
        n, e = count_events(by[slug])
        if (n, e) != (exp_n, exp_e):
            errors.append(f"{slug}: got {n}/{e} patients/events, expected {exp_n}/{exp_e}")

    n, e = count_events(rows)
    if (n, e) != expected_total:
        errors.append(f"TOTAL: got {n}/{e} patients/events, expected {expected_total[0]}/{expected_total[1]}")

    return (1 if errors else 0), errors, rows


def verify_labels(out_pool: Path, out_validation: Path) -> int:
    rc_pool, errors_pool, pool_rows = _verify_one(
        out_pool, COHORT_ORDER_POOL, EXPECTED_POOL, EXPECTED_POOL_TOTAL, set()
    )
    print()
    rc_val, errors_val, val_rows = _verify_one(
        out_validation, COHORT_ORDER_VALIDATION, EXPECTED_VALIDATION, EXPECTED_VALIDATION_TOTAL, set()
    )

    errors = list(errors_pool) + list(errors_val)

    # Cross-table leakage check, mirroring os_validation_labels.py.
    pool_ids = {clean(r.get("sample_id")) for r in pool_rows}
    val_ids = {clean(r.get("sample_id")) for r in val_rows}
    overlap = sorted(pool_ids & val_ids)
    if overlap:
        errors.append(f"{len(overlap)} sample_id(s) in both pfs-training-pool and pfs-validation: {overlap[:8]}")

    # Subset check: every pfs sample_id must also be an OS sample_id in the
    # matching table (no invented rows).
    if POOL_OS_LABELS.exists():
        _, os_pool_rows = read_csv_dicts(POOL_OS_LABELS)
        os_pool_ids = {clean(r.get("sample_id")) for r in os_pool_rows}
        stray = sorted(pool_ids - os_pool_ids)
        if stray:
            errors.append(f"{len(stray)} pfs-training-pool sample_id(s) not present in os-training-pool: {stray[:8]}")
    if VALIDATION_OS_LABELS.exists():
        _, os_val_rows = read_csv_dicts(VALIDATION_OS_LABELS)
        os_val_ids = {clean(r.get("sample_id")) for r in os_val_rows}
        stray = sorted(val_ids - os_val_ids)
        if stray:
            errors.append(f"{len(stray)} pfs-validation sample_id(s) not present in os-validation: {stray[:8]}")

    if errors:
        eprint(f"FAIL: {len(errors)} check(s)")
        for msg in errors:
            eprint("  -", msg)
        return 1
    print("OK: counts, uniqueness, times, event coding, event_definition consistency, "
          "and pool/validation disjointness all pass.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract standardized PFS/PFI labels for the HGSOC pool + validation cohorts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "subcommands:\n"
            "  all         extract everything, write both labels.csv\n"
            "  pool        extract the 4 pool cohorts, write pfs-training-pool/labels.csv\n"
            "  validation  extract the 4 validation cohorts, write pfs-validation/labels.csv\n"
            "  verify      re-read both labels.csv and assert expected n/events + checks\n"
            "  tcga | gse26193 | gse63885 | gse30161            (pool cohort to stdout)\n"
            "  gse32062 | gse140082 | gse49997 | gse17260        (validation cohort to stdout)\n"
        ),
    )
    parser.add_argument("--data-root", type=Path, default=DATA_ROOT)
    parser.add_argument("--out-pool", type=Path, default=DEFAULT_OUT_POOL)
    parser.add_argument("--out-validation", type=Path, default=DEFAULT_OUT_VALIDATION)
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("all")
    sub.add_parser("pool")
    sub.add_parser("validation")
    sub.add_parser("verify")
    for name in list(POOL_CLI_ALIASES) + list(VALIDATION_CLI_ALIASES):
        sub.add_parser(name)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cmd = args.cmd or "all"
    data_root: Path = args.data_root
    out_pool: Path = args.out_pool
    out_validation: Path = args.out_validation

    if cmd == "verify":
        return verify_labels(out_pool, out_validation)

    if cmd in ("all", "pool"):
        pool_rows, pool_dropped = extract_all_pool(data_root)
        write_labels(out_pool, pool_rows)
        eprint()
        eprint(summary_table(pool_rows, COHORT_ORDER_POOL, EXPECTED_POOL, EXPECTED_POOL_TOTAL))
        dt = dropped_table(pool_dropped)
        if dt:
            eprint()
            eprint(dt)
        eprint(f"\nwrote {out_pool} ({len(pool_rows)} rows)")

    if cmd in ("all", "validation"):
        val_rows, val_dropped = extract_all_validation(data_root)
        write_labels(out_validation, val_rows)
        eprint()
        eprint(summary_table(val_rows, COHORT_ORDER_VALIDATION, EXPECTED_VALIDATION, EXPECTED_VALIDATION_TOTAL))
        dt = dropped_table(val_dropped)
        if dt:
            eprint()
            eprint(dt)
        eprint(f"\nwrote {out_validation} ({len(val_rows)} rows)")

    if cmd in ("all", "pool", "validation"):
        return 0

    if cmd in POOL_CLI_ALIASES:
        slug = POOL_CLI_ALIASES[cmd]
        ref_rows = load_reference(POOL_OS_LABELS, slug)
        rows, dropped = POOL_EXTRACTORS[slug](data_root, ref_rows)
        write_labels_fh(sys.stdout, rows)
        n, e = count_events(rows)
        exp = EXPECTED_POOL[slug]
        eprint(f"{slug}: {n} patients / {e} events (expected {exp[0]}/{exp[1]}), {len(dropped)} dropped")
        return 0

    if cmd in VALIDATION_CLI_ALIASES:
        slug = VALIDATION_CLI_ALIASES[cmd]
        ref_rows = load_reference(VALIDATION_OS_LABELS, slug)
        rows, dropped = VALIDATION_EXTRACTORS[slug](data_root, ref_rows)
        write_labels_fh(sys.stdout, rows)
        n, e = count_events(rows)
        exp = EXPECTED_VALIDATION[slug]
        eprint(f"{slug}: {n} patients / {e} events (expected {exp[0]}/{exp[1]}), {len(dropped)} dropped")
        return 0

    eprint(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
