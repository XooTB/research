#!/usr/bin/env python3
"""Convert collected research datasets into CSV.

Detects format from content/extension and writes CSVs under each dataset's
`csv/` subdirectory (or `--out-dir`).

Supported inputs:
  * GEO series matrix (.txt / .txt.gz)  -> phenotype.csv + expression.csv
  * UCSC Xena / TSV (incl. extensionless) -> <stem>.csv
  * CSV / TSV / TXT / Parquet / Excel     -> <stem>.csv
  * Gzipped variants of the above

Usage:
    datasets_to_csv.py --path datasets/<topic>/<slug>
    datasets_to_csv.py --topic ovarian-cancer-prognosis-ml
    datasets_to_csv.py --path datasets/.../GSE9891_series_matrix.txt
    datasets_to_csv.py --topic ovarian-cancer-prognosis-ml --force
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import re
from pathlib import Path

from common import WORKSPACE, emit, eprint, ws_path

SKIP_NAMES = {"report.md", "readme.md", "readme.txt", ".ds_store"}
# Extensionless Xena-style matrices commonly appear as these basenames.
XENA_BASENAMES = {
    "hiseqv2", "ov_clinicalmatrix", "clinicalmatrix", "phenotype",
}


def _open_text(path: Path):
    """Return a text file handle; transparently gunzip .gz."""
    if path.suffix.lower() == ".gz" or path.name.lower().endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8",
                                errors="replace", newline="")
    return open(path, encoding="utf-8", errors="replace", newline="")


def _strip_quotes(cell: str) -> str:
    cell = cell.strip()
    if len(cell) >= 2 and cell[0] == cell[-1] and cell[0] in "'\"":
        return cell[1:-1]
    return cell


def _sniff_delimiter(sample: str) -> str:
    if "\t" in sample:
        return "\t"
    if sample.count(",") > sample.count(";"):
        return ","
    if ";" in sample:
        return ";"
    return "\t"


def detect_format(path: Path) -> str:
    """Return one of: geo_series_matrix, tsv, csv, parquet, excel, unknown."""
    name = path.name.lower()
    sufs = "".join(path.suffixes).lower()  # e.g. .txt.gz

    if ".parquet" in sufs:
        return "parquet"
    if ".xlsx" in sufs or ".xls" in sufs:
        return "excel"
    if name.endswith("_series_matrix.txt") or name.endswith("_series_matrix.txt.gz"):
        return "geo_series_matrix"

    # Peek content for GEO header / delimiter even without extension.
    try:
        with _open_text(path) as fh:
            head = "".join(fh.readline() for _ in range(5))
    except OSError:
        return "unknown"

    if "!series_" in head.lower() or "!sample_" in head.lower():
        return "geo_series_matrix"
    if path.suffix.lower() == ".csv" or name.endswith(".csv.gz"):
        return "csv"
    if path.suffix.lower() in {".tsv", ".txt"} or name.endswith((".tsv.gz", ".txt.gz")):
        return "tsv"
    if "\t" in head:
        return "tsv"
    if "," in head.splitlines()[0] if head else False:
        return "csv"
    # Extensionless Xena matrices are tab-delimited.
    if path.suffix == "" or path.name.lower() in XENA_BASENAMES:
        return "tsv"
    return "unknown"


def _csv_out_path(dataset_dir: Path, out_dir: Path | None, name: str) -> Path:
    dest = out_dir if out_dir is not None else (dataset_dir / "csv")
    dest.mkdir(parents=True, exist_ok=True)
    return dest / name


def convert_tabular(path: Path, out: Path, *, force: bool) -> dict:
    if out.exists() and not force:
        return {"status": "skipped", "reason": "exists", "output": str(out)}

    with _open_text(path) as fh:
        sample = fh.read(8192)
        fh.seek(0)
        delim = _sniff_delimiter(sample)
        reader = csv.reader(fh, delimiter=delim)
        rows = list(reader)

    if not rows:
        return {"status": "error", "error": "empty file", "input": str(path)}

    with open(out, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerows(rows)

    return {
        "status": "ok",
        "input": str(path),
        "output": str(out),
        "format": "tabular",
        "n_rows": max(0, len(rows) - 1),
        "n_cols": len(rows[0]) if rows else 0,
    }


def _parse_char_field(raw: str) -> tuple[str | None, str]:
    """Split 'Key : Value' phenotype characteristics; else (None, raw)."""
    raw = _strip_quotes(raw)
    if " : " in raw:
        key, _, val = raw.partition(" : ")
        return key.strip(), val.strip()
    if ": " in raw:
        key, _, val = raw.partition(": ")
        return key.strip(), val.strip()
    return None, raw


def convert_geo_series_matrix(
    path: Path,
    dataset_dir: Path,
    out_dir: Path | None,
    *,
    force: bool,
    expression_only: bool,
) -> list[dict]:
    results: list[dict] = []
    sample_fields: dict[str, list[str]] = {}
    char_rows: list[list[str]] = []
    expression_rows: list[list[str]] = []
    in_table = False

    with _open_text(path) as fh:
        for raw in fh:
            line = raw.rstrip("\n\r")
            if line.startswith("!series_matrix_table_begin"):
                in_table = True
                continue
            if line.startswith("!series_matrix_table_end"):
                in_table = False
                continue
            if in_table:
                # GEO quotes every cell; csv handles it.
                row = [_strip_quotes(c) for c in next(csv.reader([line], delimiter="\t"))]
                expression_rows.append(row)
                continue
            if not line.startswith("!Sample_"):
                continue
            parts = [_strip_quotes(c) for c in next(csv.reader([line], delimiter="\t"))]
            if not parts:
                continue
            key = parts[0]
            vals = parts[1:]
            if key == "!Sample_characteristics_ch1":
                char_rows.append(vals)
            else:
                # Keep last occurrence for duplicate keys (rare).
                sample_fields[key] = vals

    # --- expression.csv ---
    expr_out = _csv_out_path(dataset_dir, out_dir, "expression.csv")
    if expr_out.exists() and not force:
        results.append({"status": "skipped", "reason": "exists", "output": str(expr_out)})
    elif not expression_rows:
        results.append({"status": "error", "error": "no expression table", "input": str(path)})
    else:
        with open(expr_out, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerows(expression_rows)
        results.append({
            "status": "ok",
            "input": str(path),
            "output": str(expr_out),
            "format": "geo_expression",
            "n_rows": max(0, len(expression_rows) - 1),
            "n_cols": len(expression_rows[0]) if expression_rows else 0,
        })

    if expression_only:
        return results

    # --- phenotype.csv (samples as rows) ---
    n_samples = 0
    for vals in sample_fields.values():
        n_samples = max(n_samples, len(vals))
    for vals in char_rows:
        n_samples = max(n_samples, len(vals))
    if n_samples == 0:
        results.append({"status": "error", "error": "no sample metadata", "input": str(path)})
        return results

    # Build column map: geo_accession first when present.
    columns: list[str] = []
    col_data: dict[str, list[str]] = {}

    def add_col(name: str, values: list[str]) -> None:
        padded = list(values) + [""] * (n_samples - len(values))
        if name in col_data:
            # Disambiguate duplicate metadata keys.
            i = 2
            while f"{name}_{i}" in col_data:
                i += 1
            name = f"{name}_{i}"
        columns.append(name)
        col_data[name] = padded[:n_samples]

    preferred = [
        "!Sample_geo_accession",
        "!Sample_title",
        "!Sample_source_name_ch1",
        "!Sample_description",
        "!Sample_platform_id",
        "!Sample_organism_ch1",
    ]
    for key in preferred:
        if key in sample_fields:
            add_col(key.removeprefix("!Sample_"), sample_fields.pop(key))

    # Expand characteristics: each !Sample_characteristics_ch1 line is usually
    # one "Key : Value" field across all samples (same key).
    char_idx = 0
    for vals in char_rows:
        aligned_keys: list[str | None] = []
        aligned_vals: list[str] = []
        for v in vals[:n_samples]:
            k, val = _parse_char_field(v)
            aligned_keys.append(k)
            aligned_vals.append(val)
        while len(aligned_vals) < n_samples:
            aligned_keys.append(None)
            aligned_vals.append("")
        named = [k for k in aligned_keys if k]
        if named and len(set(named)) == 1:
            add_col(named[0], aligned_vals)
        elif named:
            # Mixed keys on one line — keep raw cells.
            char_idx += 1
            add_col(f"characteristics_{char_idx}", vals)
        else:
            char_idx += 1
            add_col(f"characteristics_{char_idx}", vals)

    # Remaining !Sample_* fields.
    for key in sorted(sample_fields):
        short = key.removeprefix("!Sample_")
        # Skip bulky contact / protocol fields by default? Keep them — complete.
        add_col(short, sample_fields[key])

    pheno_out = _csv_out_path(dataset_dir, out_dir, "phenotype.csv")
    if pheno_out.exists() and not force:
        results.append({"status": "skipped", "reason": "exists", "output": str(pheno_out)})
        return results

    with open(pheno_out, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        for i in range(n_samples):
            writer.writerow([col_data[c][i] for c in columns])

    results.append({
        "status": "ok",
        "input": str(path),
        "output": str(pheno_out),
        "format": "geo_phenotype",
        "n_rows": n_samples,
        "n_cols": len(columns),
    })
    return results


def convert_parquet(path: Path, out: Path, *, force: bool) -> dict:
    if out.exists() and not force:
        return {"status": "skipped", "reason": "exists", "output": str(out)}
    try:
        import pandas as pd  # noqa: WPS433
    except ImportError:
        return {"status": "error", "error": "pandas+pyarrow required for parquet",
                "input": str(path)}
    df = pd.read_parquet(path)
    df.to_csv(out, index=False)
    return {
        "status": "ok", "input": str(path), "output": str(out),
        "format": "parquet", "n_rows": len(df), "n_cols": df.shape[1],
    }


def convert_excel(path: Path, out: Path, *, force: bool) -> dict:
    if out.exists() and not force:
        return {"status": "skipped", "reason": "exists", "output": str(out)}
    try:
        import pandas as pd  # noqa: WPS433
    except ImportError:
        return {"status": "error", "error": "pandas required for excel",
                "input": str(path)}
    # First sheet only; multi-sheet -> stem_sheetname.csv
    sheets = pd.read_excel(path, sheet_name=None)
    if len(sheets) == 1:
        name, df = next(iter(sheets.items()))
        df.to_csv(out, index=False)
        return {
            "status": "ok", "input": str(path), "output": str(out),
            "format": "excel", "sheet": name,
            "n_rows": len(df), "n_cols": df.shape[1],
        }
    results = []
    for name, df in sheets.items():
        safe = re.sub(r"[^\w\-]+", "_", str(name)).strip("_") or "sheet"
        sheet_out = out.with_name(f"{out.stem}_{safe}.csv")
        if sheet_out.exists() and not force:
            results.append({"status": "skipped", "reason": "exists",
                            "output": str(sheet_out)})
            continue
        df.to_csv(sheet_out, index=False)
        results.append({
            "status": "ok", "input": str(path), "output": str(sheet_out),
            "format": "excel", "sheet": name,
            "n_rows": len(df), "n_cols": df.shape[1],
        })
    return {"status": "ok", "outputs": results, "input": str(path)}


def is_data_file(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.name.startswith("."):
        return False
    low = path.name.lower()
    if low in SKIP_NAMES:
        return False
    if path.parent.name == "csv":
        return False  # don't re-convert outputs
    # Skip archives that aren't single-file gz data.
    if path.suffix.lower() == ".zip" or ".zip.part" in low:
        return False
    if any(low.endswith(s) for s in (".md", ".pdf", ".html", ".htm", ".xml", ".soft", ".tar")):
        return False
    # Accept known suffixes OR extensionless likely-tabular files.
    if path.suffix == "":
        return True
    if any(low.endswith(s) for s in (
        ".csv", ".tsv", ".txt", ".csv.gz", ".tsv.gz", ".txt.gz",
        ".parquet", ".xlsx", ".xls",
    )):
        return True
    # Lone .gz with unknown inner type — try.
    if low.endswith(".gz"):
        return True
    return False


def convert_file(
    path: Path,
    dataset_dir: Path,
    out_dir: Path | None,
    *,
    force: bool,
    expression_only: bool,
) -> list[dict]:
    fmt = detect_format(path)
    if fmt == "geo_series_matrix":
        return convert_geo_series_matrix(
            path, dataset_dir, out_dir, force=force,
            expression_only=expression_only,
        )

    stem = path.name
    for ext in (".txt.gz", ".tsv.gz", ".csv.gz", ".gz", ".txt", ".tsv", ".csv",
                ".parquet", ".xlsx", ".xls"):
        if stem.lower().endswith(ext):
            stem = stem[: -len(ext)]
            break
    stem = stem or path.stem
    out = _csv_out_path(dataset_dir, out_dir, f"{stem}.csv")

    if fmt in {"tsv", "csv"}:
        return [convert_tabular(path, out, force=force)]
    if fmt == "parquet":
        return [convert_parquet(path, out, force=force)]
    if fmt == "excel":
        res = convert_excel(path, out, force=force)
        return res.get("outputs", [res]) if isinstance(res, dict) else [res]

    return [{"status": "error", "error": f"unsupported format: {fmt}",
             "input": str(path)}]


def resolve_targets(path: Path | None, topic: str | None) -> list[Path]:
    """Return dataset directories (or a single file's parent dataset dir list)."""
    datasets_root = ws_path("datasets.dir", "datasets")
    if path is not None:
        p = path if path.is_absolute() else (WORKSPACE / path)
        if p.is_file():
            return [p]
        if p.is_dir():
            # topic dir vs single dataset dir
            children = [c for c in sorted(p.iterdir()) if c.is_dir() and c.name != "csv"]
            has_data = any(is_data_file(f) for f in p.iterdir() if f.is_file())
            if has_data and not any(is_data_file(f) for c in children for f in c.rglob("*") if f.is_file()):
                # Prefer treating as dataset dir if it directly contains data.
                return [p]
            if children and all((c / "REPORT.md").exists() or any(is_data_file(f) for f in c.iterdir() if f.is_file())
                                for c in children):
                return children
            return [p]
        raise SystemExit(f"path not found: {p}")

    if topic:
        topic_dir = datasets_root / topic
        if not topic_dir.is_dir():
            raise SystemExit(f"topic dir not found: {topic_dir}")
        return sorted(
            c for c in topic_dir.iterdir()
            if c.is_dir() and c.name != "csv"
        )

    raise SystemExit("provide --path or --topic")


def dataset_dir_for(target: Path) -> Path:
    if target.is_file():
        return target.parent
    return target


def collect_inputs(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    files = []
    for f in sorted(target.iterdir()):
        if is_data_file(f):
            files.append(f)
    return files


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", type=Path, help="Dataset dir, topic dir, or single file")
    ap.add_argument("--topic", help="Convert all datasets under datasets/<topic>/")
    ap.add_argument("--out-dir", type=Path,
                    help="Override output directory (default: <dataset>/csv/)")
    ap.add_argument("--force", action="store_true", help="Overwrite existing CSVs")
    ap.add_argument("--expression-only", action="store_true",
                    help="GEO: write expression.csv only (skip phenotype.csv)")
    args = ap.parse_args()

    targets = resolve_targets(args.path, args.topic)
    out_dir = args.out_dir
    if out_dir is not None and not out_dir.is_absolute():
        out_dir = WORKSPACE / out_dir

    all_results: list[dict] = []
    for target in targets:
        inputs = collect_inputs(target)
        ds_dir = dataset_dir_for(target)
        if not inputs:
            all_results.append({
                "status": "skipped", "reason": "no data files",
                "dataset": str(ds_dir),
            })
            continue
        for src in inputs:
            eprint(f"converting {src.relative_to(WORKSPACE) if src.is_relative_to(WORKSPACE) else src} ...")
            all_results.extend(
                convert_file(
                    src, ds_dir, out_dir,
                    force=args.force,
                    expression_only=args.expression_only,
                )
            )

    ok = sum(1 for r in all_results if r.get("status") == "ok")
    skipped = sum(1 for r in all_results if r.get("status") == "skipped")
    errors = sum(1 for r in all_results if r.get("status") == "error")
    pack_roots = []
    for r in all_results:
        for key in ("output", "input"):
            if r.get(key):
                pack_roots.append(Path(r[key]).parent)
    if pack_roots:
        try:
            import github_pack
            github_pack.hook_pack(pack_roots)
        except Exception as exc:  # noqa: BLE001
            eprint(f"! github-pack failed: {exc}")
    emit({
        "converted": ok,
        "skipped": skipped,
        "errors": errors,
        "results": all_results,
    })
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
