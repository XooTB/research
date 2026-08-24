#!/usr/bin/env python3
"""Ingest an existing dataset shortlist CSV into the library as candidates.

Tailored to the workspace file 'Datasets  - Drug & Treatment.csv' with columns:
    Topic, Dataset Name, Source, Link, Link Type, File Format, Columns,
    Description, File Size
but tolerant of missing columns. Entries are recorded with status=candidate
(not downloaded). Re-running is safe (upsert by source+source_id).

Usage:
    ingest_csv.py --csv "Datasets  - Drug & Treatment.csv"
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import db
from common import WORKSPACE, slugify, emit, eprint

SOURCE_MAP = {
    "kaggle": "kaggle",
    "hugging face": "huggingface",
    "huggingface": "huggingface",
    "zenodo": "zenodo",
}

SIZE_RE = re.compile(r"([\d.]+)\s*(GB|MB|KB|TB|B)", re.I)
UNIT = {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3, "tb": 1024**4}


def parse_size(text: str) -> int | None:
    m = SIZE_RE.search(text or "")
    if not m:
        return None
    return int(float(m.group(1)) * UNIT[m.group(2).lower()])


def derive(source: str, link: str) -> tuple[str, str | None, str | None]:
    """Return (normalized_source, source_id, url)."""
    norm = SOURCE_MAP.get((source or "").strip().lower(), "direct")
    url = link if (link or "").startswith("http") else None
    source_id = None
    if url:
        if norm == "kaggle":
            m = re.search(r"kaggle\.com/datasets/([^/]+/[^/?#]+)", url)
            source_id = m.group(1) if m else url
        elif norm == "huggingface":
            m = re.search(r"huggingface\.co/datasets/([^?#]+)", url)
            source_id = m.group(1).rstrip("/") if m else url
        elif norm == "zenodo":
            m = re.search(r"zenodo\.org/records?/(\d+)", url)
            source_id = m.group(1) if m else url
        else:
            source_id = url
    return norm, source_id, url


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="Datasets  - Drug & Treatment.csv")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        csv_path = WORKSPACE / csv_path
    if not csv_path.exists():
        emit({"error": f"CSV not found: {csv_path}"})
        return

    conn = db.connect()
    ingested = []
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            name = (r.get("Dataset Name") or "").strip()
            if not name:
                continue
            source, source_id, url = derive(r.get("Source", ""), r.get("Link", ""))
            if not source_id:
                source_id = f"csv:{slugify(name, 80)}"
            did = db.upsert_dataset(conn, {
                "name": name,
                "source": source,
                "source_id": source_id,
                "url": url,
                "topic": slugify(r.get("Topic", "uncategorized")),
                "description": (r.get("Description") or "").strip() or None,
                "file_format": (r.get("File Format") or "").strip() or None,
                "size_bytes": parse_size(r.get("File Size", "")),
                "columns_json": None,
                "usability_notes": f"columns hint: {r.get('Columns', '').strip()}" or None,
                "status": "candidate",
            })
            ingested.append({"id": did, "name": name, "source": source,
                             "topic": slugify(r.get("Topic", ""))})
            eprint(f"+ [{did}] {name}  ({source})")

    conn.close()
    emit({"ingested": ingested, "count": len(ingested)})


if __name__ == "__main__":
    main()
