#!/usr/bin/env python3
"""Sync paper_datasets links from extractor output.

Reads the extraction CSV (paper slug, kind, value, url, context) produced by
paper_datasets_extract.py, matches paper slugs against papers.pdf_path and
accessions / named resources against tracked datasets, then inserts
paper_datasets rows via db.link_paper_dataset.

Importable: call sync_links(conn, csv_path, topic) from other scripts
(paper_datasets_extract / datasets_add do this automatically after writing
extraction CSVs or adding datasets).

Usage:
    paper_dataset_links.py [--csv PATH] [--topic TOPIC]
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path

import db
from common import emit, eprint, ws_path

# kinds that can never correspond to a tracked dataset row
SKIP_KINDS = {"DOI", "url", "EGA", "name:Bioconductor", "SRA/BioProject", "dbGaP"}

GSE_RE = re.compile(r"GSE\d+")
CONTEXT_MAX = 300


def find_paper(conn, slug: str, topic: str):
    rows = conn.execute(
        "SELECT id FROM papers WHERE topic=? AND pdf_path LIKE '%' || ? || '%'",
        (topic, slug),
    ).fetchall()
    if not rows:
        return None
    if len(rows) > 1:
        eprint(f"warning: slug {slug} matched {len(rows)} papers; using first")
    return rows[0]["id"]


def find_datasets(conn, kind: str, value: str, topic: str) -> list[int]:
    if kind == "GEO series":
        m = GSE_RE.search(value or "")
        if not m:
            return []
        acc = m.group(0)
        rows = conn.execute(
            "SELECT id FROM datasets WHERE topic=? AND (name LIKE '%' || ? || '%'"
            " OR url LIKE '%' || ? || '%')",
            (topic, acc, acc),
        ).fetchall()
        return [r["id"] for r in rows]
    if kind == "name:TCGA":
        rows = conn.execute(
            "SELECT id FROM datasets WHERE topic=? AND name LIKE 'TCGA-OV%'",
            (topic,),
        ).fetchall()
        return [r["id"] for r in rows]
    return []


def sync_links(conn, csv_path: Path, topic: str) -> dict:
    """(Re)link papers to datasets for one topic from an extraction CSV.

    Idempotent (INSERT OR IGNORE). Returns a report dict; does not close conn.
    """
    csv_path = Path(csv_path)
    created = 0
    existing = 0
    skipped: Counter = Counter()
    unmatched: set[str] = set()
    unmatched_papers: set[str] = set()

    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    eprint(f"read {len(rows)} findings from {csv_path}")

    for row in rows:
        kind, value = row["kind"], (row["value"] or "").strip()
        slug = row["paper"]

        if kind in SKIP_KINDS or kind not in ("GEO series", "name:TCGA"):
            skipped[kind] += 1
            continue

        paper_id = find_paper(conn, slug, topic)
        if paper_id is None:
            unmatched_papers.add(slug)
            skipped[f"paper-not-found:{kind}"] += 1
            continue

        ds_ids = find_datasets(conn, kind, value, topic)
        if not ds_ids:
            m = GSE_RE.search(value)
            unmatched.add(m.group(0) if kind == "GEO series" and m else value)
            continue

        evidence = f"{kind}:{value}"
        context = (row.get("context") or "").strip() or None
        if context and len(context) > CONTEXT_MAX:
            context = context[:CONTEXT_MAX]

        for ds_id in ds_ids:
            if db.link_paper_dataset(conn, paper_id, ds_id, evidence, context):
                created += 1
            else:
                existing += 1

    total = conn.execute("SELECT COUNT(*) c FROM paper_datasets").fetchone()["c"]
    return {
        "csv": str(csv_path),
        "topic": topic,
        "links_created": created,
        "links_already_existing": existing,
        "skipped_by_kind": dict(skipped),
        "unmatched_accessions": sorted(unmatched),
        "unmatched_papers": sorted(unmatched_papers),
        "paper_datasets_total": total,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=None, help="extraction CSV path")
    ap.add_argument("--topic", default="ovarian-cancer-prognosis-ml")
    args = ap.parse_args()

    csv_path = Path(args.csv) if args.csv else ws_path(
        "paths.extracted_dir", "docs/extracted") / f"{args.topic}-datasets.csv"
    conn = db.connect()
    report = sync_links(conn, csv_path, args.topic)
    conn.close()
    emit(report)


if __name__ == "__main__":
    main()
