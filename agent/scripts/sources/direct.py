"""Generic direct-URL dataset download (any http(s) link)."""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from urllib.parse import urlparse, unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import http_get  # noqa: E402


def search(query: str, limit: int = 15, **kw) -> list[dict]:
    # No index to search; direct source is used by URL only.
    return []


def download(item: dict, dest_dir: Path) -> dict:
    url = item.get("url") or item.get("source_id")
    if not url:
        return {"ok": False, "error": "no url provided for direct download"}
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = unquote(Path(urlparse(url).path).name) or "download.bin"
    target = dest_dir / name
    r = http_get(url, timeout=600, stream=True)
    r.raise_for_status()
    with open(target, "wb") as fh:
        for chunk in r.iter_content(chunk_size=1 << 16):
            fh.write(chunk)
    if zipfile.is_zipfile(target):
        with zipfile.ZipFile(target) as zf:
            zf.extractall(dest_dir)
            files = zf.namelist()
        target.unlink()
        return {"ok": True, "path": str(dest_dir), "files": files}
    return {"ok": True, "path": str(dest_dir), "files": [name]}
