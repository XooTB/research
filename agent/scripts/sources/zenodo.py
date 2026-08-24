"""Zenodo records search + download (open access, direct file links)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import http_get  # noqa: E402

API = "https://zenodo.org/api/records"


def _record_id(item: dict) -> str:
    sid = item.get("source_id") or ""
    return sid.rsplit("/", 1)[-1] if sid else ""


def search(query: str, limit: int = 15, **kw) -> list[dict]:
    params = {"q": query, "size": limit, "sort": "bestmatch",
              "access_right": "open"}
    resp = http_get(API, params=params, timeout=30)
    resp.raise_for_status()
    out = []
    for rec in resp.json().get("hits", {}).get("hits", []) or []:
        meta = rec.get("metadata", {})
        files = rec.get("files", []) or []
        total = sum(f.get("size", 0) for f in files)
        fmts = sorted({(f.get("key", "").rsplit(".", 1)[-1].lower())
                       for f in files if "." in f.get("key", "")})
        out.append({
            "name": meta.get("title"),
            "source": "zenodo",
            "source_id": str(rec.get("id")),
            "url": rec.get("links", {}).get("self_html") or rec.get("doi_url"),
            "description": (meta.get("description") or "")[:500] or None,
            "license": (meta.get("license") or {}).get("id"),
            "size_hint": total or None,
            "file_format": "/".join(fmts) if fmts else None,
            "is_free": meta.get("access_right") == "open",
        })
    return out


def download(item: dict, dest_dir: Path) -> dict:
    rid = _record_id(item)
    rec = http_get(f"{API}/{rid}", timeout=30)
    rec.raise_for_status()
    files = rec.json().get("files", []) or []
    if not files:
        return {"ok": False, "error": "record has no downloadable files"}
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for f in files:
        link = f.get("links", {}).get("self") or f.get("links", {}).get("download")
        name = f.get("key")
        r = http_get(link, timeout=300, stream=True)
        r.raise_for_status()
        target = dest_dir / name
        with open(target, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 16):
                fh.write(chunk)
        saved.append(name)
    return {"ok": True, "path": str(dest_dir), "files": saved}
