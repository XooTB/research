"""Semantic Scholar Graph API (works anonymously; key raises rate limits)."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import http_get, cfg  # noqa: E402

API = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,abstract,year,venue,authors,externalIds,openAccessPdf,url"


def search(query: str, limit: int = 15, **kw) -> list[dict]:
    headers = {}
    key = cfg("credentials.semantic_scholar_api_key", "")
    if key:
        headers["x-api-key"] = key
    params = {"query": query, "limit": min(limit, 100), "fields": FIELDS}
    resp = http_get(API, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    out = []
    for p in data.get("data", []) or []:
        ext = p.get("externalIds") or {}
        oa = p.get("openAccessPdf") or {}
        out.append({
            "title": p.get("title") or "",
            "authors": [a.get("name", "") for a in (p.get("authors") or [])],
            "year": p.get("year"),
            "venue": p.get("venue"),
            "abstract": p.get("abstract"),
            "doi": ext.get("DOI"),
            "source": "semantic_scholar",
            "source_id": p.get("paperId"),
            "url": p.get("url"),
            "pdf_url": oa.get("url"),
        })
    return out
