"""Hugging Face Datasets search + download.

Search uses the public HTTP API (no token). Download prefers `huggingface_hub`
if installed, otherwise falls back to resolving files over HTTPS. Only a token
(HF_TOKEN env) is needed for gated datasets; public ones are free.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import http_get, eprint  # noqa: E402

LIST_API = "https://huggingface.co/api/datasets"


def search(query: str, limit: int = 15, **kw) -> list[dict]:
    params = {"search": query, "limit": limit, "full": "true", "sort": "downloads", "direction": -1}
    resp = http_get(LIST_API, params=params, timeout=30)
    resp.raise_for_status()
    out = []
    for d in resp.json() or []:
        card = d.get("cardData") or {}
        license_ = card.get("license") if isinstance(card, dict) else None
        out.append({
            "name": d.get("id"),
            "source": "huggingface",
            "source_id": d.get("id"),
            "url": f"https://huggingface.co/datasets/{d.get('id')}",
            "description": (d.get("description") or "")[:500] or None,
            "license": license_,
            "size_hint": None,
            "file_format": None,
            "downloads": d.get("downloads"),
            "likes": d.get("likes"),
            "is_free": not d.get("gated", False) and not d.get("private", False),
            "gated": d.get("gated", False),
        })
    return out


def download(item: dict, dest_dir: Path) -> dict:
    repo_id = item["source_id"]
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        from huggingface_hub import snapshot_download  # noqa: WPS433
        path = snapshot_download(repo_id=repo_id, repo_type="dataset",
                                 local_dir=str(dest_dir))
        return {"ok": True, "path": path, "method": "huggingface_hub"}
    except ImportError:
        pass  # fall back to HTTP resolve

    tree = http_get(f"https://huggingface.co/api/datasets/{repo_id}/tree/main",
                    params={"recursive": "true"}, timeout=30)
    tree.raise_for_status()
    files = [f["path"] for f in tree.json() if f.get("type") == "file"]
    if not files:
        return {"ok": False, "error": "no files listed; dataset may be script-based or gated"}
    for rel in files:
        url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{rel}"
        r = http_get(url, timeout=120, stream=True)
        r.raise_for_status()
        target = dest_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 16):
                fh.write(chunk)
    return {"ok": True, "path": str(dest_dir), "method": "http-resolve", "files": files}
