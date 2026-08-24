#!/usr/bin/env python3
"""Inspect a downloaded dataset: structure, schema, usability. Writes REPORT.md.

Works with or without pandas:
  * pandas present  -> dtypes, per-column missing %, richer profiling
  * pandas absent    -> stdlib csv fallback (columns, row count, sample)
Parquet needs pandas+pyarrow; JSON/JSONL are sampled with stdlib.

Usage:
    datasets_verify.py --id 3
    datasets_verify.py --path datasets/antibiotic-resistance/atlas
"""
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path

import db
from common import cfg, emit, eprint

TABULAR = {".csv", ".tsv", ".parquet", ".json", ".jsonl", ".ndjson"}


def _human(n: int | None) -> str:
    if not n:
        return "unknown"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _try_pandas():
    try:
        import pandas as pd  # noqa: WPS433
        return pd
    except ImportError:
        return None


def profile_csv_stdlib(path: Path, sample_rows: int) -> dict:
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        delim = "\t" if path.suffix.lower() == ".tsv" else ","
        reader = csv.reader(fh, delimiter=delim)
        try:
            header = next(reader)
        except StopIteration:
            return {"error": "empty file"}
        rows = 0
        missing = [0] * len(header)
        sample = []
        for i, row in enumerate(reader):
            rows += 1
            for j in range(min(len(row), len(header))):
                if row[j].strip() == "":
                    missing[j] += 1
            if i < 3:
                sample.append(row)
    return {
        "columns": header,
        "n_cols": len(header),
        "n_rows_counted": rows,
        "missing_by_col": {header[j]: missing[j] for j in range(len(header))},
        "sample": sample,
        "engine": "stdlib-csv",
    }


def profile_tabular_pandas(pd, path: Path, sample_rows: int) -> dict:
    suf = path.suffix.lower()
    read_kw = {"nrows": sample_rows} if suf in {".csv", ".tsv"} else {}
    if suf in {".csv", ".tsv"}:
        df = pd.read_csv(path, sep="\t" if suf == ".tsv" else ",", **read_kw)
    elif suf == ".parquet":
        df = pd.read_parquet(path)
    elif suf in {".json", ".jsonl", ".ndjson"}:
        df = pd.read_json(path, lines=suf in {".jsonl", ".ndjson"})
    else:
        return {"error": f"unsupported: {suf}"}
    n = len(df)
    return {
        "columns": list(df.columns.astype(str)),
        "n_cols": df.shape[1],
        "n_rows_sampled": n,
        "dtypes": {str(c): str(t) for c, t in df.dtypes.items()},
        "missing_pct": {str(c): round(float(df[c].isna().mean()) * 100, 2)
                        for c in df.columns},
        "sample": df.head(3).astype(str).to_dict(orient="records"),
        "engine": "pandas",
        "note": "row stats are from a sample" if read_kw else "full file read",
    }


def profile_file(path: Path, pd, sample_rows: int) -> dict:
    info = {"file": path.name, "size": path.stat().st_size,
            "size_h": _human(path.stat().st_size), "format": path.suffix.lower()}
    if path.suffix.lower() not in TABULAR:
        return info
    try:
        if pd is not None:
            info.update(profile_tabular_pandas(pd, path, sample_rows))
        elif path.suffix.lower() in {".csv", ".tsv"}:
            info.update(profile_csv_stdlib(path, sample_rows))
        else:
            info["note"] = f"install pandas+pyarrow to profile {path.suffix} files"
    except Exception as exc:  # noqa: BLE001
        info["error"] = str(exc)
    return info


def build_report(root: Path, profiles: list[dict]) -> str:
    lines = [f"# Dataset verification report", "",
             f"**Location:** `{root}`", ""]
    total = sum(p.get("size", 0) for p in profiles)
    tabular = [p for p in profiles if "columns" in p]
    lines += [
        f"- Files: {len(profiles)}",
        f"- Total size: {_human(total)}",
        f"- Tabular files profiled: {len(tabular)}",
        "",
    ]
    for p in profiles:
        lines.append(f"## `{p['file']}`  ({p.get('size_h', '?')}, {p.get('format', '?')})")
        if "error" in p:
            lines.append(f"- ERROR: {p['error']}")
        if "columns" in p:
            rows = p.get("n_rows_sampled") or p.get("n_rows_counted")
            lines.append(f"- Columns ({p['n_cols']}): {', '.join(p['columns'])}")
            lines.append(f"- Rows: {rows} ({p.get('engine')})")
            if "dtypes" in p:
                lines.append("- Dtypes: " + ", ".join(
                    f"{c}:{t}" for c, t in list(p["dtypes"].items())[:20]))
            miss = p.get("missing_pct") or {}
            flagged = {c: v for c, v in miss.items() if v and v > 0}
            if flagged:
                lines.append("- Missing values: " + ", ".join(
                    f"{c} {v}%" for c, v in list(flagged.items())[:20]))
        lines.append("")
    lines += ["## Usability verdict", "",
              "_(Filled in by the agent based on the profile above and your criteria.)_", ""]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int)
    ap.add_argument("--path")
    args = ap.parse_args()

    conn = db.connect()
    row = None
    if args.id is not None:
        row = conn.execute("SELECT * FROM datasets WHERE id=?", (args.id,)).fetchone()
        if not row:
            eprint(f"No dataset with id {args.id}")
            emit({"error": f"no dataset id {args.id}"})
            return
        root = Path(row["local_path"]) if row["local_path"] else None
    else:
        root = Path(args.path).resolve()

    if not root or not root.exists():
        emit({"error": f"path not found: {root}"})
        return

    pd = _try_pandas()
    sample_rows = cfg("datasets.verify_sample_rows", 1000)
    profiles = []
    for f in sorted(root.rglob("*")):
        if f.is_file():
            profiles.append(profile_file(f, pd, sample_rows))

    report = build_report(root, profiles)
    report_path = root / "REPORT.md"
    report_path.write_text(report, encoding="utf-8")

    total = sum(p.get("size", 0) for p in profiles)
    tabular = [p for p in profiles if "columns" in p]
    all_cols = sorted({c for p in tabular for c in p.get("columns", [])})
    fmts = sorted({p["format"] for p in profiles if p.get("format")})

    if row is not None:
        db.upsert_dataset(conn, {
            "source": row["source"], "source_id": row["source_id"],
            "file_format": "/".join(fmts), "size_bytes": total,
            "n_cols": len(all_cols), "columns": all_cols,
            "verified": True, "status": "verified",
        })
    conn.close()

    emit({
        "path": str(root),
        "report": str(report_path),
        "pandas_available": pd is not None,
        "total_size": _human(total),
        "formats": fmts,
        "files": len(profiles),
        "profiles": profiles,
    })


if __name__ == "__main__":
    main()
