#!/usr/bin/env python3
"""Recode OS-table residual disease and FIGO stage at modelling time.

The compiled label tables keep source vocabularies as recorded
(docs/os-training-labels.md, docs/os-validation-labels.md). This module is
the single recoding implementation for M3/M4 notebooks. Stdlib only.

GOG residual rule (optimal = residual ≤ 1 cm):
    optimal (0)     no macroscopic / R0 / R1 / 1-10 mm / Optimal / 0 / No
    suboptimal (1)  R2 / 11-20 mm / >20 mm / Suboptimal / not optimal /
                    residual 1 / Yes / Inoperable
    missing         empty, Unknown

GSE14764 ``0``/``1`` and GSE49997 ``No``/``Yes`` do not carry a 1 cm cutoff;
any recorded residual is coded suboptimal. R1 is treated as optimal (≤ 1 cm).

Stage becomes an integer 1–4 (I–IV). ``III/IV`` → 3. GSE26193 typo ``1Ia`` → 1.

    python3 agent/scripts/os_clinical.py verify
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
DATA_ROOT = WORKSPACE / "datasets" / "ovarian-cancer-prognosis-ml"
TRAIN_LABELS = DATA_ROOT / "os-training-pool" / "labels.csv"
VAL_LABELS = DATA_ROOT / "os-validation" / "labels.csv"

_NA = {"", "na", "nan", "unknown", "#null!", "none"}


def _norm(val: object) -> str:
    s = " ".join(str(val).strip().lower().replace("_", " ").split())
    s = s.replace("−", "-").replace("–", "-")
    return s


def recode_residual(val: object) -> int | None:
    """1 = suboptimal / residual above GOG optimal; 0 = optimal; None = missing."""
    key = _norm(val)
    if key in _NA:
        return None

    if key in {
        "optimal", "r0", "r1",
        "no macroscopic disease", "no", "0",
        "1-10 mm", "1-10mm", "1 10 mm",
    }:
        return 0
    if key in {
        "suboptimal", "sub-optimal", "sub optimal", "not optimal",
        "r2", "11-20 mm", "11-20mm", "11 20 mm",
        ">20 mm", ">20mm", "> 20 mm",
        "1", "yes", "inoperable",
    }:
        return 1
    return None


def recode_stage(val: object) -> int | None:
    """FIGO I–IV as 1–4. None if missing or unparseable."""
    raw = str(val).strip()
    if _norm(raw) in _NA:
        return None
    s = raw.upper().replace("STAGE", "").strip()
    s = s.replace(" ", "")
    if s.startswith("1I"):  # GSE26193 "1Ia"
        s = s[1:]
    if "III/IV" in s or s in {"III/IV", "3/4"}:
        return 3
    if s.startswith("IV") or s.startswith("4"):
        return 4
    if s.startswith("III") or s.startswith("3"):
        return 3
    if s.startswith("II") or s.startswith("2"):
        return 2
    if s.startswith("I") or s.startswith("1"):
        return 1
    return None


def annotate_row(row: dict) -> dict:
    out = dict(row)
    out["residual_subopt"] = recode_residual(row.get("residual_disease", ""))
    out["stage_ord"] = recode_stage(row.get("figo_stage", ""))
    age = str(row.get("age_years", "")).strip()
    try:
        out["age"] = float(age) if age else None
    except ValueError:
        out["age"] = None
    return out


def _scan(path: Path) -> tuple[list[str], list[str], int, int]:
    unmapped_r: dict[str, int] = {}
    unmapped_s: dict[str, int] = {}
    n = 0
    n_both = 0
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            n += 1
            raw_r = row.get("residual_disease", "")
            raw_s = row.get("figo_stage", "")
            r = recode_residual(raw_r)
            s = recode_stage(raw_s)
            if str(raw_r).strip() and r is None:
                unmapped_r[repr(raw_r)] = unmapped_r.get(repr(raw_r), 0) + 1
            if str(raw_s).strip() and s is None:
                unmapped_s[repr(raw_s)] = unmapped_s.get(repr(raw_s), 0) + 1
            if r is not None and s is not None:
                n_both += 1
    msgs = []
    for kind, bag in (("residual", unmapped_r), ("stage", unmapped_s)):
        for val, k in sorted(bag.items()):
            msgs.append(f"{path.name} unmapped {kind} {val} (n={k})")
    return msgs, [], n, n_both


def verify(paths: list[Path] | None = None) -> int:
    paths = paths or [TRAIN_LABELS, VAL_LABELS]
    bad: list[str] = []
    for path in paths:
        if not path.is_file():
            bad.append(f"missing {path}")
            continue
        msgs, _, n, n_both = _scan(path)
        print(f"{path.relative_to(WORKSPACE)}: {n} rows, {n_both} with both residual+stage")
        bad.extend(msgs)
    if bad:
        print("FAILED:", file=sys.stderr)
        for line in bad:
            print(" ", line, file=sys.stderr)
        return 1
    print("OK — every non-empty residual and stage value recodes")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", nargs="?", default="verify", choices=["verify"])
    args = ap.parse_args()
    raise SystemExit(verify() if args.cmd == "verify" else 2)


if __name__ == "__main__":
    main()
