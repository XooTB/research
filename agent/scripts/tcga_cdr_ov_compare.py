#!/usr/bin/env python3
"""Subset the TCGA-CDR PanCanAtlas sheet to OV and compare against the
current TCGA OS training-pool labels (Xena-derived).

Stdlib only (T003; the CDR labels are being evaluated, not switched to).

Reads:
    datasets/ovarian-cancer-prognosis-ml/tcga-cdr-pancanatlas/csv/tcga-cdr.csv
    datasets/ovarian-cancer-prognosis-ml/os-training-pool/labels.csv
        (rows with cohort == "tcga-ov-hiseqv2"; sample_id is a TCGA sample
        barcode like TCGA-04-1348-01 — first 12 chars are the patient
        barcode used by CDR's bcr_patient_barcode)

Writes:
    datasets/ovarian-cancer-prognosis-ml/tcga-cdr-pancanatlas/csv/ov_subset.csv
        one row per CDR patient with type == OV: bcr_patient_barcode, OS,
        OS.time, DSS, DSS.time, PFI, PFI.time, plus age/stage/histology/grade/
        residual columns present in CDR.

Prints a JSON comparison summary to stdout; progress to stderr. Does not
modify labels.csv or any tracked experiment/pool file — read-only on those.

    python3 agent/scripts/tcga_cdr_ov_compare.py
"""
from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORKSPACE, emit, eprint  # noqa: E402

CDR_CSV = WORKSPACE / "datasets/ovarian-cancer-prognosis-ml/tcga-cdr-pancanatlas/csv/tcga-cdr.csv"
POOL_LABELS = WORKSPACE / "datasets/ovarian-cancer-prognosis-ml/os-training-pool/labels.csv"
OUT_CSV = WORKSPACE / "datasets/ovarian-cancer-prognosis-ml/tcga-cdr-pancanatlas/csv/ov_subset.csv"

MISSING = {"#n/a", "[not available]", "[not applicable]", "[unknown]", "[discrepancy]", ""}

OV_COLUMNS = [
    "bcr_patient_barcode", "type", "age_at_initial_pathologic_diagnosis",
    "ajcc_pathologic_tumor_stage", "clinical_stage", "histological_type",
    "histological_grade", "residual_tumor",
    "OS", "OS.time", "DSS", "DSS.time", "PFI", "PFI.time",
]


def _clean(v: str):
    return None if v.strip().lower() in MISSING else v.strip()


def _num(v):
    v = _clean(v) if isinstance(v, str) else v
    if v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def load_cdr_ov() -> list[dict]:
    with open(CDR_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    ov = [r for r in rows if r.get("type") == "OV"]
    eprint(f"[tcga_cdr_ov_compare] CDR total rows={len(rows)} OV rows={len(ov)}")
    return ov


def load_pool_tcga() -> dict[str, dict]:
    with open(POOL_LABELS, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["cohort"] == "tcga-ov-hiseqv2"]
    eprint(f"[tcga_cdr_ov_compare] pool tcga-ov-hiseqv2 rows={len(rows)}")
    by_patient = {}
    for r in rows:
        patient = r["sample_id"][:12]
        by_patient[patient] = r
    return by_patient


def write_subset(ov_rows: list[dict]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OV_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in ov_rows:
            w.writerow(r)
    eprint(f"[tcga_cdr_ov_compare] wrote {OUT_CSV} ({len(ov_rows)} rows)")


def main() -> None:
    ov_rows = load_cdr_ov()
    write_subset(ov_rows)
    cdr_by_patient = {r["bcr_patient_barcode"]: r for r in ov_rows}
    pool_by_patient = load_pool_tcga()

    matched = 0
    event_disagreements = 0
    time_diffs = []
    pfi_usable = 0
    event_disagreement_examples = []

    for patient, pool_row in pool_by_patient.items():
        cdr_row = cdr_by_patient.get(patient)
        if cdr_row is None:
            continue
        matched += 1

        pool_event = _num(pool_row["os_event"])
        cdr_event = _num(cdr_row.get("OS"))
        if pool_event is not None and cdr_event is not None and pool_event != cdr_event:
            event_disagreements += 1
            if len(event_disagreement_examples) < 10:
                event_disagreement_examples.append(
                    {"patient": patient, "pool_os_event": pool_event, "cdr_OS": cdr_event})

        pool_time = _num(pool_row["os_time_days"])
        cdr_time = _num(cdr_row.get("OS.time"))
        if pool_time is not None and cdr_time is not None:
            time_diffs.append(abs(pool_time - cdr_time))

        pfi_time = _num(cdr_row.get("PFI.time"))
        pfi_event = _num(cdr_row.get("PFI"))
        if pfi_time is not None and pfi_time > 0 and pfi_event is not None:
            pfi_usable += 1

    extra_ov = [p for p in cdr_by_patient if p not in pool_by_patient]

    def q(data, frac):
        if not data:
            return None
        data = sorted(data)
        idx = (len(data) - 1) * frac
        lo, hi = int(idx), min(int(idx) + 1, len(data) - 1)
        return data[lo] + (data[hi] - data[lo]) * (idx - lo)

    diff_summary = None
    if time_diffs:
        diff_summary = {
            "n": len(time_diffs),
            "median": statistics.median(time_diffs),
            "q1": q(time_diffs, 0.25),
            "q3": q(time_diffs, 0.75),
            "iqr": (q(time_diffs, 0.75) - q(time_diffs, 0.25)),
            "max": max(time_diffs),
        }

    result = {
        "cdr_ov_patients": len(cdr_by_patient),
        "pool_tcga_patients": len(pool_by_patient),
        "matched_of_302": matched,
        "os_event_disagreements": event_disagreements,
        "os_event_disagreement_examples": event_disagreement_examples,
        "os_time_diff_days": diff_summary,
        "pfi_usable_of_matched": pfi_usable,
        "extra_ov_patients_not_in_pool": len(extra_ov),
        "out_csv": str(OUT_CSV),
    }
    emit(result)


if __name__ == "__main__":
    main()
