#!/usr/bin/env python3
"""Validate that a converted CSV is a lossless copy of its original file.

Guarantees checked, per original/CSV pair:
  * same number of rows (no lost/extra rows)
  * same number of columns in every row
  * every cell is byte-for-byte identical as a string (no reformatting,
    truncation, type coercion, quoting artifacts, or encoding changes)

The original file is parsed independently of the conversion script (plain
delimiter split, no quote processing), so converter bugs cannot hide.

Usage:
    validate_csv_conversion.py --path datasets/<topic>/<slug>
    validate_csv_conversion.py --path datasets/<topic>/<slug>/<original-file>
    validate_csv_conversion.py --original <file> --csv <file>

Exit code: 0 if every pair passes, 1 otherwise. JSON report on stdout.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import sys
from itertools import zip_longest
from pathlib import Path

from common import WORKSPACE, emit, eprint

MAX_REPORTED_MISMATCHES = 25
SKIP_NAMES = {"report.md", "readme.md", "readme.txt", ".ds_store"}
SKIP_SUFFIXES = (".md", ".pdf", ".html", ".htm", ".xml", ".soft", ".tar",
                 ".zip")
KNOWN_EXTS = (".txt.gz", ".tsv.gz", ".csv.gz", ".gz", ".txt", ".tsv", ".csv",
              ".parquet", ".xlsx", ".xls")
_MISSING = object()  # sentinel for zip_longest row alignment


def open_text(path: Path):
    """Text handle for path; transparently gunzips .gz."""
    if path.name.lower().endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8",
                                errors="replace", newline="")
    return open(path, encoding="utf-8", errors="replace", newline="")


def sniff_delimiter(path: Path) -> str:
    with open_text(path) as fh:
        for line in fh:
            if line.strip():
                if "\t" in line:
                    return "\t"
                if "," in line:
                    return ","
                if ";" in line:
                    return ";"
                return "\t"
    raise SystemExit(f"empty original file: {path}")


def iter_original_rows(path: Path, delim: str):
    """Yield one list of cells per non-empty line, split literally.

    No quote processing on purpose: this is the independent reference parse.
    """
    with open_text(path) as fh:
        for line in fh:
            line = line.rstrip("\r\n")
            if line == "":
                continue
            yield line.split(delim)


def iter_csv_rows(path: Path):
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        yield from csv.reader(fh)


def stem_for(path: Path) -> str:
    name = path.name
    for ext in KNOWN_EXTS:
        if name.lower().endswith(ext):
            return name[: -len(ext)]
    return path.stem or name


def is_data_file(path: Path) -> bool:
    if not path.is_file() or path.name.startswith("."):
        return False
    low = path.name.lower()
    if low in SKIP_NAMES or low.endswith(SKIP_SUFFIXES):
        return False
    return path.suffix == "" or low.endswith(KNOWN_EXTS)


def find_csv_for(original: Path, explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit if explicit.is_file() else None
    candidate = original.parent / "csv" / f"{stem_for(original)}.csv"
    return candidate if candidate.is_file() else None


def validate_pair(original: Path, csv_path: Path) -> dict:
    delim = sniff_delimiter(original)
    if delim == ",":
        # Original is itself CSV: parse with the csv module for correctness.
        orig_rows = iter_csv_rows(original)
    else:
        orig_rows = iter_original_rows(original, delim)
    conv_rows = iter_csv_rows(csv_path)

    header: list[str] | None = None
    n_rows_orig = 0
    n_rows_csv = 0
    n_cells = 0
    n_bad_width = 0
    n_bad_cells = 0
    mismatches: list[dict] = []
    width_issues: list[dict] = []

    def record_mismatch(row_no: int, col_no: int, before, after) -> None:
        nonlocal n_bad_cells
        n_bad_cells += 1
        if len(mismatches) < MAX_REPORTED_MISMATCHES:
            col_name = None
            if header and col_no - 1 < len(header):
                col_name = header[col_no - 1]
            mismatches.append({
                "row": row_no,
                "col": col_no,
                "col_name": col_name,
                "original": None if before is _MISSING else str(before)[:200],
                "csv": None if after is _MISSING else str(after)[:200],
            })

    row_no = 0
    for orig_row, conv_row in zip_longest(orig_rows, conv_rows,
                                          fillvalue=_MISSING):
        row_no += 1
        if orig_row is _MISSING:
            n_rows_csv += 1
            record_mismatch(row_no, 0, _MISSING, "<entire extra row in csv>")
            continue
        if conv_row is _MISSING:
            n_rows_orig += 1
            record_mismatch(row_no, 0, "<entire row missing from csv>",
                            _MISSING)
            continue

        n_rows_orig += 1
        n_rows_csv += 1
        if header is None:
            header = list(orig_row)

        if len(orig_row) != len(conv_row):
            n_bad_width += 1
            if len(width_issues) < MAX_REPORTED_MISMATCHES:
                width_issues.append({
                    "row": row_no,
                    "original_cols": len(orig_row),
                    "csv_cols": len(conv_row),
                })

        for col_no, (before, after) in enumerate(
                zip_longest(orig_row, conv_row, fillvalue=_MISSING), start=1):
            if before is _MISSING or after is _MISSING:
                record_mismatch(row_no, col_no, before, after)
                continue
            n_cells += 1
            if before != after:
                record_mismatch(row_no, col_no, before, after)

    ok = n_bad_cells == 0 and n_bad_width == 0 and n_rows_orig == n_rows_csv
    return {
        "status": "pass" if ok else "fail",
        "original": str(original),
        "csv": str(csv_path),
        "delimiter_original": {"\t": "tab", ",": "comma", ";": "semicolon"}[delim],
        "rows_original": n_rows_orig,
        "rows_csv": n_rows_csv,
        "header_cols": len(header) if header else 0,
        "cells_compared": n_cells,
        "rows_with_wrong_col_count": n_bad_width,
        "cells_different": n_bad_cells,
        "width_issues_sample": width_issues,
        "mismatches_sample": mismatches,
    }


def resolve_pairs(args) -> list[tuple[Path, Path | None]]:
    if args.original:
        orig = Path(args.original)
        if not orig.is_absolute():
            orig = WORKSPACE / orig
        if not orig.is_file():
            raise SystemExit(f"original not found: {orig}")
        csv_arg = Path(args.csv) if args.csv else None
        if csv_arg is not None and not csv_arg.is_absolute():
            csv_arg = WORKSPACE / csv_arg
        return [(orig, csv_arg)]

    p = Path(args.path)
    if not p.is_absolute():
        p = WORKSPACE / p
    if p.is_file():
        return [(p, None)]
    if p.is_dir():
        files = [f for f in sorted(p.iterdir()) if is_data_file(f)]
        if not files:
            raise SystemExit(f"no data files found in: {p}")
        return [(f, None) for f in files]
    raise SystemExit(f"path not found: {p}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", help="Dataset dir or single original file")
    ap.add_argument("--original", help="Original file (pair mode)")
    ap.add_argument("--csv", help="CSV file (pair mode, optional)")
    args = ap.parse_args()
    if not args.path and not args.original:
        raise SystemExit("provide --path or --original")
    if args.original and args.path:
        raise SystemExit("use either --path or --original, not both")

    results = []
    for original, explicit_csv in resolve_pairs(args):
        csv_path = find_csv_for(original, explicit_csv)
        if csv_path is None:
            results.append({
                "status": "fail",
                "original": str(original),
                "error": "no converted CSV found "
                         f"(expected {original.parent / 'csv' / (stem_for(original) + '.csv')})",
            })
            continue
        eprint(f"validating {original.name} -> {csv_path.name} ...")
        results.append(validate_pair(original, csv_path))

    n_pass = sum(1 for r in results if r["status"] == "pass")
    emit({
        "passed": n_pass,
        "failed": len(results) - n_pass,
        "results": results,
    })
    if n_pass != len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
