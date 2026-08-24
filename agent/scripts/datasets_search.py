#!/usr/bin/env python3
"""Search datasets across configured sources and emit JSON to stdout.

Only free datasets are surfaced when datasets.free_only is true (default).
The agent reads this JSON to rank candidates and check them against the
user's requirements before anything is downloaded.

Usage:
    datasets_search.py --query "antibiotic resistance" [--sources huggingface,zenodo] [--limit 15]
"""
from __future__ import annotations

import argparse
import importlib
import traceback

from common import cfg, emit, eprint

VALID = ["huggingface", "kaggle", "zenodo", "direct"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--sources", default=",".join(cfg("datasets.sources", VALID)))
    ap.add_argument("--limit", type=int, default=cfg("datasets.default_limit", 15))
    args = ap.parse_args()

    free_only = cfg("datasets.free_only", True)
    sources = [s.strip() for s in args.sources.split(",")
               if s.strip() in VALID and s.strip() != "direct"]

    results, errors, notes = [], {}, []
    for name in sources:
        try:
            mod = importlib.import_module(f"sources.{name}")
            found = mod.search(args.query, limit=args.limit)
            for item in found:
                if item.get("error"):
                    notes.append(f"{name}: {item['error']}")
                    continue
                if free_only and item.get("is_free") is False:
                    continue
                results.append(item)
            eprint(f"[{name}] {len(found)} results")
        except Exception as exc:  # noqa: BLE001
            errors[name] = str(exc)
            eprint(f"[{name}] ERROR: {exc}")
            eprint(traceback.format_exc())

    emit({
        "query": args.query,
        "sources_queried": sources,
        "free_only": free_only,
        "errors": errors,
        "notes": notes,
        "count": len(results),
        "results": results,
    })


if __name__ == "__main__":
    main()
