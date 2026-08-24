#!/usr/bin/env python3
"""Search papers across configured sources and emit merged JSON to stdout.

The agent (Cursor) reads this JSON to rank by relevance, apply the user's
criteria, and present a shortlist. This script does NOT rank — it only
gathers, normalizes, and deduplicates.

Usage:
    papers_search.py --query "antibiotic resistance prediction" \
        [--sources pubmed,arxiv] [--limit 15] [--author "Smith"]
"""
from __future__ import annotations

import argparse
import importlib
import re
import traceback

from common import cfg, emit, eprint

VALID = ["pubmed", "semantic_scholar", "arxiv", "openalex"]


def _norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def dedupe(papers: list[dict]) -> list[dict]:
    by_key: dict[str, dict] = {}
    order: list[str] = []
    for p in papers:
        doi = (p.get("doi") or "").lower().strip()
        key = f"doi:{doi}" if doi else f"title:{_norm_title(p.get('title', ''))}"
        if key not in by_key:
            p["found_in"] = [p["source"]]
            by_key[key] = p
            order.append(key)
        else:
            merged = by_key[key]
            merged.setdefault("found_in", [merged["source"]])
            if p["source"] not in merged["found_in"]:
                merged["found_in"].append(p["source"])
            # Prefer a record that has an abstract / pdf link.
            if not merged.get("abstract") and p.get("abstract"):
                merged["abstract"] = p["abstract"]
            if not merged.get("pdf_url") and p.get("pdf_url"):
                merged["pdf_url"] = p["pdf_url"]
            if not merged.get("doi") and p.get("doi"):
                merged["doi"] = p["doi"]
    return [by_key[k] for k in order]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--sources", default=",".join(cfg("papers.sources", VALID)))
    ap.add_argument("--limit", type=int, default=cfg("papers.default_limit", 15))
    ap.add_argument("--author", default=None)
    args = ap.parse_args()

    sources = [s.strip() for s in args.sources.split(",") if s.strip() in VALID]
    results, errors = [], {}
    for name in sources:
        try:
            mod = importlib.import_module(f"sources.{name}")
            kw = {}
            if args.author:
                kw["author"] = args.author
            found = mod.search(args.query, limit=args.limit, **kw)
            results.extend(found)
            eprint(f"[{name}] {len(found)} results")
        except Exception as exc:  # noqa: BLE001
            errors[name] = str(exc)
            eprint(f"[{name}] ERROR: {exc}")
            eprint(traceback.format_exc())

    merged = dedupe(results)
    emit({
        "query": args.query,
        "author": args.author,
        "sources_queried": sources,
        "errors": errors,
        "count": len(merged),
        "results": merged,
    })


if __name__ == "__main__":
    main()
