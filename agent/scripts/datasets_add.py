#!/usr/bin/env python3
"""Download selected datasets into datasets/<topic>/<slug>/ and record in DB.

Input is a JSON file: a dataset dict or a list of them (shape from
datasets_search.py). Each entry may carry "topic". For a direct URL download,
pass an entry like {"source": "direct", "url": "...", "name": "...", "topic": "..."}.

After download the dataset is registered (status=downloaded). Run
datasets_verify.py next to profile and produce a REPORT.md.

Usage:
    datasets_add.py --input picks.json --topic "antibiotic-resistance"
"""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

import db
from common import ws_path, slugify, emit, eprint


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--topic", default="uncategorized")
    ap.add_argument("--no-download", action="store_true",
                    help="register as candidate without downloading")
    args = ap.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "results" in data:
        data = data["results"]
    items = data if isinstance(data, list) else [data]

    conn = db.connect()
    ds_root = ws_path("paths.datasets_dir", "datasets")
    results = []
    for item in items:
        topic = item.get("topic") or args.topic
        topic_slug = slugify(topic)
        name = item.get("name") or item.get("source_id") or "dataset"
        slug = slugify(name.replace("/", "-"), 60)
        dest = ds_root / topic_slug / slug

        dl = {"ok": None}
        if not args.no_download:
            try:
                mod = importlib.import_module(f"sources.{item['source']}")
                dl = mod.download(item, dest)
            except Exception as exc:  # noqa: BLE001
                dl = {"ok": False, "error": str(exc)}
            eprint(f"{'+' if dl.get('ok') else '!'} {name}: "
                   f"{dl.get('path') or dl.get('error')}")

        rec = dict(item)
        rec["topic"] = topic_slug
        rec["local_path"] = str(dest) if dl.get("ok") else item.get("local_path")
        rec["size_bytes"] = item.get("size_hint")
        rec["status"] = "downloaded" if dl.get("ok") else "candidate"
        did = db.upsert_dataset(conn, rec)
        results.append({"id": did, "name": name, "topic": topic_slug,
                        "path": rec["local_path"], "download": dl})

    # Newly added datasets may match accessions the extractor already found;
    # re-sync links per topic when an extraction CSV exists. Failure-safe.
    for topic_slug in sorted({r["topic"] for r in results}):
        try:
            import paper_dataset_links
            csv_path = ws_path("paths.extracted_dir", "docs/extracted") \
                / f"{topic_slug}-datasets.csv"
            if not csv_path.exists():
                continue
            report = paper_dataset_links.sync_links(conn, csv_path, topic_slug)
            eprint(f"link sync [{topic_slug}]: +{report['links_created']} links "
                   f"({report['paper_datasets_total']} total)")
        except Exception as exc:  # noqa: BLE001
            eprint(f"! link sync failed for {topic_slug}: {exc}")

    conn.close()
    try:
        import github_pack
        dests = [r["path"] for r in results if r.get("path")]
        github_pack.hook_pack(dests)
    except Exception as exc:  # noqa: BLE001
        eprint(f"! github-pack failed: {exc}")
    emit({"results": results, "count": len(results)})


if __name__ == "__main__":
    main()
