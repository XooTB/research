#!/usr/bin/env python3
"""Pack files over GitHub's 100 MB limit; keep unpacked copies on disk.

GitHub rejects any blob > 100 MB. Working copies stay unzipped locally and
are gitignored. The zip (or zip parts) is what git tracks.

Usage:
    github_pack.py pack [--path DIR_OR_FILE]   # zip/split anything over 100 MB
    github_pack.py unpack [--path DIR]         # restore missing unpacked files
    github_pack.py status
"""
from __future__ import annotations

import argparse
import json
import os
import re
import zipfile
from pathlib import Path

from common import WORKSPACE, emit, eprint

THRESHOLD = 100 * 1024 * 1024  # GitHub hard limit
PART_SIZE = 90 * 1024 * 1024   # stay under the limit with headroom
MANIFEST_PATH = WORKSPACE / ".research" / "github-pack.json"
GITIGNORE_PATH = WORKSPACE / ".gitignore"
BEGIN = "# BEGIN github-pack (generated — do not edit)"
END = "# END github-pack"
SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules"}
PART_RE = re.compile(r"\.zip\.part\d+$", re.I)


def _rel(path: Path) -> str:
    path = path.resolve()
    try:
        return path.relative_to(WORKSPACE).as_posix()
    except ValueError:
        return path.as_posix()


def _load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {
            "threshold_bytes": THRESHOLD,
            "part_bytes": PART_SIZE,
            "items": [],
        }
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    items = sorted(manifest.get("items") or [], key=lambda i: i["original"])
    manifest = {
        "threshold_bytes": THRESHOLD,
        "part_bytes": PART_SIZE,
        "items": items,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _rewrite_gitignore(manifest)


def _item_for(manifest: dict, original: str) -> dict | None:
    for item in manifest.get("items") or []:
        if item["original"] == original:
            return item
    return None


def _upsert_item(manifest: dict, item: dict) -> None:
    items = manifest.setdefault("items", [])
    for i, existing in enumerate(items):
        if existing["original"] == item["original"]:
            items[i] = item
            return
    items.append(item)


def _rewrite_gitignore(manifest: dict) -> None:
    originals = []
    assembled = []
    for item in manifest.get("items") or []:
        originals.append(item["original"])
        if item.get("parts"):
            assembled.append(item["zip"])
    block_lines = [
        BEGIN,
        "# Unpacked originals stay on disk for work; git tracks the zip/parts.",
    ]
    block_lines.extend(originals)
    if assembled:
        block_lines.append("# Assembled zips of split archives (rebuild with unpack)")
        block_lines.extend(assembled)
    block_lines.append(END)
    block = "\n".join(block_lines) + "\n"

    existing = GITIGNORE_PATH.read_text(encoding="utf-8") if GITIGNORE_PATH.exists() else ""
    if BEGIN in existing and END in existing:
        pre, rest = existing.split(BEGIN, 1)
        _, post = rest.split(END, 1)
        new = pre.rstrip("\n") + ("\n\n" if pre.strip() else "") + block
        if post.strip():
            new = new.rstrip("\n") + "\n" + post.lstrip("\n")
        GITIGNORE_PATH.write_text(new, encoding="utf-8")
        return

    prefix = existing.rstrip() + "\n\n" if existing.strip() else ""
    GITIGNORE_PATH.write_text(prefix + block, encoding="utf-8")


def is_pack_artifact(path: Path) -> bool:
    name = path.name
    if PART_RE.search(name):
        return True
    if name.endswith(".zip"):
        return True
    return False


def iter_large_files(root: Path) -> list[Path]:
    root = root.resolve()
    found: list[Path] = []
    if root.is_file():
        if root.stat().st_size > THRESHOLD and not is_pack_artifact(root):
            found.append(root)
        return found
    if not root.is_dir():
        return found
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            if is_pack_artifact(path):
                continue
            try:
                if path.stat().st_size > THRESHOLD:
                    found.append(path)
            except OSError:
                continue
    return found


def _zip_file(original: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = zip_path.with_name(zip_path.name + ".tmp")
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            zf.write(original, arcname=original.name)
        tmp.replace(zip_path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _split_file(src: Path, part_prefix: Path) -> list[Path]:
    """Split src into part_prefix.part01, .part02, ... and delete src."""
    parts: list[Path] = []
    with src.open("rb") as fh:
        n = 1
        while True:
            chunk = fh.read(PART_SIZE)
            if not chunk:
                break
            part = Path(f"{part_prefix}.part{n:02d}")
            part.write_bytes(chunk)
            parts.append(part)
            n += 1
    src.unlink()
    return parts


def _assemble_parts(parts: list[Path], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    try:
        with tmp.open("wb") as out:
            for part in parts:
                with part.open("rb") as fh:
                    while True:
                        chunk = fh.read(1024 * 1024)
                        if not chunk:
                            break
                        out.write(chunk)
        tmp.replace(dest)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _extract_zip(zip_path: Path, dest_dir: Path, original_name: str) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if original_name in names:
            member = original_name
        elif len(names) == 1:
            member = names[0]
        else:
            raise FileNotFoundError(
                f"{zip_path} has {names!r}, expected {original_name!r}"
            )
        info = zf.getinfo(member)
        target = dest_dir / original_name
        tmp = target.with_name(target.name + ".unpack-tmp")
        with zf.open(info) as src, tmp.open("wb") as out:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        tmp.replace(target)


def pack_file(original: Path, manifest: dict | None = None) -> dict:
    """Zip original (split if needed). Leaves the unpacked file on disk."""
    original = original.resolve()
    own_manifest = manifest is None
    if manifest is None:
        manifest = _load_manifest()
    rel = _rel(original)
    zip_path = original.with_name(original.name + ".zip")
    eprint(f"packing {rel} ({original.stat().st_size / 1024 / 1024:.1f} MB) ...")
    _zip_file(original, zip_path)
    zip_size = zip_path.stat().st_size
    parts: list[Path] = []
    if zip_size >= THRESHOLD:
        eprint(f"  zip is {zip_size / 1024 / 1024:.1f} MB; splitting into "
               f"{PART_SIZE / 1024 / 1024:.0f} MB parts")
        parts = _split_file(zip_path, zip_path)
    item = {
        "original": rel,
        "zip": _rel(zip_path),
        "parts": [_rel(p) for p in parts],
        "original_bytes": original.stat().st_size,
        "zip_bytes": zip_size,
    }
    _upsert_item(manifest, item)
    if own_manifest:
        _save_manifest(manifest)
    return item


def _already_packed(path: Path, manifest: dict) -> bool:
    item = _item_for(manifest, _rel(path))
    if not item:
        return False
    parts = item.get("parts") or []
    if parts:
        return all((WORKSPACE / p).exists() for p in parts)
    return (WORKSPACE / item["zip"]).exists()


def pack_paths(paths: list[Path]) -> dict:
    manifest = _load_manifest()
    packed = []
    skipped = []
    for path in paths:
        path = path.resolve()
        if not path.is_file():
            continue
        if path.stat().st_size <= THRESHOLD:
            skipped.append({"path": _rel(path), "reason": "under threshold"})
            continue
        if is_pack_artifact(path):
            skipped.append({"path": _rel(path), "reason": "pack artifact"})
            continue
        if _already_packed(path, manifest):
            skipped.append({"path": _rel(path), "reason": "already packed"})
            continue
        packed.append(pack_file(path, manifest))
    if packed:
        _save_manifest(manifest)
    return {"packed": packed, "skipped": skipped}


def scan_and_pack(roots: list[Path] | None = None) -> dict:
    if not roots:
        roots = [
            WORKSPACE / "datasets",
            WORKSPACE / "papers",
            WORKSPACE / "docs",
        ]
    files: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for f in iter_large_files(root):
            key = f.resolve()
            if key not in seen:
                seen.add(key)
                files.append(f)
    return pack_paths(files)


def unpack_item(item: dict, *, overwrite: bool = False) -> dict:
    original = WORKSPACE / item["original"]
    if original.exists() and not overwrite:
        return {"path": item["original"], "status": "present"}
    zip_path = WORKSPACE / item["zip"]
    parts = [WORKSPACE / p for p in (item.get("parts") or [])]
    assembled_tmp = False
    if parts:
        missing = [str(p) for p in parts if not p.exists()]
        if missing:
            return {"path": item["original"], "status": "error",
                    "error": f"missing parts: {missing}"}
        _assemble_parts(parts, zip_path)
        assembled_tmp = True
    if not zip_path.exists():
        return {"path": item["original"], "status": "error",
                "error": f"missing zip {item['zip']}"}
    original.parent.mkdir(parents=True, exist_ok=True)
    _extract_zip(zip_path, original.parent, original.name)
    if assembled_tmp:
        zip_path.unlink(missing_ok=True)
    return {"path": item["original"], "status": "unpacked",
            "bytes": original.stat().st_size}


def unpack_all(overwrite: bool = False) -> dict:
    manifest = _load_manifest()
    results = [unpack_item(item, overwrite=overwrite)
               for item in manifest.get("items") or []]
    return {"unpacked": results, "count": len(results)}


def hook_pack(paths: list[Path | str] | None = None) -> dict:
    """Best-effort pack for other scripts. Never raises."""
    try:
        roots = [Path(p) for p in paths] if paths else None
        report = scan_and_pack(roots)
        n = len(report.get("packed") or [])
        if n:
            eprint(f"github-pack: packed {n} file(s) over 100 MB")
        return report
    except Exception as exc:  # noqa: BLE001
        eprint(f"! github-pack failed: {exc}")
        return {"packed": [], "error": str(exc)}


def status() -> dict:
    manifest = _load_manifest()
    rows = []
    for item in manifest.get("items") or []:
        original = WORKSPACE / item["original"]
        zip_path = WORKSPACE / item["zip"]
        parts = [WORKSPACE / p for p in (item.get("parts") or [])]
        rows.append({
            "original": item["original"],
            "unpacked_on_disk": original.exists(),
            "zip_on_disk": zip_path.exists(),
            "parts_on_disk": sum(1 for p in parts if p.exists()),
            "parts": len(parts),
            "original_bytes": item.get("original_bytes"),
            "zip_bytes": item.get("zip_bytes"),
        })
    packed_originals = {item["original"] for item in manifest.get("items") or []}
    large = []
    for root in (WORKSPACE / "datasets", WORKSPACE / "papers", WORKSPACE / "docs"):
        if root.exists():
            large.extend(
                _rel(p) for p in iter_large_files(root)
                if _rel(p) not in packed_originals
            )
    return {
        "threshold_bytes": THRESHOLD,
        "items": rows,
        "unpacked_missing": [r["original"] for r in rows if not r["unpacked_on_disk"]],
        "still_over_limit": large,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["pack", "unpack", "status"])
    ap.add_argument("--path", type=Path, help="File or directory to pack/unpack")
    ap.add_argument("--overwrite", action="store_true",
                    help="unpack: replace existing unpacked files")
    args = ap.parse_args()

    if args.action == "status":
        emit(status())
        return
    if args.action == "unpack":
        emit(unpack_all(overwrite=args.overwrite))
        return
    roots = None
    if args.path:
        path = args.path if args.path.is_absolute() else WORKSPACE / args.path
        roots = [path]
    emit(scan_and_pack(roots))


if __name__ == "__main__":
    main()
