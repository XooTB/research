#!/usr/bin/env python3
"""Add selected papers to the library: download PDF, record in SQLite, export BibTeX.

Input is a JSON file containing either a single paper dict or a list of them
(the same shape emitted by papers_search.py). Each entry may carry a "topic"
field; a global --topic applies to entries without one.

Usage:
    papers_add.py --input picks.json --topic "antibiotic-resistance"
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import db
from common import WORKSPACE, ws_path, slugify, short_title, http_get, emit, eprint


def _download_pdf(paper: dict, dest_dir: Path) -> str | None:
    url = paper.get("pdf_url")
    if not url:
        return None
    try:
        r = http_get(url, timeout=120, stream=True,
                     headers={"Accept": "application/pdf"})
        r.raise_for_status()
        ctype = r.headers.get("Content-Type", "")
        # Only keep it if it actually looks like a PDF.
        dest_dir.mkdir(parents=True, exist_ok=True)
        target = dest_dir / "paper.pdf"
        first = True
        with open(target, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 16):
                if first:
                    first = False
                    if not chunk.startswith(b"%PDF") and "pdf" not in ctype.lower():
                        fh.close()
                        target.unlink(missing_ok=True)
                        return None
                fh.write(chunk)
        return str(target)
    except Exception as exc:  # noqa: BLE001
        eprint(f"  PDF download failed: {exc}")
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="JSON file: paper dict or list")
    ap.add_argument("--topic", default="uncategorized")
    ap.add_argument("--no-pdf", action="store_true", help="record metadata only")
    args = ap.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "results" in data:
        data = data["results"]
    papers = data if isinstance(data, list) else [data]

    conn = db.connect()
    papers_dir = ws_path("paths.papers_dir", "papers")
    added = []
    for p in papers:
        topic = p.get("topic") or args.topic
        topic_slug = slugify(topic)
        folder = papers_dir / topic_slug / f"{p.get('year') or 'nd'}-" \
            f"{slugify((p.get('authors') or ['unknown'])[0].split()[-1] if p.get('authors') else 'unknown', 20)}-" \
            f"{short_title(p.get('title', ''))}"

        pdf_path = None
        if not args.no_pdf:
            pdf_path = _download_pdf(p, folder)

        p_rec = dict(p)
        p_rec["topic"] = topic_slug
        p_rec["pdf_path"] = pdf_path
        pid = db.upsert_paper(conn, p_rec)
        added.append({
            "id": pid, "title": p.get("title"), "topic": topic_slug,
            "pdf": pdf_path, "pdf_ok": bool(pdf_path),
        })
        eprint(f"+ [{pid}] {p.get('title', '')[:70]}  pdf={'yes' if pdf_path else 'no'}")

    bib = db.export_bibtex(conn)
    conn.close()

    # New PDFs can be mined for dataset references: re-run the extractor per
    # topic (collection slug == topic slug), which also syncs DB links.
    # Failure-safe: never break the add flow. Extractor stdout is progress,
    # not JSON, so fold it into stderr to keep our stdout clean.
    topics = sorted({a["topic"] for a in added})
    with_pdf = {a["topic"] for a in added if a["pdf_ok"]}
    for topic_slug in topics:
        try:
            if topic_slug not in with_pdf:
                eprint(f"no new PDFs for {topic_slug}; "
                       "paper-dataset links unchanged")
                continue
            script = Path(__file__).with_name("paper_datasets_extract.py")
            eprint(f"re-running dataset extraction + linking for {topic_slug} ...")
            subprocess.run(
                [sys.executable, str(script), "--collection", topic_slug],
                cwd=str(WORKSPACE), stdout=sys.stderr, check=True)
        except Exception as exc:  # noqa: BLE001
            eprint(f"! extraction/link sync failed for {topic_slug}: {exc}")

    try:
        import github_pack
        github_pack.hook_pack([papers_dir])
    except Exception as exc:  # noqa: BLE001
        eprint(f"! github-pack failed: {exc}")

    emit({"added": added, "count": len(added), "bibtex": str(bib)})


if __name__ == "__main__":
    main()
