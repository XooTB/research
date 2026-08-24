"""SQLite library: schema, upserts, and BibTeX export.

The DB is the single source of truth for what's in the library. Every
paper/dataset that gets added is recorded here, and papers are also exported
to a BibTeX file for use in reference managers / LaTeX.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from common import ws_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    authors     TEXT,            -- '; '-joined
    year        INTEGER,
    venue       TEXT,
    abstract    TEXT,
    doi         TEXT,
    source      TEXT,            -- pubmed|semantic_scholar|arxiv|openalex
    source_id   TEXT,
    url         TEXT,
    pdf_url     TEXT,
    pdf_path    TEXT,
    topic       TEXT,
    tags        TEXT,
    bibkey      TEXT UNIQUE,
    added_at    TEXT,
    UNIQUE(source, source_id)
);

CREATE TABLE IF NOT EXISTS datasets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    source          TEXT,        -- kaggle|huggingface|zenodo|direct
    source_id       TEXT,
    url             TEXT,
    topic           TEXT,
    description     TEXT,
    local_path      TEXT,
    file_format     TEXT,
    size_bytes      INTEGER,
    n_rows          INTEGER,
    n_cols          INTEGER,
    columns_json    TEXT,
    license         TEXT,
    verified        INTEGER DEFAULT 0,
    usability_notes TEXT,
    status          TEXT DEFAULT 'candidate',  -- candidate|downloaded|verified
    added_at        TEXT,
    UNIQUE(source, source_id)
);

CREATE TABLE IF NOT EXISTS notes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ref_type  TEXT,   -- paper|dataset
    ref_id    INTEGER,
    criterion TEXT,
    value     TEXT,
    added_at  TEXT
);

CREATE TABLE IF NOT EXISTS paper_datasets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id    INTEGER NOT NULL REFERENCES papers(id),
    dataset_id  INTEGER NOT NULL REFERENCES datasets(id),
    evidence    TEXT,            -- extractor finding: kind/value, e.g. "GEO series:GSE9891"
    context     TEXT,            -- sentence-level context from the PDF (may be NULL)
    UNIQUE(paper_id, dataset_id)
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    path = ws_path("paths.db_path", ".research/library.db")
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


# ---------------------------------------------------------------------------
# Papers
# ---------------------------------------------------------------------------
def make_bibkey(conn, authors: str, year, title: str) -> str:
    first = (authors or "unknown").split(";")[0].split(",")[0].split()
    surname = first[-1] if first else "unknown"
    from common import slugify
    base = f"{slugify(surname, 20)}{year or 'nd'}"
    key, n = base, 1
    while conn.execute("SELECT 1 FROM papers WHERE bibkey=?", (key,)).fetchone():
        n += 1
        key = f"{base}{chr(ord('a') + n - 2)}"
    return key


def upsert_paper(conn, paper: dict) -> int:
    """Insert or update a paper by (source, source_id). Returns row id."""
    existing = conn.execute(
        "SELECT id, bibkey FROM papers WHERE source=? AND source_id=?",
        (paper.get("source"), paper.get("source_id")),
    ).fetchone()

    fields = {
        "title": paper.get("title", ""),
        "authors": "; ".join(paper.get("authors", [])) if isinstance(paper.get("authors"), list) else paper.get("authors"),
        "year": paper.get("year"),
        "venue": paper.get("venue"),
        "abstract": paper.get("abstract"),
        "doi": paper.get("doi"),
        "source": paper.get("source"),
        "source_id": paper.get("source_id"),
        "url": paper.get("url"),
        "pdf_url": paper.get("pdf_url"),
        "pdf_path": paper.get("pdf_path"),
        "topic": paper.get("topic"),
        "tags": paper.get("tags"),
    }

    if existing:
        set_clause = ", ".join(f"{k}=?" for k in fields if fields[k] is not None)
        vals = [v for v in fields.values() if v is not None]
        if set_clause:
            conn.execute(f"UPDATE papers SET {set_clause} WHERE id=?", (*vals, existing["id"]))
        conn.commit()
        return existing["id"]

    fields["bibkey"] = make_bibkey(conn, fields["authors"], fields["year"], fields["title"])
    fields["added_at"] = now()
    cols = ", ".join(fields)
    ph = ", ".join("?" for _ in fields)
    cur = conn.execute(f"INSERT INTO papers ({cols}) VALUES ({ph})", tuple(fields.values()))
    conn.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------
def upsert_dataset(conn, ds: dict) -> int:
    existing = conn.execute(
        "SELECT id FROM datasets WHERE source=? AND source_id=?",
        (ds.get("source"), ds.get("source_id")),
    ).fetchone()

    fields = {
        "name": ds.get("name", ""),
        "source": ds.get("source"),
        "source_id": ds.get("source_id"),
        "url": ds.get("url"),
        "topic": ds.get("topic"),
        "description": ds.get("description"),
        "local_path": ds.get("local_path"),
        "file_format": ds.get("file_format"),
        "size_bytes": ds.get("size_bytes"),
        "n_rows": ds.get("n_rows"),
        "n_cols": ds.get("n_cols"),
        "columns_json": json.dumps(ds["columns"]) if ds.get("columns") is not None else ds.get("columns_json"),
        "license": ds.get("license"),
        "verified": 1 if ds.get("verified") else 0,
        "usability_notes": ds.get("usability_notes"),
        "status": ds.get("status", "candidate"),
    }

    if existing:
        set_clause = ", ".join(f"{k}=?" for k in fields if fields[k] is not None)
        vals = [v for v in fields.values() if v is not None]
        if set_clause:
            conn.execute(f"UPDATE datasets SET {set_clause} WHERE id=?", (*vals, existing["id"]))
        conn.commit()
        return existing["id"]

    fields["added_at"] = now()
    cols = ", ".join(fields)
    ph = ", ".join("?" for _ in fields)
    cur = conn.execute(f"INSERT INTO datasets ({cols}) VALUES ({ph})", tuple(fields.values()))
    conn.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# Paper <-> dataset links
# ---------------------------------------------------------------------------
def link_paper_dataset(conn, paper_id: int, dataset_id: int,
                       evidence: str | None = None, context: str | None = None) -> bool:
    """Link a paper to a dataset. Returns True if a new row was inserted."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO paper_datasets (paper_id, dataset_id, evidence, context)"
        " VALUES (?, ?, ?, ?)",
        (paper_id, dataset_id, evidence, context),
    )
    conn.commit()
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# BibTeX export
# ---------------------------------------------------------------------------
def _bib_escape(text: str) -> str:
    return (text or "").replace("{", "").replace("}", "").replace("\\", "")


def export_bibtex(conn) -> Path:
    rows = conn.execute(
        "SELECT * FROM papers WHERE bibkey IS NOT NULL ORDER BY year DESC, bibkey"
    ).fetchall()
    entries = []
    for r in rows:
        etype = "article" if r["venue"] else "misc"
        lines = [f"@{etype}{{{r['bibkey']},"]
        lines.append(f"  title = {{{_bib_escape(r['title'])}}},")
        if r["authors"]:
            authors = " and ".join(a.strip() for a in r["authors"].split(";") if a.strip())
            lines.append(f"  author = {{{_bib_escape(authors)}}},")
        if r["year"]:
            lines.append(f"  year = {{{r['year']}}},")
        if r["venue"]:
            lines.append(f"  journal = {{{_bib_escape(r['venue'])}}},")
        if r["doi"]:
            lines.append(f"  doi = {{{r['doi']}}},")
        if r["url"]:
            lines.append(f"  url = {{{r['url']}}},")
        lines.append("}")
        entries.append("\n".join(lines))

    out = ws_path("paths.bib_path", ".research/references.bib")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n\n".join(entries) + ("\n" if entries else ""), encoding="utf-8")
    return out
