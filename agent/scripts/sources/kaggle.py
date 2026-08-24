"""Kaggle datasets search + download via the public REST API.

Auth uses ~/.kaggle/kaggle.json (or KAGGLE_USERNAME / KAGGLE_KEY env vars).
All datasets surfaced are free to download once you have a (free) Kaggle
account and token. Missing credentials degrade gracefully with a clear note.
"""
from __future__ import annotations

import json
import os
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import http_get, get_requests, eprint  # noqa: E402

BASE = "https://www.kaggle.com/api/v1"


def _auth() -> tuple | None:
    user = os.environ.get("KAGGLE_USERNAME")
    key = os.environ.get("KAGGLE_KEY")
    if user and key:
        return (user, key)
    cfg_file = Path.home() / ".kaggle" / "kaggle.json"
    if cfg_file.exists():
        data = json.loads(cfg_file.read_text())
        if data.get("username") and data.get("key"):
            return (data["username"], data["key"])
    return None


def search(query: str, limit: int = 15, **kw) -> list[dict]:
    auth = _auth()
    if not auth:
        return [{
            "name": None, "source": "kaggle", "source_id": None,
            "error": "no Kaggle credentials found (~/.kaggle/kaggle.json or "
                     "KAGGLE_USERNAME/KAGGLE_KEY). Kaggle results skipped.",
        }]
    requests = get_requests()
    resp = requests.get(f"{BASE}/datasets/list", params={"search": query},
                        auth=auth, timeout=30,
                        headers={"User-Agent": "research-agent/0.1"})
    resp.raise_for_status()
    out = []
    for d in (resp.json() or [])[:limit]:
        ref = d.get("ref")  # "owner/slug"
        out.append({
            "name": d.get("title") or ref,
            "source": "kaggle",
            "source_id": ref,
            "url": f"https://www.kaggle.com/datasets/{ref}",
            "description": (d.get("subtitle") or "")[:500] or None,
            "license": d.get("licenseName"),
            "size_hint": d.get("totalBytes"),
            "file_format": None,
            "downloads": d.get("downloadCount"),
            "votes": d.get("voteCount"),
            "is_free": True,
        })
    return out


def download(item: dict, dest_dir: Path) -> dict:
    auth = _auth()
    if not auth:
        return {"ok": False, "error": "no Kaggle credentials configured"}
    ref = item["source_id"]
    requests = get_requests()
    r = requests.get(f"{BASE}/datasets/download/{ref}", auth=auth,
                     timeout=600, stream=True,
                     headers={"User-Agent": "research-agent/0.1"})
    r.raise_for_status()
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / f"{ref.split('/')[-1]}.zip"
    with open(zip_path, "wb") as fh:
        for chunk in r.iter_content(chunk_size=1 << 16):
            fh.write(chunk)
    extracted = []
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(dest_dir)
            extracted = zf.namelist()
        zip_path.unlink()
    except zipfile.BadZipFile:
        return {"ok": True, "path": str(dest_dir), "note": "downloaded (not a zip)",
                "files": [zip_path.name]}
    return {"ok": True, "path": str(dest_dir), "files": extracted}
