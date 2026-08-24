#!/usr/bin/env python3
"""List / query what's already in the library. Emits JSON.

Usage:
    library.py                      # summary counts
    library.py --papers [--topic x] # list papers
    library.py --datasets [--topic x] [--status candidate|downloaded|verified]
"""
from __future__ import annotations

import argparse

import db
from common import emit


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--papers", action="store_true")
    ap.add_argument("--datasets", action="store_true")
    ap.add_argument("--topic")
    ap.add_argument("--status")
    args = ap.parse_args()

    conn = db.connect()

    if not args.papers and not args.datasets:
        emit({
            "papers": conn.execute("SELECT COUNT(*) c FROM papers").fetchone()["c"],
            "datasets": conn.execute("SELECT COUNT(*) c FROM datasets").fetchone()["c"],
            "paper_topics": [dict(r) for r in conn.execute(
                "SELECT topic, COUNT(*) n FROM papers GROUP BY topic ORDER BY n DESC")],
            "dataset_topics": [dict(r) for r in conn.execute(
                "SELECT topic, COUNT(*) n FROM datasets GROUP BY topic ORDER BY n DESC")],
            "dataset_status": [dict(r) for r in conn.execute(
                "SELECT status, COUNT(*) n FROM datasets GROUP BY status")],
        })
        conn.close()
        return

    table = "papers" if args.papers else "datasets"
    where, params = [], []
    if args.topic:
        where.append("topic=?")
        params.append(args.topic)
    if args.status and table == "datasets":
        where.append("status=?")
        params.append(args.status)
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    rows = conn.execute(f"SELECT * FROM {table}{clause} ORDER BY id", params).fetchall()
    conn.close()
    emit({"table": table, "count": len(rows), "rows": [dict(r) for r in rows]})


if __name__ == "__main__":
    main()
