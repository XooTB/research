"""T010: turn <domain>_picks.json into papers_add.py input with open-access PDF URLs.

Usage: resolve_pdfs.py <picks.json> <topic-slug> <out.json>
Semantic Scholar batch lookup by DOI (authors, abstract, openAccessPdf, arXiv id);
arXiv id -> arxiv.org/pdf fallback. Papers with no OA PDF keep pdf_url=None
(papers_add records metadata only).
"""
import json
import sys
import time

import requests

S2 = "https://api.semanticscholar.org/graph/v1/paper/batch"
FIELDS = "title,authors,year,venue,abstract,openAccessPdf,externalIds,url"


def s2_batch(ids):
    for i in range(6):
        r = requests.post(S2, params={"fields": FIELDS}, json={"ids": ids}, timeout=120)
        if r.status_code == 200:
            return r.json()
        print("S2", r.status_code, r.text[:150], file=sys.stderr)
        time.sleep(5 * (i + 1))
    return [None] * len(ids)


def main():
    picks_path, topic, out_path = sys.argv[1:4]
    picks = json.load(open(picks_path))
    ids = []
    for p in picks:
        doi = (p.get("doi") or "").replace("https://doi.org/", "")
        ids.append(f"DOI:{doi}" if doi else f"URL:https://openalex.org/{p['openalex_id']}")
    meta = []
    for i in range(0, len(ids), 400):
        meta += s2_batch(ids[i:i + 400])
        time.sleep(1.5)
    out = []
    for p, m in zip(picks, meta):
        m = m or {}
        ext = m.get("externalIds") or {}
        pdf = (m.get("openAccessPdf") or {}).get("url") or None
        if not pdf and ext.get("ArXiv"):
            pdf = f"https://arxiv.org/pdf/{ext['ArXiv']}"
        authors = [a["name"] for a in (m.get("authors") or [])] or [p.get("first_author") or "unknown"]
        out.append({
            "title": p["title"], "authors": authors, "year": p.get("year"),
            "venue": p.get("venue") or m.get("venue"), "doi": p.get("doi"),
            "url": p.get("doi") or m.get("url"), "pdf_url": pdf,
            "abstract": m.get("abstract"), "topic": topic,
            "found_in": ["openalex", "semantic_scholar"],
            "subtopic": p.get("subtopic"), "openalex_id": p.get("openalex_id"),
        })
    json.dump(out, open(out_path, "w"), indent=1)
    n = sum(1 for o in out if o["pdf_url"])
    print(json.dumps({"picks": len(out), "with_pdf_url": n}))


if __name__ == "__main__":
    main()
