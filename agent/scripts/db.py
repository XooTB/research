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

from common import ws_path, ws_rel

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
    pdf_path    TEXT,            -- workspace-relative
    topic       TEXT,
    tags        TEXT,
    bibkey      TEXT UNIQUE,
    added_at    TEXT,
    UNIQUE(source, source_id)
);

CREATE TABLE IF NOT EXISTS datasets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    source          TEXT,        -- kaggle|huggingface|zenodo|direct|derived
    source_id       TEXT,
    url             TEXT,
    topic           TEXT,
    description     TEXT,
    local_path      TEXT,        -- workspace-relative
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


def _find_existing(conn, table: str, rec: dict, keys: list[tuple[str, ...]]):
    """First row matching any of `keys`, trying each column tuple in order.

    A key is only used when every column in it has a value: SQL `col = NULL`
    never matches, which is how blank duplicate rows used to get inserted.
    """
    for cols in keys:
        vals = [rec.get(c) for c in cols]
        if any(v is None or v == "" for v in vals):
            continue
        where = " AND ".join(f"{c}=?" for c in cols)
        row = conn.execute(f"SELECT * FROM {table} WHERE {where}", vals).fetchone()
        if row:
            return row
    return None


def _write(conn, table: str, existing, fields: dict, provided: set[str]) -> int:
    """UPDATE only the fields the caller actually provided, or INSERT."""
    if existing:
        updates = {k: v for k, v in fields.items() if k in provided and v is not None}
        if updates:
            set_clause = ", ".join(f"{k}=?" for k in updates)
            conn.execute(f"UPDATE {table} SET {set_clause} WHERE id=?",
                         (*updates.values(), existing["id"]))
        conn.commit()
        return existing["id"]

    fields = {k: v for k, v in fields.items() if v is not None}
    fields["added_at"] = now()
    cols = ", ".join(fields)
    ph = ", ".join("?" for _ in fields)
    cur = conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({ph})", tuple(fields.values()))
    conn.commit()
    return cur.lastrowid


def upsert_paper(conn, paper: dict) -> int:
    """Insert or update a paper. Returns row id.

    Matched by id, then (source, source_id), then DOI, then pdf_path. On update
    only the keys present in `paper` are written.
    """
    rec = dict(paper)
    if "pdf_path" in rec:
        rec["pdf_path"] = ws_rel(rec["pdf_path"])
    existing = _find_existing(conn, "papers", rec,
                              [("id",), ("source", "source_id"), ("doi",), ("pdf_path",)])

    authors = rec.get("authors")
    fields = {
        "title": rec.get("title"),
        "authors": "; ".join(authors) if isinstance(authors, list) else authors,
        "year": rec.get("year"),
        "venue": rec.get("venue"),
        "abstract": rec.get("abstract"),
        "doi": rec.get("doi"),
        "source": rec.get("source"),
        "source_id": rec.get("source_id"),
        "url": rec.get("url"),
        "pdf_url": rec.get("pdf_url"),
        "pdf_path": rec.get("pdf_path"),
        "topic": rec.get("topic"),
        "tags": rec.get("tags"),
    }
    if not existing:
        if not fields["title"]:
            raise ValueError(f"refusing to insert a paper without a title: {paper!r}")
        fields["bibkey"] = make_bibkey(conn, fields["authors"], fields["year"], fields["title"])
    return _write(conn, "papers", existing, fields, set(rec))


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------
DATASET_STATUSES = ("candidate", "downloaded", "verified")


def upsert_dataset(conn, ds: dict) -> int:
    """Insert or update a dataset. Returns row id.

    Matched by id, then (source, source_id), then local_path, then (topic, name).
    On update only the keys present in `ds` are written, so a partial update
    (e.g. from datasets_verify) never resets status or verified.
    """
    rec = dict(ds)
    if "local_path" in rec:
        rec["local_path"] = ws_rel(rec["local_path"])
    if "columns" in rec:
        rec["columns_json"] = json.dumps(rec["columns"]) if rec["columns"] is not None else None
    if "verified" in rec and rec["verified"] is not None:
        rec["verified"] = 1 if rec["verified"] else 0
    if rec.get("status") is not None and rec["status"] not in DATASET_STATUSES:
        raise ValueError(f"unknown dataset status {rec['status']!r}")
    existing = _find_existing(conn, "datasets", rec,
                              [("id",), ("source", "source_id"), ("local_path",),
                               ("topic", "name")])

    fields = {k: rec.get(k) for k in (
        "name", "source", "source_id", "url", "topic", "description", "local_path",
        "file_format", "size_bytes", "n_rows", "n_cols", "columns_json", "license",
        "verified", "usability_notes", "status")}
    if not existing:
        if not fields["name"]:
            raise ValueError(f"refusing to insert a dataset without a name: {ds!r}")
        fields["status"] = fields["status"] or "candidate"
        fields["verified"] = fields["verified"] or 0
    return _write(conn, "datasets", existing, fields, set(rec))


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
