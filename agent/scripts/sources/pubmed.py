"""PubMed via NCBI E-utilities (esearch + efetch). No key needed; a key and
email raise the rate limit and are read from config if present."""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import http_get, cfg  # noqa: E402

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def _creds() -> dict:
    p = {}
    email = cfg("credentials.ncbi_email", "")
    key = cfg("credentials.ncbi_api_key", "")
    if email:
        p["email"] = email
        p["tool"] = "research-agent"
    if key:
        p["api_key"] = key
    return p


def _text(node, path) -> str | None:
    el = node.find(path)
    return "".join(el.itertext()).strip() if el is not None else None


def search(query: str, limit: int = 15, **kw) -> list[dict]:
    params = {"db": "pubmed", "term": query, "retmax": limit, "retmode": "json"}
    params.update(_creds())
    resp = http_get(ESEARCH, params=params, timeout=30)
    resp.raise_for_status()
    ids = resp.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    fparams = {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}
    fparams.update(_creds())
    fresp = http_get(EFETCH, params=fparams, timeout=45)
    fresp.raise_for_status()
    root = ET.fromstring(fresp.text)

    out = []
    for art in root.findall(".//PubmedArticle"):
        pmid = _text(art, ".//PMID")
        year = _text(art, ".//JournalIssue/PubDate/Year") or _text(art, ".//PubDate/MedlineDate")
        year_int = int(year[:4]) if year and year[:4].isdigit() else None
        authors = []
        for a in art.findall(".//AuthorList/Author"):
            last = _text(a, "LastName")
            fore = _text(a, "ForeName")
            if last:
                authors.append(f"{fore} {last}".strip() if fore else last)
        doi = None
        for aid in art.findall(".//ArticleIdList/ArticleId"):
            if aid.get("IdType") == "doi":
                doi = (aid.text or "").strip()
        abstract = " ".join(
            (seg.text or "").strip() for seg in art.findall(".//Abstract/AbstractText")
        ).strip() or None
        out.append({
            "title": _text(art, ".//ArticleTitle") or "",
            "authors": authors,
            "year": year_int,
            "venue": _text(art, ".//Journal/Title"),
            "abstract": abstract,
            "doi": doi,
            "source": "pubmed",
            "source_id": pmid,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
            # PMC full text (when available) is resolved at download time.
            "pdf_url": f"https://doi.org/{doi}" if doi else None,
        })
    return out
