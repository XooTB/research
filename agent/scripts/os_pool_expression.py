#!/usr/bin/env python3
"""Build a gene-symbol expression matrix for the HGSOC OS training pool.

Stdlib only (csv, gzip, json, argparse, statistics, subprocess). The label
table is already done — this script is the expression half.

    python3 agent/scripts/os_pool_expression.py all
    python3 agent/scripts/os_pool_expression.py annotate
    python3 agent/scripts/os_pool_expression.py collapse
    python3 agent/scripts/os_pool_expression.py merge
    python3 agent/scripts/os_pool_expression.py verify

Inputs
------
labels.csv (751 patients / 485 deaths) defines the analysis samples and
column order. GEO cohorts match ``geo_accession`` to expression columns;
TCGA matches ``sample_id`` (barcode) to HiSeqV2 columns.

Platform annotations (GEO "Download annotation", dated Aug 09 2016; see
``datasets/ovarian-cancer-prognosis-ml/platform-annotations/REPORT.md``):

    GPL96.annot.gz   HG-U133A          (~22,283 probe sets)
    GPL570.annot.gz  HG-U133 Plus 2.0  (~54,675 probe sets)

Gzipped TSVs with a ``^`` / ``!`` / ``#`` metadata preamble, table bounds
``!platform_table_begin`` / ``!platform_table_end``, probe-set column ``ID``
and ``Gene symbol``. Modern GEO annotation *adds* gene symbols that the
original array design did not carry. The canonical example:

    1007_s_at  ->  MIR4640///DDR1

DDR1 is the gene this probe was designed against; MIR4640 is a microRNA
later annotated to the same locus. This pipeline **drops** that probe
(and every other ``///`` multi-mapper) rather than picking a side. That
is intentional: a frozen, reproducible map beats a slightly larger probe
count. Empty / ``---`` symbols and ``AFFX-`` control probes are dropped
too.

Expression CSVs (probe or symbol rows × sample columns; first column is
the row ID):

    tcga-ov-xena-rna-seq-hiseqv2/csv/HiSeqV2.csv
        20,530 rows; first column ``sample`` is already a gene symbol
        (RNA-seq, Xena log2-ish normalized). Sample columns are TCGA
        barcodes.
    gse26712-.../csv/expression.csv     GPL96,  22,283 probes, ``ID_REF``
    gse14764-.../csv/expression.csv     GPL96,  22,283 probes
    gse26193-.../csv/expression.csv     GPL570, 54,675 probes
    gse30161-.../csv/expression.csv     GPL570, 54,675 probes
    gse63885-.../csv/expression.csv     GPL570, 54,675 probes

Pipeline
--------
1. annotate
   Parse each GPL*.annot.gz into ``GPL*.probe2symbol.tsv`` (columns
   ``probe``, ``symbol``) under platform-annotations/. Drop empty/``---``
   symbols, drop multi-mappers containing ``///``, drop ``AFFX-`` controls.

2. collapse
   Per Affymetrix cohort: map probes → symbols via the TSV; for symbols
   with several probes keep the probe with the **highest mean expression
   across that cohort's labels.csv samples** (standard max-mean collapse).
   Ties break on lexicographically smaller probe ID. Write
   ``os-training-pool/expression/<cohort>.csv`` as symbol × sample, columns
   in labels.csv order, restricted to that cohort's analysis samples.

   TCGA is already gene symbols. Duplicate symbol rows (none expected in
   HiSeqV2) use the same max-mean rule; ties keep the first file order.
   Restricted to the 302 labels samples.

   Numeric strings are copied from the source CSV unchanged — means are
   used only to pick a winner, never to rewrite values.

3. merge
   Intersect the symbol sets of the three platform families in the pool
   (rnaseq_hiseqv2, GPL96-collapsed, GPL570-collapsed). Within a family
   that has several cohorts, the family set is the intersection of those
   cohorts so every sample on that family has a value. The split doc
   guessed ~12k common symbols (HiSeqV2 20,530 ∩ GPL96 ~13k ∩ GPL570
   ~20k); this script reports the real number.

   Write:
     os-training-pool/expression_pool.csv
         rows = common symbols (sorted), columns = all 751 sample_ids
         in labels.csv row order, first column named ``symbol``
     os-training-pool/expression_pool.symbols.txt
         one symbol per line, same order as the matrix rows
     os-training-pool/expression_manifest.json
         per-cohort dims, symbol counts at each stage, intersection
         size, collapse rule, anomalies

   If expression_pool.csv exceeds 100 MB, run github_pack.py on the
   pool directory (GitHub rejects blobs > 100 MB; the pack script owns
   the .gitignore block). Unpacked working copies stay on disk.

4. verify
   Assert dims == (n_common_symbols) × 751; labels.csv sample_ids appear
   as columns in order; no empty cells; every value is a finite float;
   per-cohort column counts match labels (302 / 185 / 70 / 79 / 47 / 68).
   Exit nonzero on failure.

Why max-mean (not IQR / median / average-of-probes)
---------------------------------------------------
Highest-mean probe is the field default for Affymetrix HG-U133 collapse
(Riester / curatedOvarianData / most MAS5-era signatures). It is
deterministic given a frozen annotation and a frozen sample list, and it
does not invent a new numeric scale. Averaging probes mixes distinct
isoform/cross-hybridization signals. IQR is for noise filtering, not
for choosing a representative.

References: docs/os-train-validation-split.md,
docs/os-training-labels.md, docs/os-training-expression.md,
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
from collections import defaultdict
from pathlib import Path
from typing import Iterator, Sequence

# ---------------------------------------------------------------------------
# Paths / constants
# ---------------------------------------------------------------------------
WORKSPACE = Path(__file__).resolve().parents[2]
DATA_ROOT = WORKSPACE / "datasets" / "ovarian-cancer-prognosis-ml"
POOL_DIR = DATA_ROOT / "os-training-pool"
DEFAULT_LABELS = POOL_DIR / "labels.csv"
ANNOT_DIR = DATA_ROOT / "platform-annotations"
EXPR_OUT_DIR = POOL_DIR / "expression"
POOL_CSV = POOL_DIR / "expression_pool.csv"
SYMBOLS_TXT = POOL_DIR / "expression_pool.symbols.txt"
MANIFEST_JSON = POOL_DIR / "expression_manifest.json"
PACK_SCRIPT = WORKSPACE / "agent" / "scripts" / "github_pack.py"
GITHUB_LIMIT = 100 * 1024 * 1024

SYMBOL_COL = "symbol"
COLLAPSE_RULE = (
    "Per symbol, among probes that map 1:1 onto that symbol (annotation "
    "drops empty/--- symbols, /// multi-mappers, and AFFX- controls), keep "
    "the probe with the highest mean expression across the cohort's "
    "labels.csv analysis samples. Ties break on lexicographically smaller "
    "probe ID (Affy) or earlier file order (RNA-seq duplicate rows). "
    "Source numeric strings are copied unchanged — the mean is a selector, "
    "not a transform. TCGA HiSeqV2 rows are already gene symbols and use "
    "the same max-mean rule if a symbol appears more than once."
)

# labels.csv cohort slug -> expression location and how to match columns
COHORTS: dict[str, dict] = {
    "tcga-ov-hiseqv2": {
        "family": "rnaseq_hiseqv2",
        "gpl": None,
        "id_field": "sample_id",
        "expr": "tcga-ov-xena-rna-seq-hiseqv2/csv/HiSeqV2.csv",
        "expected_n": 302,
    },
    "gse26712": {
        "family": "GPL96",
        "gpl": "GPL96",
        "id_field": "geo_accession",
        "expr": "gse26712-ovarian-expression-series-matrix/csv/expression.csv",
        "expected_n": 185,
    },
    "gse63885": {
        "family": "GPL570",
        "gpl": "GPL570",
        "id_field": "geo_accession",
        "expr": "gse63885-ovarian-expression-series-matrix/csv/expression.csv",
        "expected_n": 70,
    },
    "gse26193": {
        "family": "GPL570",
        "gpl": "GPL570",
        "id_field": "geo_accession",
        "expr": "gse26193-ovarian-expression-series-matrix/csv/expression.csv",
        "expected_n": 79,
    },
    "gse30161": {
        "family": "GPL570",
        "gpl": "GPL570",
        "id_field": "geo_accession",
        "expr": "gse30161-ovarian-expression-series-matrix/csv/expression.csv",
        "expected_n": 47,
    },
    "gse14764": {
        "family": "GPL96",
        "gpl": "GPL96",
        "id_field": "geo_accession",
        "expr": "gse14764-ovarian-expression-series-matrix/csv/expression.csv",
        "expected_n": 68,
    },
}

# labels.csv is written in this order; pool columns follow labels row order
# which is the same sequence.
COHORT_ORDER = list(COHORTS.keys())
FAMILY_ORDER = ["rnaseq_hiseqv2", "GPL96", "GPL570"]
PLATFORMS = ("GPL96", "GPL570")

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


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def write_csv_row(fh, cells: Sequence[str]) -> None:
    # csv.writer would quote some numeric strings in edge cases; join is
    # safe here because IDs and MAS5/Xena values contain no commas/quotes.
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
    """Return (output sample_ids, expression-column keys) in labels order."""
    meta = COHORTS[slug]
    field = meta["id_field"]
    out_ids: list[str] = []
    expr_keys: list[str] = []
    for row in label_rows:
        sid = (row.get("sample_id") or "").strip()
        key = (row.get(field) or "").strip()
        if not sid or not key:
            raise SystemExit(f"{slug}: blank sample_id / {field} in labels")
        out_ids.append(sid)
        expr_keys.append(key)
    return out_ids, expr_keys


# ---------------------------------------------------------------------------
# 1. annotate
# ---------------------------------------------------------------------------
def parse_annot_gz(path: Path) -> tuple[dict[str, str], dict]:
    """Return (probe->symbol, stats) applying the drop rules."""
    kept: dict[str, str] = {}
    stats = {
        "source": path.name,
        "annotation_date": "",
        "annotation_platform": "",
        "probe_rows": 0,
        "dropped_affx": 0,
        "dropped_empty": 0,
        "dropped_multi": 0,
        "kept_probes": 0,
        "unique_symbols": 0,
        "example_dropped_multi": "1007_s_at -> MIR4640///DDR1",
    }
    header: list[str] | None = None
    id_i = 0
    sym_i = None
    with _open_text(path) as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if line.startswith("!Annotation_date"):
                stats["annotation_date"] = line.split("=", 1)[-1].strip()
                continue
            if line.startswith("!Annotation_platform ="):
                stats["annotation_platform"] = line.split("=", 1)[-1].strip()
                continue
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
                    sym_i = header.index("Gene symbol")
                except ValueError:
                    raise SystemExit(f"{path}: no 'Gene symbol' column")
                continue
            parts = line.split("\t")
            stats["probe_rows"] += 1
            probe = parts[id_i].strip() if id_i < len(parts) else ""
            symbol = parts[sym_i].strip() if sym_i < len(parts) else ""
            if not probe:
                stats["dropped_empty"] += 1
                continue
            # Exclusive drop-reason priority: AFFX, then empty/---, then ///.
            if probe.upper().startswith("AFFX-"):
                stats["dropped_affx"] += 1
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
    for gpl in PLATFORMS:
        src = annot_dir / f"{gpl}.annot.gz"
        if not src.exists():
            raise SystemExit(f"missing annotation: {src}")
        mapping, stats = parse_annot_gz(src)
        dest = annot_dir / f"{gpl}.probe2symbol.tsv"
        write_probe2symbol(dest, mapping)
        stats["path"] = dest.name
        out_stats[gpl] = stats
        eprint(
            f"  {gpl}: {stats['probe_rows']} probes → "
            f"kept {stats['kept_probes']} / {stats['unique_symbols']} symbols "
            f"(drop AFFX={stats['dropped_affx']}, empty={stats['dropped_empty']}, "
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
    path: Path, expr_keys: list[str], slug: str
) -> Iterator[tuple[str, list[str]]]:
    """Yield (row_id, selected_cells as original strings). Streams the file."""
    with _open_text(path) as fh:
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
def collapse_affy_cohort(
    slug: str,
    expr_path: Path,
    out_ids: list[str],
    expr_keys: list[str],
    probe_map: dict[str, str],
    out_path: Path,
) -> dict:
    """Two-pass max-mean collapse for one Affymetrix cohort."""
    # Pass 1: mean per mapped probe; keep the winning probe per symbol.
    # winner[symbol] = (mean, probe_id)
    winner: dict[str, tuple[float, str]] = {}
    n_input = 0
    n_unmapped = 0
    n_no_mean = 0
    n_ties = 0
    for probe, cells in iter_selected_rows(expr_path, expr_keys, slug):
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

    # Pass 2: copy the winning probe's original strings.
    values: dict[str, list[str]] = {}
    for probe, cells in iter_selected_rows(expr_path, expr_keys, slug):
        symbol = winning_probe.get(probe)
        if symbol is None:
            continue
        values[symbol] = cells
        if len(values) == len(winning_probe):
            break  # all winners collected

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


def collapse_rnaseq_cohort(
    slug: str,
    expr_path: Path,
    out_ids: list[str],
    expr_keys: list[str],
    out_path: Path,
) -> dict:
    """HiSeqV2: already gene symbols. Max-mean if a symbol repeats."""
    winner_mean: dict[str, float] = {}
    winner_cells: dict[str, list[str]] = {}
    n_input = 0
    n_empty = 0
    n_multi = 0
    n_dups = 0
    n_ties = 0
    n_no_mean = 0
    for symbol, cells in iter_selected_rows(expr_path, expr_keys, slug):
        n_input += 1
        if not symbol or symbol == "---":
            n_empty += 1
            continue
        if "///" in symbol:
            n_multi += 1
            continue
        mean = row_mean(cells)
        if mean is None:
            n_no_mean += 1
            continue
        prev = winner_mean.get(symbol)
        if prev is None:
            winner_mean[symbol] = mean
            winner_cells[symbol] = cells
            continue
        n_dups += 1
        if mean > prev:
            winner_mean[symbol] = mean
            winner_cells[symbol] = cells
        elif mean == prev:
            n_ties += 1
            # keep first-seen (file order) — already stored

    symbols_sorted = sorted(winner_cells)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        write_csv_row(fh, [SYMBOL_COL, *out_ids])
        for symbol in symbols_sorted:
            write_csv_row(fh, [symbol, *winner_cells[symbol]])

    return {
        "cohort": slug,
        "n_samples": len(out_ids),
        "n_input_rows": n_input,
        "n_empty_symbols": n_empty,
        "n_multi_symbols": n_multi,
        "n_duplicate_symbol_rows": n_dups,
        "n_mean_ties": n_ties,
        "n_rows_no_mean": n_no_mean,
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
        eprint(f"  {slug} ({meta['family']}, n={len(out_ids)}) <- {expr_path.name}")
        if meta["gpl"] is None:
            reports[slug] = collapse_rnaseq_cohort(
                slug, expr_path, out_ids, expr_keys, out_path
            )
        else:
            reports[slug] = collapse_affy_cohort(
                slug, expr_path, out_ids, expr_keys, maps[meta["gpl"]], out_path
            )
        dims = reports[slug]["dims"]
        eprint(
            f"    wrote {out_path.name}  {dims[0]} symbols × {dims[1]} samples "
            f"({reports[slug]['bytes'] / (1024 * 1024):.1f} MB)"
        )
    return reports


# ---------------------------------------------------------------------------
# 3. merge
# ---------------------------------------------------------------------------
def read_symbol_list(path: Path) -> list[str]:
    """First-column symbols from a collapsed CSV (header skipped). Streams."""
    symbols: list[str] = []
    with _open_text(path) as fh:
        reader = csv.reader(fh)
        next(reader, None)
        for row in reader:
            if row and row[0]:
                symbols.append(row[0])
    return symbols


def load_collapsed_as_lookup(
    path: Path,
    expected_samples: list[str],
    keep: set[str] | None = None,
) -> dict[str, list[str]]:
    """symbol -> list of original-string values, aligned to expected_samples.

    Collapsed matrices are already gene-level (~12–21k rows × ≤302 cols).
    ``keep`` (the 3-family intersection) drops symbols we will not write.
    """
    lookup: dict[str, list[str]] = {}
    with _open_text(path) as fh:
        reader = csv.reader(fh)
        header = next(reader)
        if header[:1] != [SYMBOL_COL]:
            raise SystemExit(f"{path}: first column is {header[:1]!r}, want ['{SYMBOL_COL}']")
        got = header[1:]
        if got != expected_samples:
            if set(got) == set(expected_samples) and len(got) == len(expected_samples):
                raise SystemExit(
                    f"{path}: sample columns are a permutation of labels order"
                )
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
    expr_out_dir: Path,
    pool_csv: Path,
    symbols_txt: Path,
    manifest_path: Path,
    annot_stats: dict | None,
    collapse_reports: dict[str, dict] | None,
) -> dict:
    eprint("== merge ==")
    labels = load_labels(labels_path)
    by = labels_by_cohort(labels)
    all_sample_ids = [r["sample_id"] for r in labels]
    if len(all_sample_ids) != 751:
        eprint(f"  ! labels has {len(all_sample_ids)} rows, expected 751")

    family_cohorts: dict[str, list[str]] = defaultdict(list)
    cohort_symbols: dict[str, set[str]] = {}
    for slug in COHORT_ORDER:
        path = expr_out_dir / f"{slug}.csv"
        if not path.exists():
            raise SystemExit(f"run collapse first; missing {path}")
        syms = set(read_symbol_list(path))
        cohort_symbols[slug] = syms
        family_cohorts[COHORTS[slug]["family"]].append(slug)
        eprint(f"  {slug}: {len(syms)} symbols")

    family_sets: dict[str, set[str]] = {}
    family_info: dict[str, dict] = {}
    for family in FAMILY_ORDER:
        slugs = family_cohorts[family]
        sets = [cohort_symbols[s] for s in slugs]
        union = set.union(*sets) if sets else set()
        inter = set.intersection(*sets) if sets else set()
        family_sets[family] = inter
        family_info[family] = {
            "cohorts": slugs,
            "n_symbols_union": len(union),
            "n_symbols_intersection": len(inter),
            "within_family_only_in_some_cohorts": sorted(union - inter)[:20],
            "n_only_in_some_cohorts": len(union - inter),
        }
        eprint(
            f"  family {family}: intersection {len(inter)} "
            f"(union {len(union)}; {len(union - inter)} not in every cohort)"
        )

    common = set.intersection(*(family_sets[f] for f in FAMILY_ORDER))
    common_sorted = sorted(common)
    eprint(f"  3-family intersection: {len(common_sorted)} symbols")

    # Load collapsed matrices (gene-level — much smaller than probe matrices)
    # and emit the pool in labels.csv column order.
    lookups: dict[str, dict[str, list[str]]] = {}
    cohort_out_ids: dict[str, list[str]] = {}
    for slug in COHORT_ORDER:
        out_ids, _keys = cohort_sample_ids(by[slug], slug)
        cohort_out_ids[slug] = out_ids
        lookups[slug] = load_collapsed_as_lookup(
            expr_out_dir / f"{slug}.csv", out_ids, keep=common
        )

    # Precompute (slug, column_index) for each pool column.
    col_index: dict[str, tuple[str, int]] = {}
    for slug, ids in cohort_out_ids.items():
        for i, sid in enumerate(ids):
            col_index[sid] = (slug, i)

    anomalies: list[str] = []
    missing_cells = 0
    pool_csv.parent.mkdir(parents=True, exist_ok=True)
    with pool_csv.open("w", encoding="utf-8", newline="") as fh:
        write_csv_row(fh, [SYMBOL_COL, *all_sample_ids])
        for symbol in common_sorted:
            row_cells = [symbol]
            for sid in all_sample_ids:
                slug, i = col_index[sid]
                vals = lookups[slug].get(symbol)
                if vals is None or i >= len(vals) or vals[i] == "":
                    missing_cells += 1
                    row_cells.append("")
                else:
                    row_cells.append(vals[i])
            write_csv_row(fh, row_cells)

    if missing_cells:
        anomalies.append(f"{missing_cells} empty cells written (should be 0)")

    symbols_txt.write_text("".join(s + "\n" for s in common_sorted), encoding="utf-8")
    pool_bytes = pool_csv.stat().st_size
    eprint(
        f"  wrote {pool_csv.name}  {len(common_sorted)} × {len(all_sample_ids)}  "
        f"({pool_bytes / (1024 * 1024):.1f} MB)"
    )

    packed = False
    pack_report: dict | None = None
    if pool_bytes > GITHUB_LIMIT:
        eprint(
            f"  pool CSV is {pool_bytes / (1024 * 1024):.1f} MB > 100 MB; packing"
        )
        pack_report = _run_pack(pool_csv.parent)
        packed = bool((pack_report or {}).get("packed"))
    else:
        eprint("  pool CSV under 100 MB; skipping github_pack")

    # HiSeq duplicate note from collapse report
    tcga = (collapse_reports or {}).get("tcga-ov-hiseqv2") or {}
    if tcga.get("n_duplicate_symbol_rows"):
        anomalies.append(
            f"HiSeqV2 had {tcga['n_duplicate_symbol_rows']} duplicate symbol rows"
        )
    else:
        # explicit negative finding — useful in the doc
        pass

    for slug, info in (collapse_reports or {}).items():
        if info.get("n_winners_missing_on_pass2"):
            anomalies.append(
                f"{slug}: {info['n_winners_missing_on_pass2']} winners missing on pass 2"
            )

    for family, info in family_info.items():
        if info["n_only_in_some_cohorts"]:
            anomalies.append(
                f"{family}: {info['n_only_in_some_cohorts']} symbols not in every "
                f"cohort of this family (dropped from family intersection)"
            )

    def rel_pool(p: Path) -> str:
        return _rel(p, WORKSPACE)

    manifest = {
        "collapse_rule": COLLAPSE_RULE,
        "annotation_notes": (
            "GEO GPL96/GPL570 annotations dated Aug 09 2016. Multi-mapping "
            "probes (///) are dropped rather than resolved, including "
            "1007_s_at -> MIR4640///DDR1. Reproducibility over maximal "
            "probe count. Provenance: platform-annotations/REPORT.md."
        ),
        "annotation": annot_stats or {},
        "cohorts": collapse_reports or {},
        "platform_families": {
            f: {**family_info[f], "n_symbols": len(family_sets[f])}
            for f in FAMILY_ORDER
        },
        "intersection_size": len(common_sorted),
        "pool": {
            "n_symbols": len(common_sorted),
            "n_samples": len(all_sample_ids),
            "dims": [len(common_sorted), len(all_sample_ids)],
            "path": rel_pool(pool_csv),
            "symbols_path": rel_pool(symbols_txt),
            "bytes": pool_bytes,
            "column_order": "labels.csv row order (sample_id)",
        },
        "expected_column_counts": {
            slug: COHORTS[slug]["expected_n"] for slug in COHORT_ORDER
        },
        "packed": packed,
        "pack_report": pack_report,
        "anomalies": anomalies,
    }
    # Paths inside collapse reports are absolute; relativize for the file.
    for slug, info in (manifest["cohorts"] or {}).items():
        p = info.get("path")
        if p:
            info["path"] = rel_pool(Path(p))

    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    eprint(f"  wrote {manifest_path.name}")
    return manifest


def _run_pack(pool_dir: Path) -> dict:
    cmd = [
        sys.executable,
        str(PACK_SCRIPT),
        "pack",
        "--path",
        str(pool_dir),
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
    pool_csv: Path,
    symbols_txt: Path,
    manifest_path: Path | None = None,
) -> int:
    eprint("== verify ==")
    errors: list[str] = []
    labels = load_labels(labels_path)
    sample_ids = [r["sample_id"] for r in labels]
    by = labels_by_cohort(labels)
    expected_n = {slug: COHORTS[slug]["expected_n"] for slug in COHORT_ORDER}

    if len(sample_ids) != 751:
        errors.append(f"labels.csv has {len(sample_ids)} rows, expected 751")

    for slug, n_exp in expected_n.items():
        n_got = len(by.get(slug, []))
        if n_got != n_exp:
            errors.append(f"labels {slug}: {n_got} rows, expected {n_exp}")

    if not pool_csv.exists():
        eprint(f"FAIL: missing {pool_csv}")
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

    n_common = len(symbols_file)
    if n_common == 0:
        errors.append("symbols.txt is empty")

    n_rows = 0
    n_empty = 0
    n_nonfloat = 0
    header: list[str] = []
    with _open_text(pool_csv) as fh:
        reader = csv.reader(fh)
        header = next(reader, [])
        if not header or header[0] != SYMBOL_COL:
            errors.append(f"first header cell is {header[:1]!r}, want ['{SYMBOL_COL}']")
        cols = header[1:]
        if cols != sample_ids:
            if len(cols) != len(sample_ids):
                errors.append(
                    f"column count {len(cols)} != labels n {len(sample_ids)}"
                )
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

    if n_empty:
        errors.append(f"{n_empty} empty/NA cells")
    if n_nonfloat:
        errors.append(f"{n_nonfloat} non-finite / non-float cells")
    if n_common and n_rows != n_common:
        errors.append(f"matrix has {n_rows} rows, symbols.txt has {n_common}")
    if n_rows == 0:
        errors.append("expression_pool.csv has no data rows")

    # Per-cohort column counts from labels (columns == labels sample_ids).
    eprint("  per-cohort columns (from labels order):")
    for slug in COHORT_ORDER:
        n = len(by.get(slug, []))
        flag = "OK" if n == expected_n[slug] else "FAIL"
        eprint(f"    {slug:16s} {n:4d}  (expected {expected_n[slug]}) {flag}")

    if header:
        eprint(
            f"  matrix: {n_rows} symbols × {len(header) - 1} samples  "
            f"({pool_csv.stat().st_size / (1024 * 1024):.1f} MB)"
        )
    eprint(f"  intersection size: {n_rows}")

    if manifest_path and manifest_path.exists():
        man = json.loads(manifest_path.read_text(encoding="utf-8"))
        man_n = (man.get("pool") or {}).get("n_symbols")
        if man_n is not None and man_n != n_rows:
            errors.append(f"manifest n_symbols {man_n} != matrix rows {n_rows}")

    if errors:
        eprint(f"FAIL: {len(errors)} check(s)")
        for msg in errors:
            eprint("  -", msg)
        return 1
    eprint("OK: dims, column order, finite values, per-cohort counts.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gene-symbol expression matrix for the HGSOC OS training pool.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "subcommands:\n"
            "  all        annotate + collapse + merge + verify (default)\n"
            "  annotate   GPL96/GPL570 -> probe2symbol TSV\n"
            "  collapse   per-cohort max-mean probe->symbol matrices\n"
            "  merge      3-family symbol intersection -> expression_pool.csv\n"
            "  verify     assert pool dims, column order, finite values\n"
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
        help="os-training-pool/labels.csv",
    )
    parser.add_argument(
        "--annot-dir",
        type=Path,
        default=ANNOT_DIR,
        help="platform-annotations/ (GPL*.annot.gz in, probe2symbol TSV out)",
    )
    parser.add_argument(
        "--expr-out",
        type=Path,
        default=EXPR_OUT_DIR,
        help="per-cohort collapsed CSVs",
    )
    parser.add_argument(
        "--pool-csv",
        type=Path,
        default=POOL_CSV,
        help="merged expression_pool.csv",
    )
    sub = parser.add_subparsers(dest="cmd")
    for name, help_ in (
        ("all", "run annotate, collapse, merge, verify"),
        ("annotate", "write probe->symbol maps"),
        ("collapse", "write per-cohort symbol matrices"),
        ("merge", "intersect families and write the pool matrix"),
        ("verify", "assert the pool matrix"),
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
    pool_csv: Path = args.pool_csv
    symbols_txt = pool_csv.with_name("expression_pool.symbols.txt")
    manifest_path = pool_csv.with_name("expression_manifest.json")

    if cmd == "annotate":
        cmd_annotate(annot_dir)
        return 0
    if cmd == "collapse":
        cmd_collapse(data_root, labels_path, annot_dir, expr_out)
        return 0
    if cmd == "merge":
        cmd_merge(
            labels_path,
            expr_out,
            pool_csv,
            symbols_txt,
            manifest_path,
            annot_stats=None,
            collapse_reports=None,
        )
        return 0
    if cmd == "verify":
        return cmd_verify(labels_path, pool_csv, symbols_txt, manifest_path)
    if cmd != "all":
        eprint(f"unknown command: {cmd}")
        return 2

    annot_stats = cmd_annotate(annot_dir)
    collapse_reports = cmd_collapse(data_root, labels_path, annot_dir, expr_out)
    cmd_merge(
        labels_path,
        expr_out,
        pool_csv,
        symbols_txt,
        manifest_path,
        annot_stats=annot_stats,
        collapse_reports=collapse_reports,
    )
    return cmd_verify(labels_path, pool_csv, symbols_txt, manifest_path)


if __name__ == "__main__":
    sys.exit(main())
