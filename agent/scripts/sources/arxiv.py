"""arXiv search via the public Atom API (no key required)."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import http_get  # noqa: E402

API = "https://export.arxiv.org/api/query"
NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def search(query: str, limit: int = 15, **kw) -> list[dict]:
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    resp = http_get(API, params=params, timeout=30)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    out = []
    for entry in root.findall("a:entry", NS):
        arxiv_url = entry.findtext("a:id", default="", namespaces=NS)
        arxiv_id = arxiv_url.rsplit("/", 1)[-1]
        published = entry.findtext("a:published", default="", namespaces=NS)
        year = int(published[:4]) if published[:4].isdigit() else None
        authors = [a.findtext("a:name", default="", namespaces=NS)
                   for a in entry.findall("a:author", NS)]
        doi = entry.findtext("arxiv:doi", default=None, namespaces=NS)
        pdf_url = None
        for link in entry.findall("a:link", NS):
            if link.get("title") == "pdf":
                pdf_url = link.get("href")
        out.append({
            "title": " ".join((entry.findtext("a:title", default="", namespaces=NS)).split()),
            "authors": authors,
            "year": year,
            "venue": entry.findtext("arxiv:journal_ref", default=None, namespaces=NS),
            "abstract": " ".join((entry.findtext("a:summary", default="", namespaces=NS)).split()),
            "doi": doi,
            "source": "arxiv",
            "source_id": re.sub(r"v\d+$", "", arxiv_id),
            "url": arxiv_url,
            "pdf_url": pdf_url or (arxiv_url.replace("/abs/", "/pdf/") if arxiv_url else None),
        })
    return out
