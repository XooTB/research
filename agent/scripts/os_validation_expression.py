#!/usr/bin/env python3
"""Build gene-symbol expression matrices for the HGSOC OS validation cohorts.

Stdlib only. Validation-side mirror of os_pool_expression.py: the label
table (os-validation/labels.csv, 892 patients / 410 deaths) defines the
analysis samples and column order; the merged matrix is restricted to the
training pool's 11,474 common symbols so a model trained on
os-training-pool/expression_pool.csv can be scored directly.

    python3 agent/scripts/os_validation_expression.py all
    python3 agent/scripts/os_validation_expression.py annotate
    python3 agent/scripts/os_validation_expression.py collapse
    python3 agent/scripts/os_validation_expression.py merge
    python3 agent/scripts/os_validation_expression.py verify

Inputs
------
os-validation/labels.csv (892 / 410; from os_validation_labels.py).
Training feature space: os-training-pool/expression_pool.symbols.txt
(11,474 symbols, sorted — the row order of every validation output).

Platform annotations (platform-annotations/REPORT.md, downloaded 27 Aug 2026):

    GPL6480.annot.gz                    Agilent 4x44K      ID -> Gene symbol
    GPL14951.platform_table.soft.gz     Illumina HT-12     ID -> Symbol
    GPL2986.annot.gz                    ABI HGS V2         ID -> Gene symbol

Same drop rules as the training side: empty/``---`` symbols, ``///``
multi-mappers, and ``AFFX-`` controls are dropped (Agilent/Illumina
control probes carry no symbol and fall to the empty rule).

Expression sources:

    gse32062-gpl6480-.../csv/expression.csv.zip   GPL6480, 41,093 probes (read from zip)
    gse53963-.../csv/expression.csv               GPL6480, 41,000 probes (two-color log-ratios)
    gse17260-.../csv/expression.csv               GPL6480, 41,000 probes
    gse140082-.../csv/expression.csv              GPL14951, 29,377 probes
    gse49997-.../csv/expression.csv               GPL2986, 32,878 probes

Pipeline
--------
1. annotate — parse each annotation into GPL*.probe2symbol.tsv.
2. collapse — per cohort, max-mean probe -> symbol on that cohort's
   labels.csv samples (identical rule to the training pool; source
   strings copied unchanged). Writes os-validation/expression/<cohort>.csv.
3. merge — write os-validation/expression_validation.csv with rows =
   the 11,474 training symbols and columns = all 892 sample_ids in
   labels.csv order. A symbol missing on a cohort's platform yields an
   empty cell (platform coverage is a property of the array, not of the
   model); per-cohort coverage goes into validation_manifest.json.
4. verify — dims == 11,474 x 892; columns == labels order; every cell
   is empty or a finite float; per-cohort column counts match labels.
   Exit nonzero on failure.

Known data-quality notes
------------------------
- GSE53963 is two-color (Cy5 tumor / Cy3 reference pool); the matrix
  holds one signed log-ratio per sample. Values are used as-is.
- GSM4153781 (gse140082, in the analysis set) has 9,440 empty probes —
  expect empty cells in its column after collapse.
- GSE53963 has ~32.8k empty cells spread across samples/probes.
- GSE32062's expression ships as expression.csv.zip; it is streamed
  from the zip, never unpacked to disk.
- The 10 GSE49997 excluded=yes GSMs are still columns on the expression
  matrix; the labels join ignores them.

If expression_validation.csv exceeds 100 MB, github_pack.py packs the
os-validation directory (GitHub blob limit).

References: docs/os-train-validation-split.md §4,
docs/os-training-expression.md (collapse rule rationale),
platform-annotations/REPORT.md.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import math
import subprocess
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Iterator, Sequence

# ---------------------------------------------------------------------------
# Paths / constants
# ---------------------------------------------------------------------------
WORKSPACE = Path(__file__).resolve().parents[2]
DATA_ROOT = WORKSPACE / "datasets" / "ovarian-cancer-prognosis-ml"
VAL_DIR = DATA_ROOT / "os-validation"
DEFAULT_LABELS = VAL_DIR / "labels.csv"
POOL_SYMBOLS = DATA_ROOT / "os-training-pool" / "expression_pool.symbols.txt"
ANNOT_DIR = DATA_ROOT / "platform-annotations"
EXPR_OUT_DIR = VAL_DIR / "expression"
VAL_CSV = VAL_DIR / "expression_validation.csv"
SYMBOLS_TXT = VAL_DIR / "expression_validation.symbols.txt"
MANIFEST_JSON = VAL_DIR / "validation_manifest.json"
PACK_SCRIPT = WORKSPACE / "agent" / "scripts" / "github_pack.py"
GITHUB_LIMIT = 100 * 1024 * 1024

SYMBOL_COL = "symbol"
COLLAPSE_RULE = (
    "Per symbol, among probes that map 1:1 onto that symbol (annotation "
    "drops empty/--- symbols, /// multi-mappers, and AFFX- controls), keep "
    "the probe with the highest mean expression across the cohort's "
    "os-validation/labels.csv analysis samples. Ties break on "
    "lexicographically smaller probe ID. Source numeric strings are copied "
    "unchanged — the mean is a selector, not a transform. Identical rule "
    "to the training pool (docs/os-training-expression.md)."
)

# Per-platform annotation source and symbol column.
PLATFORMS: dict[str, dict] = {
    "GPL6480": {"file": "GPL6480.annot.gz", "symbol_col": "Gene symbol"},
    "GPL14951": {"file": "GPL14951.platform_table.soft.gz", "symbol_col": "Symbol"},
    "GPL2986": {"file": "GPL2986.annot.gz", "symbol_col": "Gene symbol"},
}

# labels.csv cohort slug -> expression location.
# ``zip_member`` marks sources read straight out of a zip archive.
COHORTS: dict[str, dict] = {
    "gse32062": {
        "gpl": "GPL6480",
        "expr": "gse32062-gpl6480-ovarian-expression-series-matrix/csv/expression.csv.zip",
        "zip_member": "expression.csv",
        "expected_n": 260,
    },
    "gse53963": {
        "gpl": "GPL6480",
        "expr": "gse53963-ovarian-expression-series-matrix/csv/expression.csv",
        "expected_n": 160,
    },
    "gse17260": {
        "gpl": "GPL6480",
        "expr": "gse17260-ovarian-expression-series-matrix/csv/expression.csv",
        "expected_n": 110,
    },
    "gse140082": {
        "gpl": "GPL14951",
        "expr": "gse140082-ovarian-expression-series-matrix/csv/expression.csv",
        "expected_n": 191,
    },
    "gse49997": {
        "gpl": "GPL2986",
        "expr": "gse49997-ovarian-expression-series-matrix/csv/expression.csv",
        "expected_n": 171,
    },
}
COHORT_ORDER = list(COHORTS.keys())

_NA = frozenset({"", "na", "nan", "n/a", "none", ".", "null"})


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------
def eprint(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)


def _open_text(path: Path):
    if path.name.lower().endswith(".gz"):
        return io.TextIOWrapper(
            gzip.open(path, "rb"), encoding="utf-8", errors="replace", newline=""
        )
    return open(path, encoding="utf-8", errors="replace", newline="")


def _open_expr(path: Path, zip_member: str | None = None):
    """Expression handle; plain, .gz, or a member of a .zip archive."""
    if zip_member is not None:
        zf = zipfile.ZipFile(path)
        names = zf.namelist()
        if zip_member not in names:
            zf.close()
            raise SystemExit(f"{path}: member {zip_member!r} not in {names!r}")
        return _ZipText(zf, zip_member)
    return _open_text(path)


class _ZipText:
    """Context-manager wrapper so the ZipFile dies with the text handle."""

    def __init__(self, zf: zipfile.ZipFile, member: str):
        self._zf = zf
        self._fh = io.TextIOWrapper(
            zf.open(member), encoding="utf-8", errors="replace", newline=""
        )

    def __enter__(self):
        return self._fh

    def __exit__(self, *exc):
        self._fh.close()
        self._zf.close()
        return False


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def write_csv_row(fh, cells: Sequence[str]) -> None:
    # join is safe: GSM ids, symbols, and expression values contain no
    # commas/quotes (same assumption as the training-pool script).
    fh.write(",".join(cells))
    fh.write("\n")


# ---------------------------------------------------------------------------
# labels.csv
# ---------------------------------------------------------------------------
def load_labels(path: Path) -> list[dict[str, str]]:
    with _open_text(path) as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise SystemExit(f"empty labels file: {path}")
    return rows


def labels_by_cohort(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    by: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by[row["cohort"]].append(row)
    return by


def cohort_sample_ids(
    label_rows: list[dict[str, str]], slug: str
) -> tuple[list[str], list[str]]:
    """(output sample_ids, expression-column keys) in labels order.

    Every validation cohort joins expression on the GSM geo_accession.
    """
    out_ids: list[str] = []
    expr_keys: list[str] = []
    for row in label_rows:
        sid = (row.get("sample_id") or "").strip()
        key = (row.get("geo_accession") or "").strip()
        if not sid or not key:
            raise SystemExit(f"{slug}: blank sample_id / geo_accession in labels")
        out_ids.append(sid)
        expr_keys.append(key)
    return out_ids, expr_keys


# ---------------------------------------------------------------------------
# 1. annotate
# ---------------------------------------------------------------------------
def parse_annot_gz(path: Path, symbol_col: str) -> tuple[dict[str, str], dict]:
    """Return (probe->symbol, stats) applying the shared drop rules."""
    kept: dict[str, str] = {}
    stats = {
        "source": path.name,
        "symbol_column": symbol_col,
        "probe_rows": 0,
        "dropped_control": 0,
        "dropped_empty": 0,
        "dropped_multi": 0,
        "kept_probes": 0,
        "unique_symbols": 0,
    }
    header: list[str] | None = None
    id_i = 0
    sym_i = None
    with _open_text(path) as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if line.startswith("!platform_table_end"):
                break
            if not line or line[0] in "^!#":
                continue
            if header is None:
                header = line.split("\t")
                try:
                    id_i = header.index("ID")
                except ValueError:
                    id_i = 0
                try:
                    sym_i = header.index(symbol_col)
                except ValueError:
                    raise SystemExit(f"{path}: no {symbol_col!r} column in {header!r}")
                continue
            parts = line.split("\t")
            stats["probe_rows"] += 1
            probe = parts[id_i].strip() if id_i < len(parts) else ""
            symbol = parts[sym_i].strip() if sym_i < len(parts) else ""
            if not probe:
                stats["dropped_empty"] += 1
                continue
            # Exclusive drop-reason priority: control, then empty/---, then ///.
            if probe.upper().startswith("AFFX-") or probe.startswith("("):
                stats["dropped_control"] += 1
                continue
            if not symbol or symbol == "---":
                stats["dropped_empty"] += 1
                continue
            if "///" in symbol:
                stats["dropped_multi"] += 1
                continue
            kept[probe] = symbol
    stats["kept_probes"] = len(kept)
    stats["unique_symbols"] = len(set(kept.values()))
    return kept, stats


def write_probe2symbol(path: Path, mapping: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write("probe\tsymbol\n")
        for probe in sorted(mapping):
            fh.write(f"{probe}\t{mapping[probe]}\n")


def load_probe2symbol(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    with _open_text(path) as fh:
        reader = csv.reader(fh, delimiter="\t")
        header = next(reader, None)
        if not header:
            raise SystemExit(f"empty probe map: {path}")
        for row in reader:
            if len(row) >= 2 and row[0]:
                mapping[row[0]] = row[1]
    return mapping


def cmd_annotate(annot_dir: Path) -> dict:
    eprint("== annotate ==")
    out_stats: dict[str, dict] = {}
    for gpl, meta in PLATFORMS.items():
        src = annot_dir / meta["file"]
        if not src.exists():
            raise SystemExit(f"missing annotation: {src}")
        mapping, stats = parse_annot_gz(src, meta["symbol_col"])
        dest = annot_dir / f"{gpl}.probe2symbol.tsv"
        write_probe2symbol(dest, mapping)
        stats["path"] = dest.name
        out_stats[gpl] = stats
        eprint(
            f"  {gpl}: {stats['probe_rows']} probes -> "
            f"kept {stats['kept_probes']} / {stats['unique_symbols']} symbols "
            f"(drop control={stats['dropped_control']}, empty={stats['dropped_empty']}, "
            f"multi={stats['dropped_multi']}) -> {dest.name}"
        )
    return out_stats


# ---------------------------------------------------------------------------
# Expression streaming
# ---------------------------------------------------------------------------
def _column_indices(header: list[str], wanted: list[str], slug: str) -> list[int]:
    index = {name: i for i, name in enumerate(header)}
    missing = [w for w in wanted if w not in index]
    if missing:
        preview = ", ".join(missing[:8])
        extra = f" (+{len(missing) - 8} more)" if len(missing) > 8 else ""
        raise SystemExit(
            f"{slug}: {len(missing)} labels sample(s) missing from "
            f"expression header: {preview}{extra}"
        )
    return [index[w] for w in wanted]


def _is_na_token(cell: str) -> bool:
    return cell.strip().lower() in _NA


def row_mean(cells: list[str]) -> float | None:
    total = 0.0
    n = 0
    for cell in cells:
        if _is_na_token(cell):
            continue
        try:
            v = float(cell)
        except ValueError:
            continue
        if not math.isfinite(v):
            continue
        total += v
        n += 1
    if n == 0:
        return None
    return total / n


def iter_selected_rows(
    path: Path, expr_keys: list[str], slug: str, zip_member: str | None = None
) -> Iterator[tuple[str, list[str]]]:
    """Yield (row_id, selected_cells as original strings). Streams the file."""
    with _open_expr(path, zip_member) as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration:
            raise SystemExit(f"{slug}: empty expression file {path}")
        idxs = _column_indices(header, expr_keys, slug)
        extra = len(header) - 1 - len(set(expr_keys) & set(header[1:]))
        eprint(
            f"    {path.name}: {len(header) - 1} sample columns, "
            f"using {len(idxs)}; {extra} extra columns ignored"
        )
        for row in reader:
            if not row:
                continue
            rid = row[0].strip()
            cells = [(row[i] if i < len(row) else "") for i in idxs]
            yield rid, cells


# ---------------------------------------------------------------------------
# 2. collapse
# ---------------------------------------------------------------------------
def collapse_cohort(
    slug: str,
    expr_path: Path,
    out_ids: list[str],
    expr_keys: list[str],
    probe_map: dict[str, str],
    out_path: Path,
    zip_member: str | None = None,
) -> dict:
    """Two-pass max-mean collapse (same rule as the training pool)."""
    winner: dict[str, tuple[float, str]] = {}
    n_input = 0
    n_unmapped = 0
    n_no_mean = 0
    n_ties = 0
    for probe, cells in iter_selected_rows(expr_path, expr_keys, slug, zip_member):
        n_input += 1
        symbol = probe_map.get(probe)
        if symbol is None:
            n_unmapped += 1
            continue
        mean = row_mean(cells)
        if mean is None:
            n_no_mean += 1
            continue
        prev = winner.get(symbol)
        if prev is None:
            winner[symbol] = (mean, probe)
            continue
        prev_mean, prev_probe = prev
        if mean > prev_mean:
            winner[symbol] = (mean, probe)
        elif mean == prev_mean:
            n_ties += 1
            if probe < prev_probe:
                winner[symbol] = (mean, probe)

    winning_probe = {probe: symbol for symbol, (_m, probe) in winner.items()}
    eprint(
        f"    pass1 {slug}: {n_input} rows, {len(winner)} symbols, "
        f"unmapped={n_unmapped}, no_mean={n_no_mean}, ties={n_ties}"
    )

    values: dict[str, list[str]] = {}
    for probe, cells in iter_selected_rows(expr_path, expr_keys, slug, zip_member):
        symbol = winning_probe.get(probe)
        if symbol is None:
            continue
        values[symbol] = cells
        if len(values) == len(winning_probe):
            break

    missing_winners = len(winning_probe) - len(values)
    symbols_sorted = sorted(values)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        write_csv_row(fh, [SYMBOL_COL, *out_ids])
        for symbol in symbols_sorted:
            write_csv_row(fh, [symbol, *values[symbol]])

    return {
        "cohort": slug,
        "n_samples": len(out_ids),
        "n_input_rows": n_input,
        "n_unmapped_probes": n_unmapped,
        "n_probes_no_mean": n_no_mean,
        "n_mean_ties": n_ties,
        "n_winners_missing_on_pass2": missing_winners,
        "n_symbols_collapsed": len(symbols_sorted),
        "dims": [len(symbols_sorted), len(out_ids)],
        "path": out_path.as_posix(),
        "bytes": out_path.stat().st_size,
    }


def cmd_collapse(
    data_root: Path,
    labels_path: Path,
    annot_dir: Path,
    expr_out_dir: Path,
) -> dict[str, dict]:
    eprint("== collapse ==")
    labels = load_labels(labels_path)
    by = labels_by_cohort(labels)
    maps: dict[str, dict[str, str]] = {}
    for gpl in PLATFORMS:
        tsv = annot_dir / f"{gpl}.probe2symbol.tsv"
        if not tsv.exists():
            raise SystemExit(f"run annotate first; missing {tsv}")
        maps[gpl] = load_probe2symbol(tsv)
        eprint(f"  loaded {gpl} map: {len(maps[gpl])} probes")

    expr_out_dir.mkdir(parents=True, exist_ok=True)
    reports: dict[str, dict] = {}
    for slug in COHORT_ORDER:
        meta = COHORTS[slug]
        cohort_labels = by.get(slug, [])
        if len(cohort_labels) != meta["expected_n"]:
            eprint(
                f"  ! {slug}: labels has {len(cohort_labels)} rows, "
                f"expected {meta['expected_n']}"
            )
        out_ids, expr_keys = cohort_sample_ids(cohort_labels, slug)
        expr_path = data_root / meta["expr"]
        if not expr_path.exists():
            raise SystemExit(f"missing expression: {expr_path}")
        out_path = expr_out_dir / f"{slug}.csv"
        eprint(f"  {slug} ({meta['gpl']}, n={len(out_ids)}) <- {expr_path.name}")
        reports[slug] = collapse_cohort(
            slug,
            expr_path,
            out_ids,
            expr_keys,
            maps[meta["gpl"]],
            out_path,
            zip_member=meta.get("zip_member"),
        )
        dims = reports[slug]["dims"]
        eprint(
            f"    wrote {out_path.name}  {dims[0]} symbols x {dims[1]} samples "
            f"({reports[slug]['bytes'] / (1024 * 1024):.1f} MB)"
        )
    return reports


# ---------------------------------------------------------------------------
# 3. merge (into the training feature space)
# ---------------------------------------------------------------------------
def load_training_symbols(path: Path) -> list[str]:
    if not path.exists():
        raise SystemExit(
            f"missing training symbols: {path} — run os_pool_expression.py first"
        )
    symbols = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not symbols:
        raise SystemExit(f"empty training symbols file: {path}")
    return symbols


def load_collapsed_as_lookup(
    path: Path,
    expected_samples: list[str],
    keep: set[str] | None = None,
) -> dict[str, list[str]]:
    lookup: dict[str, list[str]] = {}
    with _open_text(path) as fh:
        reader = csv.reader(fh)
        header = next(reader)
        if header[:1] != [SYMBOL_COL]:
            raise SystemExit(f"{path}: first column is {header[:1]!r}, want ['{SYMBOL_COL}']")
        got = header[1:]
        if got != expected_samples:
            raise SystemExit(
                f"{path}: sample columns != labels order "
                f"(got {len(got)}, expected {len(expected_samples)})"
            )
        for row in reader:
            if not row:
                continue
            if keep is not None and row[0] not in keep:
                continue
            lookup[row[0]] = row[1:]
    return lookup


def cmd_merge(
    labels_path: Path,
    pool_symbols_path: Path,
    expr_out_dir: Path,
    val_csv: Path,
    symbols_txt: Path,
    manifest_path: Path,
    annot_stats: dict | None,
    collapse_reports: dict[str, dict] | None,
) -> dict:
    eprint("== merge ==")
    labels = load_labels(labels_path)
    by = labels_by_cohort(labels)
    all_sample_ids = [r["sample_id"] for r in labels]
    train_symbols = load_training_symbols(pool_symbols_path)
    keep = set(train_symbols)
    eprint(f"  training feature space: {len(train_symbols)} symbols")

    lookups: dict[str, dict[str, list[str]]] = {}
    cohort_out_ids: dict[str, list[str]] = {}
    coverage: dict[str, dict] = {}
    for slug in COHORT_ORDER:
        path = expr_out_dir / f"{slug}.csv"
        if not path.exists():
            raise SystemExit(f"run collapse first; missing {path}")
        out_ids, _keys = cohort_sample_ids(by[slug], slug)
        cohort_out_ids[slug] = out_ids
        lookup = load_collapsed_as_lookup(path, out_ids, keep=keep)
        lookups[slug] = lookup
        n_have = len(lookup)
        coverage[slug] = {
            "platform": COHORTS[slug]["gpl"],
            "n_training_symbols": len(train_symbols),
            "n_present": n_have,
            "n_missing": len(train_symbols) - n_have,
            "pct_present": round(100.0 * n_have / len(train_symbols), 2),
        }
        eprint(
            f"  {slug}: {n_have}/{len(train_symbols)} training symbols present "
            f"({coverage[slug]['pct_present']}%)"
        )

    col_index: dict[str, tuple[str, int]] = {}
    for slug, ids in cohort_out_ids.items():
        for i, sid in enumerate(ids):
            col_index[sid] = (slug, i)

    empty_cells = 0
    per_cohort_empty: dict[str, int] = {slug: 0 for slug in COHORT_ORDER}
    val_csv.parent.mkdir(parents=True, exist_ok=True)
    with val_csv.open("w", encoding="utf-8", newline="") as fh:
        write_csv_row(fh, [SYMBOL_COL, *all_sample_ids])
        for symbol in train_symbols:
            row_cells = [symbol]
            for sid in all_sample_ids:
                slug, i = col_index[sid]
                vals = lookups[slug].get(symbol)
                if vals is None or i >= len(vals) or vals[i] == "":
                    empty_cells += 1
                    per_cohort_empty[slug] += 1
                    row_cells.append("")
                else:
                    row_cells.append(vals[i])
            write_csv_row(fh, row_cells)

    symbols_txt.write_text("".join(s + "\n" for s in train_symbols), encoding="utf-8")
    val_bytes = val_csv.stat().st_size
    eprint(
        f"  wrote {val_csv.name}  {len(train_symbols)} x {len(all_sample_ids)}  "
        f"({val_bytes / (1024 * 1024):.1f} MB); empty cells: {empty_cells}"
    )

    packed = False
    pack_report: dict | None = None
    if val_bytes > GITHUB_LIMIT:
        eprint(f"  validation CSV is {val_bytes / (1024 * 1024):.1f} MB > 100 MB; packing")
        pack_report = _run_pack(val_csv.parent)
        packed = bool((pack_report or {}).get("packed"))
    else:
        eprint("  validation CSV under 100 MB; skipping github_pack")

    anomalies: list[str] = []
    for slug, info in (collapse_reports or {}).items():
        if info.get("n_winners_missing_on_pass2"):
            anomalies.append(
                f"{slug}: {info['n_winners_missing_on_pass2']} winners missing on pass 2"
            )
    for slug, n_empty in per_cohort_empty.items():
        if n_empty:
            anomalies.append(
                f"{slug}: {n_empty} empty cells in merged matrix "
                f"(platform lacks the symbol or source value empty)"
            )

    manifest = {
        "collapse_rule": COLLAPSE_RULE,
        "feature_space": (
            "Rows are exactly the training pool's common symbols "
            "(os-training-pool/expression_pool.symbols.txt). A symbol missing "
            "on a validation platform is an empty cell, not a dropped row."
        ),
        "annotation": annot_stats or {},
        "cohorts": collapse_reports or {},
        "coverage": coverage,
        "pool_symbols_source": _rel(pool_symbols_path, WORKSPACE),
        "validation": {
            "n_symbols": len(train_symbols),
            "n_samples": len(all_sample_ids),
            "dims": [len(train_symbols), len(all_sample_ids)],
            "path": _rel(val_csv, WORKSPACE),
            "symbols_path": _rel(symbols_txt, WORKSPACE),
            "bytes": val_bytes,
            "empty_cells": empty_cells,
            "per_cohort_empty_cells": per_cohort_empty,
            "column_order": "os-validation/labels.csv row order (sample_id)",
        },
        "expected_column_counts": {
            slug: COHORTS[slug]["expected_n"] for slug in COHORT_ORDER
        },
        "packed": packed,
        "pack_report": pack_report,
        "anomalies": anomalies,
    }
    for slug, info in (manifest["cohorts"] or {}).items():
        p = info.get("path")
        if p:
            info["path"] = _rel(Path(p), WORKSPACE)

    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    eprint(f"  wrote {manifest_path.name}")
    return manifest


def _run_pack(val_dir: Path) -> dict:
    cmd = [
        sys.executable,
        str(PACK_SCRIPT),
        "pack",
        "--path",
        str(val_dir),
    ]
    eprint("  $", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(WORKSPACE), capture_output=True, text=True)
    if result.returncode != 0:
        eprint(result.stderr or result.stdout)
        raise SystemExit(f"github_pack.py failed with exit {result.returncode}")
    text = (result.stdout or "").strip()
    try:
        return json.loads(text) if text else {"raw": result.stdout}
    except json.JSONDecodeError:
        return {"stdout": result.stdout, "stderr": result.stderr}


# ---------------------------------------------------------------------------
# 4. verify
# ---------------------------------------------------------------------------
def _finite_float(cell: str) -> bool:
    if cell.strip() == "" or _is_na_token(cell):
        return False
    try:
        v = float(cell)
    except ValueError:
        return False
    return math.isfinite(v)


def cmd_verify(
    labels_path: Path,
    val_csv: Path,
    symbols_txt: Path,
    manifest_path: Path | None = None,
) -> int:
    eprint("== verify ==")
    errors: list[str] = []
    labels = load_labels(labels_path)
    sample_ids = [r["sample_id"] for r in labels]
    by = labels_by_cohort(labels)
    expected_n = {slug: COHORTS[slug]["expected_n"] for slug in COHORT_ORDER}

    for slug, n_exp in expected_n.items():
        n_got = len(by.get(slug, []))
        if n_got != n_exp:
            errors.append(f"labels {slug}: {n_got} rows, expected {n_exp}")

    if not val_csv.exists():
        eprint(f"FAIL: missing {val_csv}")
        return 1
    if not symbols_txt.exists():
        errors.append(f"missing {symbols_txt}")

    symbols_file: list[str] = []
    if symbols_txt.exists():
        symbols_file = [
            line.strip()
            for line in symbols_txt.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    n_rows = 0
    n_empty = 0
    n_nonfloat = 0
    header: list[str] = []
    with _open_text(val_csv) as fh:
        reader = csv.reader(fh)
        header = next(reader, [])
        if not header or header[0] != SYMBOL_COL:
            errors.append(f"first header cell is {header[:1]!r}, want ['{SYMBOL_COL}']")
        cols = header[1:]
        if cols != sample_ids:
            if len(cols) != len(sample_ids):
                errors.append(f"column count {len(cols)} != labels n {len(sample_ids)}")
            else:
                n_mismatch = sum(1 for a, b in zip(cols, sample_ids) if a != b)
                errors.append(
                    f"sample_id columns not in labels.csv order ({n_mismatch} differ)"
                )
        for i, row in enumerate(reader):
            n_rows += 1
            if not row:
                errors.append(f"blank row at line {i + 2}")
                continue
            if symbols_file and i < len(symbols_file) and row[0] != symbols_file[i]:
                errors.append(
                    f"row {i + 1} symbol {row[0]!r} != symbols.txt {symbols_file[i]!r}"
                )
                if len(errors) > 20:
                    break
            if len(row) != 1 + len(sample_ids):
                errors.append(
                    f"row {row[0]!r}: {len(row) - 1} values, expected {len(sample_ids)}"
                )
                continue
            for cell in row[1:]:
                if cell == "" or _is_na_token(cell):
                    n_empty += 1
                elif not _finite_float(cell):
                    n_nonfloat += 1

    # Empty cells are legal on the validation side (platform coverage);
    # they are reported, not asserted away.
    if n_nonfloat:
        errors.append(f"{n_nonfloat} non-finite / non-float cells")
    if symbols_file and n_rows != len(symbols_file):
        errors.append(f"matrix has {n_rows} rows, symbols.txt has {len(symbols_file)}")
    if n_rows == 0:
        errors.append("expression_validation.csv has no data rows")

    eprint("  per-cohort columns (from labels order):")
    for slug in COHORT_ORDER:
        n = len(by.get(slug, []))
        flag = "OK" if n == expected_n[slug] else "FAIL"
        eprint(f"    {slug:16s} {n:4d}  (expected {expected_n[slug]}) {flag}")

    if header:
        eprint(
            f"  matrix: {n_rows} symbols x {len(header) - 1} samples  "
            f"({val_csv.stat().st_size / (1024 * 1024):.1f} MB)"
        )
    eprint(f"  empty cells (platform coverage / missing source): {n_empty}")

    if manifest_path and manifest_path.exists():
        man = json.loads(manifest_path.read_text(encoding="utf-8"))
        man_n = (man.get("validation") or {}).get("n_symbols")
        if man_n is not None and man_n != n_rows:
            errors.append(f"manifest n_symbols {man_n} != matrix rows {n_rows}")

    if errors:
        eprint(f"FAIL: {len(errors)} check(s)")
        for msg in errors:
            eprint("  -", msg)
        return 1
    eprint("OK: dims, column order, value parsing, per-cohort counts.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gene-symbol expression matrices for the held-out HGSOC validation cohorts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "subcommands:\n"
            "  all        annotate + collapse + merge + verify (default)\n"
            "  annotate   GPL6480/GPL14951/GPL2986 -> probe2symbol TSV\n"
            "  collapse   per-cohort max-mean probe->symbol matrices\n"
            "  merge      training-symbol rows -> expression_validation.csv\n"
            "  verify     assert dims, column order, value parsing\n"
        ),
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DATA_ROOT,
        help="datasets/ovarian-cancer-prognosis-ml",
    )
    parser.add_argument(
        "--labels",
        type=Path,
        default=DEFAULT_LABELS,
        help="os-validation/labels.csv",
    )
    parser.add_argument(
        "--pool-symbols",
        type=Path,
        default=POOL_SYMBOLS,
        help="training pool expression_pool.symbols.txt (the feature space)",
    )
    parser.add_argument(
        "--annot-dir",
        type=Path,
        default=ANNOT_DIR,
        help="platform-annotations/ (annotations in, probe2symbol TSV out)",
    )
    parser.add_argument(
        "--expr-out",
        type=Path,
        default=EXPR_OUT_DIR,
        help="per-cohort collapsed CSVs",
    )
    parser.add_argument(
        "--val-csv",
        type=Path,
        default=VAL_CSV,
        help="merged expression_validation.csv",
    )
    sub = parser.add_subparsers(dest="cmd")
    for name, help_ in (
        ("all", "run annotate, collapse, merge, verify"),
        ("annotate", "write probe->symbol maps"),
        ("collapse", "write per-cohort symbol matrices"),
        ("merge", "write the validation matrix in the training feature space"),
        ("verify", "assert the validation matrix"),
    ):
        sub.add_parser(name, help=help_)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cmd = args.cmd or "all"
    data_root: Path = args.data_root
    labels_path: Path = args.labels
    annot_dir: Path = args.annot_dir
    expr_out: Path = args.expr_out
    val_csv: Path = args.val_csv
    symbols_txt = val_csv.with_name("expression_validation.symbols.txt")
    manifest_path = val_csv.with_name("validation_manifest.json")

    if cmd == "annotate":
        cmd_annotate(annot_dir)
        return 0
    if cmd == "collapse":
        cmd_collapse(data_root, labels_path, annot_dir, expr_out)
        return 0
    if cmd == "merge":
        cmd_merge(
            labels_path,
            args.pool_symbols,
            expr_out,
            val_csv,
            symbols_txt,
            manifest_path,
            annot_stats=None,
            collapse_reports=None,
        )
        return 0
    if cmd == "verify":
        return cmd_verify(labels_path, val_csv, symbols_txt, manifest_path)
    if cmd != "all":
        eprint(f"unknown command: {cmd}")
        return 2

    annot_stats = cmd_annotate(annot_dir)
    collapse_reports = cmd_collapse(data_root, labels_path, annot_dir, expr_out)
    cmd_merge(
        labels_path,
        args.pool_symbols,
        expr_out,
        val_csv,
        symbols_txt,
        manifest_path,
        annot_stats=annot_stats,
        collapse_reports=collapse_reports,
    )
    return cmd_verify(labels_path, val_csv, symbols_txt, manifest_path)


if __name__ == "__main__":
    sys.exit(main())
