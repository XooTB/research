"""OpenAlex API (open, no key; supports topic/author/venue search)."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import http_get, cfg  # noqa: E402

API = "https://api.openalex.org/works"


def _reconstruct_abstract(inv_index) -> str | None:
    if not inv_index:
        return None
    positions = []
    for word, idxs in inv_index.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(w for _, w in positions)


def search(query: str, limit: int = 15, author: str | None = None, **kw) -> list[dict]:
    params = {"per-page": min(limit, 200), "search": query}
    email = cfg("credentials.ncbi_email", "")  # reuse as polite contact if present
    if email:
        params["mailto"] = email
    if author:
        params["filter"] = f"authorships.author.display_name.search:{author}"
    resp = http_get(API, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    out = []
    for w in data.get("results", []) or []:
        ids = w.get("ids") or {}
        loc = w.get("primary_location") or {}
        src = loc.get("source") or {}
        pdf_url = loc.get("pdf_url")
        oa = w.get("open_access") or {}
        out.append({
            "title": w.get("title") or "",
            "authors": [a.get("author", {}).get("display_name", "")
                        for a in (w.get("authorships") or [])],
            "year": w.get("publication_year"),
            "venue": src.get("display_name"),
            "abstract": _reconstruct_abstract(w.get("abstract_inverted_index")),
            "doi": (w.get("doi") or "").replace("https://doi.org/", "") or None,
            "source": "openalex",
            "source_id": (w.get("id") or "").rsplit("/", 1)[-1],
            "url": w.get("doi") or ids.get("openalex"),
            "pdf_url": pdf_url or oa.get("oa_url"),
        })
    return out
