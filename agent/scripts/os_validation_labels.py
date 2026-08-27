#!/usr/bin/env python3
"""Compile the overall-survival (OS) validation-label table for HGSOC.

One row per patient/sample in the held-out validation cohorts
(docs/os-train-validation-split.md §4): the Agilent GPL6480 trio
(GSE32062, GSE53963, GSE17260), Illumina GPL14951 (GSE140082), and ABI
GPL2986 (GSE49997). Stdlib only. Mirrors os_pool_labels.py for the
training pool.

    python3 agent/scripts/os_validation_labels.py all
    python3 agent/scripts/os_validation_labels.py verify
    python3 agent/scripts/os_validation_labels.py gse53963   # one cohort to stdout

Default output:
    datasets/ovarian-cancer-prognosis-ml/os-validation/labels.csv

Schema: identical to the training-pool labels (see
docs/os-training-labels.md). Histology, stage, grade, and residual are
as recorded (not recoded to a common vocabulary). Months convert to
days with 365.25/12. Cox-usable rows require finite os_time_days >= 1.

Per-cohort rules and traps
--------------------------
1. gse32062  Yoshihara 2012, GPL6480, flagship  (expect 260 / 121)
   csv/phenotype.csv. Pure HGSOC (all 260 rows). Time = ``os (m)``
   (months, integers 1-128). Event = ``death (1)`` (1=dead, 0=censored).
   TRAP: ``status`` is GEO's public-on date, not vital status. Stage =
   ``Stage``; grade = ``grading``; residual = ``surgery status``
   (casefold — one row is 'Optimal'). No age. Uniform platinum+taxane.

2. gse53963  Yoshihara, GPL6480 two-color  (expect 160 / 139)
   Phenotype lives on CHANNEL 2 of the gzipped series matrix — the
   converter's phenotype.csv is unusable (ch1 only, duplicate ch2 lines
   overwrite). Reparse GSE53963_series_matrix.txt.gz exactly like
   GSE30161 but on ``!Sample_characteristics_ch2``, key:value per
   sample; TRAP: optional ``substage`` and ``tcga_sampleid`` keys make
   ch2 column-shifted across samples, so never index by line.
   DEDUPE (mandatory, split doc §4): drop the 14 samples with a
   non-empty ``tcga_sampleid`` — 13 overlap the TCGA HiSeqV2 training
   rows. 174 - 14 = 160; all 14 dropped are deaths, so 153 - 14 = 139.
   Time = ``time_fu_months`` (months). Event = ``vital_status``
   (Dead=1, Alive=0). All 174 are morphology=Serous. Stage = ``Stage``
   (one GSM is 'III/IV' — kept as recorded); grade = ``grade`` (note:
   scale includes 4); residual = ``debulking``; age = ``age_at_dx``.

3. gse17260  Yoshihara 2010, GPL6480  (expect 110 / 46)
   csv/phenotype.csv. All 110 serous — including 26 grade-1 samples;
   the split-doc 110/46 target INCLUDES grade 1, do not filter grade.
   Time = ``overall survival (m)`` (months). Event = ``death (1)``.
   Stage = ``Stage``; grade = ``tumor grade``; residual =
   ``cytoreductive surgery`` ('optimal' / 'not optimal'). No age.

4. gse140082  ICON7, GPL14951 FFPE  (expect 191 / 56)
   csv/phenotype.csv (converter output is correct, ch1). Subset:
   ``histology.serous`` == serous AND ``newgrade`` == high.grade AND
   ``figo_stage`` in {III, IV}. Time = ``final_ostm`` (DAYS, 1-1326).
   Event = ``final_osid`` (1=dead, 0=censored). TRAP: GEO ``status``
   is the public-on date; ``newgrade`` NA is the literal string 'NA'.
   Age = ``age``; residual = ``debulking_status``; treatment arm =
   ``treatment`` (bevacizumab/standard) goes in notes. Immature
   follow-up (~3.6 y max) — flagged in notes.

5. gse49997  Pils, GPL2986  (expect 171 / 48)
   csv/phenotype.csv. Drop ``excluded`` == yes (10 rows, clinical
   fields empty; their GSMs remain on the expression matrix). Keep
   ``histology`` == Serous. Time = ``os month`` (months, 1-49; NA is
   the empty string). Event = ``os event`` (1=dead, 0=censored).
   TRAP: ``figo grade`` is FIGO STAGE (II/III/IV), the real grade is
   ``grade`` ('3' / '1&2' / '#NULL!' — '#NULL!' becomes empty).
   Residual = ``residual tumor`` (Yes/No). Age = ``age``.

verify additionally asserts ZERO sample_id overlap with the training
pool labels (leakage check) when os-training-pool/labels.csv exists.

If real counts differ from the expect-numbers, the script emits what it
finds and verify fails loudly — no silent fudging (the split doc marked
GSE53963's ~160/~140 as an estimate; the disk-verified value is
160/139 because every dropped TCGA duplicate is a death).

References: docs/os-train-validation-split.md §4/§6,
docs/ovarian-cancer-prognosis-opportunities.md Appendix B,
docs/os-training-labels.md (schema).
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
DEFAULT_OUT = DATA_ROOT / "os-validation" / "labels.csv"
TRAIN_LABELS = DATA_ROOT / "os-training-pool" / "labels.csv"

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
# GSE53963 target is the disk-verified 160/139 (split doc said ~160/~140;
# all 14 dropped TCGA duplicates are deaths).
EXPECTED = {
    "gse32062": (260, 121),
    "gse53963": (160, 139),
    "gse17260": (110, 46),
    "gse140082": (191, 56),
    "gse49997": (171, 48),
}
EXPECTED_TOTAL = (892, 410)
COHORT_ORDER = list(EXPECTED.keys())
PLATFORMS = {"GPL6480", "GPL14951", "GPL2986"}

# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------
_NA = frozenset({"", "na", "nan", "n/a", "none", ".", "null", "unknown", "#null!"})


def eprint(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)


def _open_text(path: Path):
    """Text handle; transparently gunzip ``*.gz``."""
    if path.name.lower().endswith(".gz"):
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


def months_to_days(months: float) -> float:
    return months * DAYS_PER_MONTH


def _map_binary_event(raw: str, *, one_means_death: bool = True) -> int | None:
    s = clean(raw).lower()
    if not s:
        return None
    if s in {"1", "dead", "deceased", "death", "d", "true", "yes"}:
        return 1 if one_means_death else 0
    if s in {"0", "alive", "living", "censored", "censor", "a", "false", "no"}:
        return 0 if one_means_death else 1
    return None


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


def _finish_row(
    row: dict[str, str],
    *,
    cohort: str,
    platform: str,
    histology: str,
    raw_time: str,
    unit: str,
    raw_event: str,
    notes: str,
    age: str = "",
    stage: str = "",
    grade: str = "",
    residual: str = "",
) -> dict[str, str] | None:
    """Shared time/event gating; None if the row is not Cox-usable."""
    event = _map_binary_event(raw_event)
    val = parse_float(raw_time)
    if event is None or val is None:
        return None
    days = months_to_days(val) if unit == "months" else val
    if days < MIN_OS_DAYS:
        return None
    gsm = clean(row.get("geo_accession"))
    return make_row(
        cohort=cohort,
        sample_id=gsm,
        geo_accession=gsm,
        platform=platform,
        histology=histology,
        os_time_days=days,
        os_event=event,
        os_time_original=clean(raw_time),
        os_time_unit=unit,
        event_definition="all_cause",
        age_years=age,
        figo_stage=stage,
        grade=grade,
        residual_disease=residual,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# 1. GSE32062 (Yoshihara 2012) — flagship
# ---------------------------------------------------------------------------
def extract_gse32062(data_root: Path) -> list[dict[str, str]]:
    path = data_root / "gse32062-gpl6480-ovarian-expression-series-matrix" / "csv" / "phenotype.csv"
    _, rows = read_csv_dicts(path)
    out: list[dict[str, str]] = []
    for row in rows:
        made = _finish_row(
            row,
            cohort="gse32062",
            platform="GPL6480",
            histology=clean(row.get("source_name_ch1")) or "high-grade serous ovarian cancer",
            raw_time=row.get("os (m)", ""),
            unit="months",
            raw_event=row.get("death (1)", ""),
            notes="uniform platinum+taxane; ignored `status` (GEO public-on date)",
            stage=clean(row.get("Stage")),
            grade=clean(row.get("grading")),
            residual=clean(row.get("surgery status")),
        )
        if made is not None:
            out.append(made)
    return out


# ---------------------------------------------------------------------------
# 2. GSE53963 — channel-2 series-matrix reparse + TCGA dedupe
# ---------------------------------------------------------------------------
def _norm_char_key(key: str) -> str:
    key = key.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", key).strip()


def parse_series_matrix_chars(path: Path, channel: int) -> list[tuple[str, dict[str, str]]]:
    """Per-sample dicts from !Sample_characteristics_ch<N> ``key : value`` cells.

    Keys are not aligned across samples (optional keys shift positions),
    so every cell is split on its first colon and stored per sample.
    """
    accessions: list[str] | None = None
    per_sample: list[dict[str, str]] | None = None
    want_tag = f"!Sample_characteristics_ch{channel}"
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
            elif tag == want_tag and per_sample is not None:
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


def extract_gse53963(data_root: Path) -> list[dict[str, str]]:
    matrix = (
        data_root
        / "gse53963-ovarian-expression-series-matrix"
        / "GSE53963_series_matrix.txt.gz"
    )
    out: list[dict[str, str]] = []
    dropped: list[tuple[str, str]] = []
    for gsm, chars in parse_series_matrix_chars(matrix, channel=2):
        tcga_id = clean(chars.get("tcga_sampleid"))
        if tcga_id:
            # Mandatory dedupe vs the TCGA HiSeqV2 training rows (split doc §4).
            dropped.append((gsm, tcga_id))
            continue
        histo = clean(chars.get("morphology"))
        if histo.lower() != "serous":
            continue
        raw_time = clean(chars.get("time_fu_months"))
        event = _map_binary_event(chars.get("vital_status", ""))
        months = parse_float(raw_time)
        if event is None or months is None:
            continue
        days = months_to_days(months)
        if days < MIN_OS_DAYS:
            continue
        out.append(
            make_row(
                cohort="gse53963",
                sample_id=gsm,
                geo_accession=gsm,
                platform="GPL6480",
                histology=histo,
                os_time_days=days,
                os_event=event,
                os_time_original=raw_time,
                os_time_unit="months",
                event_definition="all_cause",
                age_years=chars.get("age_at_dx", ""),
                figo_stage=chars.get("Stage", ""),
                grade=chars.get("grade", ""),
                residual_disease=chars.get("debulking", ""),
                notes=(
                    "reparsed from ch2 series matrix (converter CSV unusable); "
                    f"{len(dropped)} TCGA duplicates dropped at extraction"
                ),
            )
        )
    eprint(
        f"gse53963: dropped {len(dropped)} TCGA duplicates: "
        + ", ".join(f"{gsm}={barcode}" for gsm, barcode in dropped)
    )
    return out


# ---------------------------------------------------------------------------
# 3. GSE17260 (Yoshihara 2010)
# ---------------------------------------------------------------------------
def extract_gse17260(data_root: Path) -> list[dict[str, str]]:
    path = data_root / "gse17260-ovarian-expression-series-matrix" / "csv" / "phenotype.csv"
    _, rows = read_csv_dicts(path)
    out: list[dict[str, str]] = []
    for row in rows:
        made = _finish_row(
            row,
            cohort="gse17260",
            platform="GPL6480",
            histology=clean(row.get("disease state")) or "serous ovarian cancer",
            raw_time=row.get("overall survival (m)", ""),
            unit="months",
            raw_event=row.get("death (1)", ""),
            notes=(
                "26 grade-1 serous retained per split-doc target; "
                "ignored `status` (GEO public-on date)"
            ),
            stage=clean(row.get("Stage")),
            grade=clean(row.get("tumor grade")),
            residual=clean(row.get("cytoreductive surgery")),
        )
        if made is not None:
            out.append(made)
    return out


# ---------------------------------------------------------------------------
# 4. GSE140082 (ICON7) — serous + high-grade + FIGO III/IV
# ---------------------------------------------------------------------------
def extract_gse140082(data_root: Path) -> list[dict[str, str]]:
    path = data_root / "gse140082-ovarian-expression-series-matrix" / "csv" / "phenotype.csv"
    _, rows = read_csv_dicts(path)
    out: list[dict[str, str]] = []
    for row in rows:
        if clean(row.get("histology.serous")).lower() != "serous":
            continue
        grade = clean(row.get("newgrade"))  # 'NA' string -> empty via _NA
        if grade != "high.grade":
            continue
        stage = clean(row.get("figo_stage"))
        if stage not in {"III", "IV"}:
            continue
        arm = clean(row.get("treatment"))
        notes = "immature follow-up (~3.6 y max); flagged secondary validator"
        if arm:
            notes += f"; treatment={arm}"
        made = _finish_row(
            row,
            cohort="gse140082",
            platform="GPL14951",
            histology=clean(row.get("histology.serous")),
            raw_time=row.get("final_ostm", ""),
            unit="days",
            raw_event=row.get("final_osid", ""),
            notes=notes,
            age=clean(row.get("age")),
            stage=stage,
            grade=grade,
            residual=clean(row.get("debulking_status")),
        )
        if made is not None:
            out.append(made)
    return out


# ---------------------------------------------------------------------------
# 5. GSE49997 (Pils, ABI)
# ---------------------------------------------------------------------------
def extract_gse49997(data_root: Path) -> list[dict[str, str]]:
    path = data_root / "gse49997-ovarian-expression-series-matrix" / "csv" / "phenotype.csv"
    _, rows = read_csv_dicts(path)
    out: list[dict[str, str]] = []
    for row in rows:
        if clean(row.get("excluded")).lower() == "yes":
            continue
        histo = clean(row.get("histology"))
        if histo != "Serous":
            continue
        made = _finish_row(
            row,
            cohort="gse49997",
            platform="GPL2986",
            histology=histo,
            raw_time=row.get("os month", ""),
            unit="months",
            raw_event=row.get("os event", ""),
            notes=(
                "short follow-up (max ~49 mo); supportive only; "
                "`figo grade` column is FIGO stage, `grade` is histologic grade"
            ),
            age=clean(row.get("age")),
            stage=clean(row.get("figo grade")),
            grade=clean(row.get("grade")),
            residual=clean(row.get("residual tumor")),
        )
        if made is not None:
            out.append(made)
    return out


EXTRACTORS = {
    "gse32062": extract_gse32062,
    "gse53963": extract_gse53963,
    "gse17260": extract_gse17260,
    "gse140082": extract_gse140082,
    "gse49997": extract_gse49997,
}
CLI_ALIASES = {name: name for name in EXTRACTORS}


def extract_cohort(slug: str, data_root: Path) -> list[dict[str, str]]:
    return EXTRACTORS[slug](data_root)


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
def verify_labels(path: Path, train_labels: Path = TRAIN_LABELS) -> int:
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
        if plat not in PLATFORMS:
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

    # Leakage check: no sample_id may appear in the training pool labels.
    if train_labels.exists():
        _, train_rows = read_csv_dicts(train_labels)
        train_ids = {clean(r.get("sample_id")) for r in train_rows}
        train_ids |= {clean(r.get("geo_accession")) for r in train_rows}
        train_ids.discard("")
        overlap = sorted(sid for sid in seen if sid in train_ids)
        tcga_leak = sorted(
            clean(r.get("sample_id"))
            for r in rows
            if clean(r.get("sample_id")).startswith("TCGA-")
        )
        if overlap:
            errors.append(f"{len(overlap)} sample_id(s) also in training pool: {overlap[:8]}")
        if tcga_leak:
            errors.append(f"{len(tcga_leak)} TCGA barcodes present in validation: {tcga_leak[:8]}")
    else:
        eprint(f"note: training labels not found at {train_labels}; leakage check skipped")

    if errors:
        eprint(f"FAIL: {len(errors)} check(s)")
        for msg in errors:
            eprint("  -", msg)
        return 1
    print("OK: counts, uniqueness, times, event coding, and train/validation disjointness all pass.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract standardized OS labels for the held-out HGSOC validation cohorts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "subcommands:\n"
            "  all        extract all 5 cohorts and write the merged CSV (default)\n"
            "  verify     re-read labels.csv and assert expected n/deaths + leakage\n"
            "  gse32062   Yoshihara 2012 GPL6480 (flagship)\n"
            "  gse53963   Yoshihara GPL6480 two-color (ch2 reparse, TCGA dedupe)\n"
            "  gse17260   Yoshihara 2010 GPL6480 (within-platform replicate)\n"
            "  gse140082  ICON7 GPL14951 FFPE (serous+high-grade+III/IV subset)\n"
            "  gse49997   Pils GPL2986 (excluded=yes dropped, Serous subset)\n"
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
    parser.add_argument(
        "--train-labels",
        type=Path,
        default=TRAIN_LABELS,
        help="training-pool labels.csv for the leakage check in verify",
    )
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("all", help="extract all cohorts, write merged labels.csv")
    sub.add_parser("verify", help="assert expected counts on labels.csv")
    for name in CLI_ALIASES:
        sub.add_parser(name, help=f"{name} only, to stdout")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cmd = args.cmd or "all"
    data_root: Path = args.data_root
    out_path: Path = args.out

    if cmd == "verify":
        return verify_labels(out_path, args.train_labels)

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
