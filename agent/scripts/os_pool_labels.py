#!/usr/bin/env python3
"""Compile the overall-survival (OS) training-label table for HGSOC.

One row per patient/sample in the RNA-seq + Affymetrix training pool
(docs/os-train-validation-split.md). Stdlib only.

Pipeline
--------
For each of the six training-pool cohorts, read phenotype (and, for TCGA,
the HiSeqV2 sample list; for GSE30161, the raw GEO series matrix), apply
the cohort-specific inclusion rules below, convert follow-up time to days,
and emit a standardized row. ``all`` concatenates the six tables in the
order listed here and writes ``labels.csv``. ``verify`` re-reads that file
and checks per-cohort n/deaths, uniqueness, time, and event coding.

    python3 agent/scripts/os_pool_labels.py all
    python3 agent/scripts/os_pool_labels.py verify
    python3 agent/scripts/os_pool_labels.py gse30161   # one cohort to stdout

Default output:
    datasets/ovarian-cancer-prognosis-ml/os-training-pool/labels.csv

Schema (column order)
---------------------
cohort            short slug (see COHORT_ORDER)
sample_id         TCGA barcode or GEO GSM accession
geo_accession     GSM id; empty for TCGA
platform          rnaseq_hiseqv2 | GPL96 | GPL570
histology         as recorded in the source (not recoded)
os_time_days      follow-up in days (float; years*365.25, months*365.25/12)
os_event          1 = death, 0 = censored
os_time_original  time string as recorded (before unit conversion)
os_time_unit      days | months | years
event_definition  all_cause | dod_dss_flavored
age_years         empty if the cohort has no age field
figo_stage, grade, residual_disease   as recorded; empty if missing
notes             per-row extraction remarks (event flavour, chemoresponse, …)

Time conversion uses the Gregorian average year 365.25 days so that
year- and month-coded cohorts are on the same scale as day-coded ones.
Cox-usable rows require a finite os_time_days >= 1.

Per-cohort rules and traps
--------------------------
1. tcga-ov-hiseqv2  (expect 302 / 182 deaths)
   Expression sample list = header of HiSeqV2.csv (308 barcodes).
   Clinical = OV_clinicalMatrix.csv. Keep sample_type == "Primary Tumor"
   (drops 5 recurrent tumors that are on the expression matrix). Require
   vital_status in {LIVING, DECEASED} and a time: days_to_death if
   DECEASED else days_to_last_followup. Exactly one primary
   (TCGA-04-1357-01) has vital status but no time and is dropped → 302.
   Intersect with HiSeqV2 barcodes. event_definition=all_cause.
   Histology is serous by construction (Xena histological_type is
   "Serous Cystadenocarcinoma").

2. gse26712  Bonome, GPL96  (expect 185 / 129)
   TRAP: column ``status_2`` is GEO's public-on date — ignore it. The
   vital field is ``status``: DOD* = event, AWD* + NED* = censored.
   Time = ``survival years`` → days (*365.25). Drop the 10 HOSE normal
   controls (tissue / source_name_ch1 / title). Residual =
   ``surgery outcome``. No age/stage/grade. event_definition=
   dod_dss_flavored (DOD is disease-specific, not all-cause).

3. gse63885  Lisowska, GPL570  (expect 70 serous / 62)
   Phenotype CSV headers contain colons, parenthetical legends, and a
   comma inside the platinum-sensitivity key that splits that header
   into extra columns (Appendix B). Match OS / status / histology /
   grade / residual by substring, never by exact header equality, and
   never use GEO's ``status`` (public-on date). Subset histotype to
   serous (~73), then drop rows whose OS-days field is NA (~3) → 70.
   DOD=event, AWD/NED=censored. event_definition=dod_dss_flavored.

4. gse26193  Mateescu, GPL570  (expect 79 serous / 60)
   Subset ``histological type`` == serous (case-insensitive). Time =
   ``os time (years)`` → days. ``os event`` is coded 1=death, 0=censored
   (confirmed against the phenotype CSV). No age, no residual.
   event_definition=all_cause (binary OS, not DOD-labelled).

5. gse30161  Ferriss, GPL570 FFPE  (expect 47 serous / 33)
   TRAP: csv/phenotype.csv is column-shifted on characteristics_1..13.
   Do not use those columns. Reparse GSE30161_series_matrix.txt:
   !Sample_geo_accession gives column order; each
   !Sample_characteristics_ch1 cell is ``key : value`` *per sample*
   because keys are not in the same order across samples (Appendix B).
   Subset histo/histology == serous. OS = "overall survival days";
   event = "censoring(dead=1, alive=0)" (whitespace/newlines in the
   key are normalized). Residual = ``optimal``. Chemoresponse goes in
   notes. event_definition=all_cause.

6. gse14764  Denkert, GPL96  (expect 68 serous / 19)
   Subset ``histological type`` containing "serous". Time =
   ``overall survival time`` in MONTHS → days. ``overall survival
   event`` is 1=death, 0=censored. Residual = ``residual tumor``
   (0/1/NA as recorded). event_definition=all_cause.

If a cohort's real count differs from the expect-numbers above after
careful parsing, this script emits what it finds. ``verify`` then fails
against the split-doc targets so the discrepancy is visible; it does
not silently fudge rows. Small gaps vs the doc are possible — that
doc itself notes some figures were estimates.

References: docs/os-train-validation-split.md,
docs/ovarian-cancer-prognosis-opportunities.md Appendix B.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import re
import sys
from pathlib import Path
from typing import Sequence

# ---------------------------------------------------------------------------
# Paths / schema / expected counts
# ---------------------------------------------------------------------------
WORKSPACE = Path(__file__).resolve().parents[2]
DATA_ROOT = WORKSPACE / "datasets" / "ovarian-cancer-prognosis-ml"
DEFAULT_OUT = DATA_ROOT / "os-training-pool" / "labels.csv"

DAYS_PER_YEAR = 365.25
DAYS_PER_MONTH = DAYS_PER_YEAR / 12.0
MIN_OS_DAYS = 1.0

LABEL_FIELDS = [
    "cohort",
    "sample_id",
    "geo_accession",
    "platform",
    "histology",
    "os_time_days",
    "os_event",
    "os_time_original",
    "os_time_unit",
    "event_definition",
    "age_years",
    "figo_stage",
    "grade",
    "residual_disease",
    "notes",
]

# Split-doc acceptance targets (n, deaths). verify() asserts these.
EXPECTED = {
    "tcga-ov-hiseqv2": (302, 182),
    "gse26712": (185, 129),
    "gse63885": (70, 62),
    "gse26193": (79, 60),
    "gse30161": (47, 33),
    "gse14764": (68, 19),
}
EXPECTED_TOTAL = (751, 485)
COHORT_ORDER = list(EXPECTED.keys())

# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------
_NA = frozenset({"", "na", "nan", "n/a", "none", ".", "null", "unknown"})


def eprint(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)


def _open_text(path: Path):
    """Text handle; transparently gunzip ``*.gz``."""
    name = path.name.lower()
    if name.endswith(".gz"):
        return io.TextIOWrapper(
            gzip.open(path, "rb"), encoding="utf-8", errors="replace", newline=""
        )
    return open(path, encoding="utf-8", errors="replace", newline="")


def read_csv_dicts(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with _open_text(path) as fh:
        reader = csv.DictReader(fh)
        fields = list(reader.fieldnames or [])
        rows = [{k: (v if v is not None else "") for k, v in row.items()} for row in reader]
    return fields, rows


def csv_header_cells(path: Path) -> list[str]:
    """First row only — used for the wide HiSeqV2 expression matrix."""
    with _open_text(path) as fh:
        return next(csv.reader(fh))


def clean(value: object) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if s.lower() in _NA:
        return ""
    return s


def parse_float(value: object) -> float | None:
    s = clean(value)
    if not s:
        return None
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def fmt_float(value: float | None) -> str:
    if value is None:
        return ""
    s = f"{value:.6f}".rstrip("0").rstrip(".")
    return s if s else "0"


def years_to_days(years: float) -> float:
    return years * DAYS_PER_YEAR


def months_to_days(months: float) -> float:
    return months * DAYS_PER_MONTH


def is_serous(text: str) -> bool:
    """True if a histotype string denotes serous (not mixed-in passing)."""
    t = clean(text).lower()
    if not t:
        return False
    return "serous" in t


def find_columns(fieldnames: Sequence[str], *needles: str) -> list[str]:
    """Headers whose lowercase name contains every needle (substring match)."""
    want = [n.lower() for n in needles]
    hits = []
    for name in fieldnames:
        low = (name or "").lower()
        if all(n in low for n in want):
            hits.append(name)
    return hits


def require_column(fieldnames: Sequence[str], *needles: str, context: str = "") -> str:
    hits = find_columns(fieldnames, *needles)
    if len(hits) != 1:
        where = f" ({context})" if context else ""
        raise RuntimeError(
            f"expected exactly 1 column matching {needles!r}{where}, "
            f"got {len(hits)}: {hits!r}"
        )
    return hits[0]


def lookup_char(chars: dict[str, str], *needles: str) -> str:
    """First GSE30161 characteristic whose normalized key contains all needles."""
    want = [n.lower() for n in needles]
    for key, val in chars.items():
        low = key.lower()
        if all(n in low for n in want):
            return val
    return ""


def make_row(
    *,
    cohort: str,
    sample_id: str,
    geo_accession: str,
    platform: str,
    histology: str,
    os_time_days: float,
    os_event: int,
    os_time_original: str,
    os_time_unit: str,
    event_definition: str,
    age_years: str = "",
    figo_stage: str = "",
    grade: str = "",
    residual_disease: str = "",
    notes: str = "",
) -> dict[str, str]:
    return {
        "cohort": cohort,
        "sample_id": sample_id,
        "geo_accession": geo_accession,
        "platform": platform,
        "histology": histology,
        "os_time_days": fmt_float(os_time_days),
        "os_event": str(int(os_event)),
        "os_time_original": os_time_original,
        "os_time_unit": os_time_unit,
        "event_definition": event_definition,
        "age_years": clean(age_years),
        "figo_stage": clean(figo_stage),
        "grade": clean(grade),
        "residual_disease": clean(residual_disease),
        "notes": notes,
    }


def write_labels(path: Path, rows: Sequence[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=LABEL_FIELDS, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in LABEL_FIELDS})


def write_labels_fh(fh, rows: Sequence[dict[str, str]]) -> None:
    writer = csv.DictWriter(
        fh, fieldnames=LABEL_FIELDS, extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in LABEL_FIELDS})


def count_deaths(rows: Sequence[dict[str, str]]) -> tuple[int, int]:
    n = len(rows)
    deaths = sum(1 for r in rows if r.get("os_event") == "1")
    return n, deaths


def summary_table(rows: Sequence[dict[str, str]]) -> str:
    by: dict[str, list[dict[str, str]]] = {c: [] for c in COHORT_ORDER}
    extra: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        c = row.get("cohort", "")
        if c in by:
            by[c].append(row)
        else:
            extra.setdefault(c, []).append(row)
    lines = [
        f"{'cohort':<18} {'n':>5} {'deaths':>7}  platform",
        "-" * 52,
    ]
    for cohort in COHORT_ORDER:
        chunk = by[cohort]
        n, d = count_deaths(chunk)
        plat = chunk[0]["platform"] if chunk else ""
        exp_n, exp_d = EXPECTED[cohort]
        flag = "" if (n, d) == (exp_n, exp_d) else f"  (expected {exp_n}/{exp_d})"
        lines.append(f"{cohort:<18} {n:>5} {d:>7}  {plat}{flag}")
    for cohort, chunk in extra.items():
        n, d = count_deaths(chunk)
        plat = chunk[0]["platform"] if chunk else ""
        lines.append(f"{cohort:<18} {n:>5} {d:>7}  {plat}  (unexpected cohort)")
    n, d = count_deaths(rows)
    flag = "" if (n, d) == EXPECTED_TOTAL else f"  (expected {EXPECTED_TOTAL[0]}/{EXPECTED_TOTAL[1]})"
    lines.append("-" * 52)
    lines.append(f"{'TOTAL':<18} {n:>5} {d:>7}{flag}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 1. TCGA-OV HiSeqV2
# ---------------------------------------------------------------------------
def extract_tcga(data_root: Path) -> list[dict[str, str]]:
    expr_csv = data_root / "tcga-ov-xena-rna-seq-hiseqv2" / "csv" / "HiSeqV2.csv"
    clin_csv = data_root / "tcga-ov-xena-clinical-matrix" / "csv" / "OV_clinicalMatrix.csv"
    header = csv_header_cells(expr_csv)
    # First cell is the gene/sample index column; the rest are barcodes.
    expr_ids = {cell.strip() for cell in header[1:] if cell.strip()}
    _, clin_rows = read_csv_dicts(clin_csv)

    out: list[dict[str, str]] = []
    for row in clin_rows:
        sample_id = clean(row.get("sampleID"))
        if sample_id not in expr_ids:
            continue
        if clean(row.get("sample_type")) != "Primary Tumor":
            continue
        vital = clean(row.get("vital_status")).upper()
        if vital == "DECEASED":
            raw = clean(row.get("days_to_death"))
            event = 1
        elif vital == "LIVING":
            raw = clean(row.get("days_to_last_followup"))
            event = 0
        else:
            continue
        days = parse_float(raw)
        if days is None or days < MIN_OS_DAYS:
            continue
        histo = clean(row.get("histological_type")) or "serous"
        out.append(
            make_row(
                cohort="tcga-ov-hiseqv2",
                sample_id=sample_id,
                geo_accession="",
                platform="rnaseq_hiseqv2",
                histology=histo,
                os_time_days=days,
                os_event=event,
                os_time_original=raw,
                os_time_unit="days",
                event_definition="all_cause",
                age_years=clean(row.get("age_at_initial_pathologic_diagnosis")),
                figo_stage=clean(row.get("clinical_stage")),
                grade=clean(row.get("neoplasm_histologic_grade")),
                residual_disease=clean(row.get("tumor_residual_disease")),
                notes="xena_os; primary_tumor",
            )
        )
    return out


# ---------------------------------------------------------------------------
# 2. GSE26712 (Bonome)
# ---------------------------------------------------------------------------
def _is_hose_control(row: dict[str, str]) -> bool:
    tissue = clean(row.get("tissue")).lower()
    source = clean(row.get("source_name_ch1")).lower()
    title = clean(row.get("title")).lower()
    if "normal ovarian surface" in tissue or tissue.startswith("normal"):
        return True
    if "surface epithelial" in source:
        return True
    if title.startswith("normal hose") or title.startswith("normal "):
        return True
    return False


def _map_dod_status(raw: str) -> int | None:
    """DOD → 1, AWD/NED → 0, anything else → None (drop)."""
    s = clean(raw).upper()
    if not s:
        return None
    token = s.split()[0].split("(")[0]
    if token == "DOD":
        return 1
    if token in {"AWD", "NED"}:
        return 0
    return None


def extract_gse26712(data_root: Path) -> list[dict[str, str]]:
    path = data_root / "gse26712-ovarian-expression-series-matrix" / "csv" / "phenotype.csv"
    _, rows = read_csv_dicts(path)
    out: list[dict[str, str]] = []
    for row in rows:
        if _is_hose_control(row):
            continue
        event = _map_dod_status(row.get("status", ""))
        years = parse_float(row.get("survival years"))
        if event is None or years is None:
            continue
        days = years_to_days(years)
        if days < MIN_OS_DAYS:
            continue
        gsm = clean(row.get("geo_accession"))
        histo = clean(row.get("tissue")) or "Late-stage high-grade ovarian cancer"
        out.append(
            make_row(
                cohort="gse26712",
                sample_id=gsm,
                geo_accession=gsm,
                platform="GPL96",
                histology=histo,
                os_time_days=days,
                os_event=event,
                os_time_original=clean(row.get("survival years")),
                os_time_unit="years",
                event_definition="dod_dss_flavored",
                residual_disease=clean(row.get("surgery outcome")),
                notes="ignored status_2 (GEO public-on date); DOD is DSS-flavored",
            )
        )
    return out


# ---------------------------------------------------------------------------
# 3. GSE63885 (Lisowska)
# ---------------------------------------------------------------------------
def extract_gse63885(data_root: Path) -> list[dict[str, str]]:
    path = data_root / "gse63885-ovarian-expression-series-matrix" / "csv" / "phenotype.csv"
    fields, rows = read_csv_dicts(path)
    histo_col = require_column(fields, "histophatological", context="GSE63885")
    # Do not use GEO ``status``. OS time and last-status live in the long
    # characteristic headers; the platinum key is comma-split (Appendix B)
    # but OS-days / last-status values stay in their own columns.
    os_col = require_column(fields, "overall survival", context="GSE63885 OS")
    status_col = require_column(fields, "last follow-up", context="GSE63885 status")
    grade_hits = find_columns(fields, "tumor grade")
    resid_hits = find_columns(fields, "residual tumor")
    figo_hits = find_columns(fields, "figo")
    grade_col = grade_hits[0] if grade_hits else ""
    resid_col = resid_hits[0] if resid_hits else ""
    figo_col = figo_hits[0] if figo_hits else ""

    out: list[dict[str, str]] = []
    for row in rows:
        histo = clean(row.get(histo_col))
        if not is_serous(histo):
            continue
        event = _map_dod_status(row.get(status_col, ""))
        raw = clean(row.get(os_col))
        days = parse_float(raw)
        if event is None or days is None or days < MIN_OS_DAYS:
            continue
        gsm = clean(row.get("geo_accession"))
        out.append(
            make_row(
                cohort="gse63885",
                sample_id=gsm,
                geo_accession=gsm,
                platform="GPL570",
                histology=histo,
                os_time_days=days,
                os_event=event,
                os_time_original=raw,
                os_time_unit="days",
                event_definition="dod_dss_flavored",
                figo_stage=clean(row.get(figo_col, "")),
                grade=clean(row.get(grade_col, "")),
                residual_disease=clean(row.get(resid_col, "")),
                notes="DOD/AWD/NED last-status (DSS-flavored); platinum header is comma-split",
            )
        )
    return out


# ---------------------------------------------------------------------------
# 4. GSE26193 (Mateescu)
# ---------------------------------------------------------------------------
def _map_binary_event(raw: str, *, one_means_death: bool = True) -> int | None:
    s = clean(raw).lower()
    if not s:
        return None
    if s in {"1", "dead", "deceased", "death", "d", "true", "yes"}:
        return 1 if one_means_death else 0
    if s in {"0", "alive", "living", "censored", "censor", "a", "false", "no"}:
        return 0 if one_means_death else 1
    return None


def extract_gse26193(data_root: Path) -> list[dict[str, str]]:
    path = data_root / "gse26193-ovarian-expression-series-matrix" / "csv" / "phenotype.csv"
    _, rows = read_csv_dicts(path)
    out: list[dict[str, str]] = []
    for row in rows:
        histo = clean(row.get("histological type"))
        if not is_serous(histo):
            continue
        event = _map_binary_event(row.get("os event", ""))
        years = parse_float(row.get("os time (years)"))
        if event is None or years is None:
            continue
        days = years_to_days(years)
        if days < MIN_OS_DAYS:
            continue
        gsm = clean(row.get("geo_accession"))
        out.append(
            make_row(
                cohort="gse26193",
                sample_id=gsm,
                geo_accession=gsm,
                platform="GPL570",
                histology=histo,
                os_time_days=days,
                os_event=event,
                os_time_original=clean(row.get("os time (years)")),
                os_time_unit="years",
                event_definition="all_cause",
                figo_stage=clean(row.get("Stage")),
                grade=clean(row.get("grade")),
                notes="os event coding: 1=death, 0=censored",
            )
        )
    return out


# ---------------------------------------------------------------------------
# 5. GSE30161 (Ferriss) — reparse series matrix, ignore shifted CSV
# ---------------------------------------------------------------------------
def _norm_char_key(key: str) -> str:
    key = key.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", key).strip()


def parse_gse30161_matrix(path: Path) -> list[tuple[str, dict[str, str]]]:
    """Per-sample dicts from !Sample_characteristics_ch1 ``key : value`` cells.

    Keys are not aligned across samples (Appendix B / split-doc trap). Each
    cell is split on the first colon after whitespace normalization, then
    stored under the normalized key for that sample only.
    """
    accessions: list[str] | None = None
    per_sample: list[dict[str, str]] | None = None
    with _open_text(path) as fh:
        for line in fh:
            if line.startswith("!series_matrix_table_begin"):
                break
            if not line.startswith("!"):
                continue
            row = next(csv.reader([line], delimiter="\t"))
            tag = row[0]
            cells = row[1:]
            if tag == "!Sample_geo_accession":
                accessions = [clean(c) for c in cells]
                per_sample = [{} for _ in accessions]
            elif tag == "!Sample_characteristics_ch1" and per_sample is not None:
                for i, cell in enumerate(cells):
                    if i >= len(per_sample):
                        break
                    cell = (cell or "").strip()
                    if not cell or ":" not in cell:
                        continue
                    key, _, val = cell.partition(":")
                    key = _norm_char_key(key)
                    if not key:
                        continue
                    per_sample[i][key] = val.strip()
    if not accessions or per_sample is None:
        raise RuntimeError(f"no !Sample_geo_accession in {path}")
    return list(zip(accessions, per_sample))


def extract_gse30161(data_root: Path) -> list[dict[str, str]]:
    matrix = data_root / "gse30161-ovarian-expression-series-matrix" / "GSE30161_series_matrix.txt"
    if not matrix.exists():
        gz = matrix.with_suffix(matrix.suffix + ".gz")
        if gz.exists():
            matrix = gz
        else:
            raise FileNotFoundError(matrix)
    out: list[dict[str, str]] = []
    for gsm, chars in parse_gse30161_matrix(matrix):
        histo = lookup_char(chars, "histo")
        # ``histo`` matches first; reject non-serous (Clear/Undiff/…)
        if not histo:
            histo = lookup_char(chars, "histology")
        if not is_serous(histo):
            continue
        raw_time = lookup_char(chars, "overall survival")
        raw_event = lookup_char(chars, "censor")
        days = parse_float(raw_time)
        event = _map_binary_event(raw_event)
        if event is None or days is None or days < MIN_OS_DAYS:
            continue
        chemo = clean(lookup_char(chars, "chemoresponse"))
        notes = "reparsed from series matrix (CSV characteristics are shifted)"
        if chemo:
            notes += f"; chemoresponse={chemo}"
        out.append(
            make_row(
                cohort="gse30161",
                sample_id=gsm,
                geo_accession=gsm,
                platform="GPL570",
                histology=histo,
                os_time_days=days,
                os_event=event,
                os_time_original=raw_time,
                os_time_unit="days",
                event_definition="all_cause",
                age_years=lookup_char(chars, "age"),
                figo_stage=chars.get("Stage") or chars.get("stage") or "",
                grade=lookup_char(chars, "grade"),
                residual_disease=lookup_char(chars, "optimal"),
                notes=notes,
            )
        )
    return out


# ---------------------------------------------------------------------------
# 6. GSE14764 (Denkert)
# ---------------------------------------------------------------------------
def extract_gse14764(data_root: Path) -> list[dict[str, str]]:
    path = data_root / "gse14764-ovarian-expression-series-matrix" / "csv" / "phenotype.csv"
    _, rows = read_csv_dicts(path)
    out: list[dict[str, str]] = []
    for row in rows:
        histo = clean(row.get("histological type"))
        if not is_serous(histo):
            continue
        event = _map_binary_event(row.get("overall survival event", ""))
        months = parse_float(row.get("overall survival time"))
        if event is None or months is None:
            continue
        days = months_to_days(months)
        if days < MIN_OS_DAYS:
            continue
        gsm = clean(row.get("geo_accession"))
        out.append(
            make_row(
                cohort="gse14764",
                sample_id=gsm,
                geo_accession=gsm,
                platform="GPL96",
                histology=histo,
                os_time_days=days,
                os_event=event,
                os_time_original=clean(row.get("overall survival time")),
                os_time_unit="months",
                event_definition="all_cause",
                figo_stage=clean(row.get("figo stage")),
                grade=clean(row.get("grade")),
                residual_disease=clean(row.get("residual tumor")),
                notes="os event coding: 1=death, 0=censored; time in months",
            )
        )
    return out


EXTRACTORS = {
    "tcga-ov-hiseqv2": extract_tcga,
    "gse26712": extract_gse26712,
    "gse63885": extract_gse63885,
    "gse26193": extract_gse26193,
    "gse30161": extract_gse30161,
    "gse14764": extract_gse14764,
}

# CLI aliases so subcommands can be the GEO accession or the slug.
CLI_ALIASES = {
    "tcga": "tcga-ov-hiseqv2",
    "tcga-ov-hiseqv2": "tcga-ov-hiseqv2",
    "gse26712": "gse26712",
    "gse63885": "gse63885",
    "gse26193": "gse26193",
    "gse30161": "gse30161",
    "gse14764": "gse14764",
}


def extract_cohort(slug: str, data_root: Path) -> list[dict[str, str]]:
    fn = EXTRACTORS[slug]
    return fn(data_root)


def extract_all(data_root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for slug in COHORT_ORDER:
        chunk = extract_cohort(slug, data_root)
        n, d = count_deaths(chunk)
        exp_n, exp_d = EXPECTED[slug]
        note = "" if (n, d) == (exp_n, exp_d) else f" (split-doc expected {exp_n}/{exp_d})"
        eprint(f"{slug}: {n} patients / {d} deaths{note}")
        rows.extend(chunk)
    return rows


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------
def verify_labels(path: Path) -> int:
    """Re-read labels.csv; return 0 if all checks pass, 1 otherwise."""
    if not path.exists():
        eprint(f"FAIL: {path} does not exist")
        return 1
    fields, rows = read_csv_dicts(path)
    errors: list[str] = []
    missing = [c for c in LABEL_FIELDS if c not in fields]
    if missing:
        errors.append(f"missing columns: {missing}")

    print(summary_table(rows))
    print()

    by: dict[str, list[dict[str, str]]] = {c: [] for c in COHORT_ORDER}
    unknown: list[str] = []
    for i, row in enumerate(rows, start=2):
        c = row.get("cohort", "")
        if c in by:
            by[c].append(row)
        else:
            unknown.append(c)

        event = clean(row.get("os_event"))
        if event not in {"0", "1"}:
            errors.append(f"line {i}: os_event={event!r} not in {{0,1}}")
        days = parse_float(row.get("os_time_days"))
        if days is None:
            errors.append(f"line {i}: non-numeric os_time_days={row.get('os_time_days')!r}")
        elif days < 0:
            errors.append(f"line {i} {row.get('sample_id')}: negative os_time_days={days}")
        elif days < MIN_OS_DAYS:
            errors.append(
                f"line {i} {row.get('sample_id')}: os_time_days={days} < {MIN_OS_DAYS}"
            )
        unit = clean(row.get("os_time_unit"))
        if unit not in {"days", "months", "years"}:
            errors.append(f"line {i}: bad os_time_unit={unit!r}")
        edef = clean(row.get("event_definition"))
        if edef not in {"all_cause", "dod_dss_flavored"}:
            errors.append(f"line {i}: bad event_definition={edef!r}")
        plat = clean(row.get("platform"))
        if plat not in {"rnaseq_hiseqv2", "GPL96", "GPL570"}:
            errors.append(f"line {i}: bad platform={plat!r}")

    if unknown:
        errors.append(f"unexpected cohort values: {sorted(set(unknown))}")

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

    for slug, (exp_n, exp_d) in EXPECTED.items():
        n, d = count_deaths(by[slug])
        if (n, d) != (exp_n, exp_d):
            errors.append(
                f"{slug}: got {n}/{d} patients/deaths, expected {exp_n}/{exp_d}"
            )

    n, d = count_deaths(rows)
    if (n, d) != EXPECTED_TOTAL:
        errors.append(
            f"TOTAL: got {n}/{d} patients/deaths, expected "
            f"{EXPECTED_TOTAL[0]}/{EXPECTED_TOTAL[1]}"
        )

    if errors:
        eprint(f"FAIL: {len(errors)} check(s)")
        for msg in errors:
            eprint("  -", msg)
        return 1
    print("OK: counts, uniqueness, times, and event coding all match.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract standardized OS labels for the HGSOC training pool.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "subcommands:\n"
            "  all        extract all 6 cohorts and write the merged CSV (default)\n"
            "  verify     re-read labels.csv and assert expected n/deaths\n"
            "  tcga       TCGA-OV HiSeqV2 only\n"
            "  gse26712   Bonome GPL96\n"
            "  gse63885   Lisowska GPL570\n"
            "  gse26193   Mateescu GPL570\n"
            "  gse30161   Ferriss GPL570 FFPE (reparses series matrix)\n"
            "  gse14764   Denkert GPL96\n"
        ),
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DATA_ROOT,
        help="datasets/ovarian-cancer-prognosis-ml (default: workspace copy)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="merged labels.csv path (used by all/verify)",
    )
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("all", help="extract all cohorts, write merged labels.csv")
    sub.add_parser("verify", help="assert expected counts on labels.csv")
    for name, help_ in (
        ("tcga", "TCGA-OV HiSeqV2"),
        ("gse26712", "GSE26712 Bonome"),
        ("gse63885", "GSE63885 Lisowska"),
        ("gse26193", "GSE26193 Mateescu"),
        ("gse30161", "GSE30161 Ferriss (reparse matrix)"),
        ("gse14764", "GSE14764 Denkert"),
    ):
        sub.add_parser(name, help=help_)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cmd = args.cmd or "all"
    data_root: Path = args.data_root
    out_path: Path = args.out

    if cmd == "verify":
        return verify_labels(out_path)

    if cmd == "all":
        rows = extract_all(data_root)
        write_labels(out_path, rows)
        eprint()
        eprint(summary_table(rows))
        eprint(f"\nwrote {out_path} ({len(rows)} rows)")
        return 0

    slug = CLI_ALIASES.get(cmd)
    if slug is None:
        eprint(f"unknown command: {cmd}")
        return 2
    rows = extract_cohort(slug, data_root)
    write_labels_fh(sys.stdout, rows)
    n, d = count_deaths(rows)
    exp = EXPECTED[slug]
    eprint(f"{slug}: {n} patients / {d} deaths (expected {exp[0]}/{exp[1]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
