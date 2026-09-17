#!/usr/bin/env python3
"""Read back results from Colab sessions. Emits JSON.

Records are written on the runtime by colab_env.save_run() into
.research/colab/runs/<utc>-<name>/run.json and copied back by colab_sync.py
(run / logs / pull / stop), so "verify the result" and "did the change help"
are answerable from the terminal.

Usage:
    colab_runs.py                       # list runs, newest first
    colab_runs.py --last                # full record of the newest run
    colab_runs.py --name <substr>       # filter by run name
    colab_runs.py --compare             # metric table across runs
    colab_runs.py --compare --name <s>  # ... restricted to matching runs
    colab_runs.py --import-notebook <f> # harvest records from an executed notebook
    colab_runs.py --ledger              # external-validation scorings, per candidate
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from common import WORKSPACE, emit, eprint, slugify, ws_path

# Notebooks print their record between these markers, so an executed notebook
# (e.g. the <name>_output.ipynb that `colab_sync.py run` writes) carries its
# results even without the runs/ folder.
RECORD_BEGIN = "===RUN-RECORD-BEGIN==="
RECORD_END = "===RUN-RECORD-END==="
LEDGER_REL = ".research/validation-ledger.jsonl"
RECORD_BLOCK = re.compile(
    re.escape(RECORD_BEGIN) + r"(.*?)" + re.escape(RECORD_END), re.DOTALL)


def runs_dir() -> Path:
    base = ws_path("paths.db_path", ".research/library.db").parent
    return base / "colab" / "runs"


def load_runs(name: str | None = None) -> list[dict]:
    root = runs_dir()
    if not root.is_dir():
        return []
    out = []
    for d in sorted(root.iterdir(), reverse=True):
        record = d / "run.json"
        if not record.is_file():
            continue
        try:
            data = json.loads(record.read_text(encoding="utf-8"))
        except ValueError as exc:
            eprint(f"! skipping unreadable {record}: {exc}")
            continue
        if name and name.lower() not in str(data.get("name", "")).lower():
            continue
        data["_dir"] = str(d)
        data["_files"] = sorted(p.name for p in d.iterdir() if p.name != "run.json")
        out.append(data)
    return out


def _output_text(cell: dict) -> str:
    """All textual output of a cell, stream and rich alike."""
    parts = []
    for out in cell.get("outputs") or []:
        if out.get("output_type") == "stream":
            parts.append("".join(out.get("text") or []))
        else:
            parts.append("".join((out.get("data") or {}).get("text/plain") or []))
    return "\n".join(parts)


def import_notebook(path: Path) -> dict:
    """Write run records found in an executed notebook's output into runs/."""
    try:
        nb = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"error": f"cannot read {path}: {exc}"}

    blocks = [m for cell in nb.get("cells") or []
              for m in RECORD_BLOCK.findall(_output_text(cell))]

    imported, skipped, errors = [], [], []
    for raw in blocks:
        try:
            record = json.loads(raw.strip())
        except ValueError as exc:
            errors.append(f"unparseable record block: {exc}")
            continue

        stamp = record.get("saved_at") or "unknown"
        dest = runs_dir() / f"{stamp}-{slugify(str(record.get('name', 'run')))}"
        target = dest / "run.json"
        if target.exists():
            skipped.append({"dir": str(dest), "reason": "already imported"})
            continue
        dest.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        if record.get("validation"):
            from colab_env import upsert_ledger
            upsert_ledger(record["validation"], WORKSPACE / LEDGER_REL)
        imported.append({"dir": str(dest), "name": record.get("name"),
                         "metrics": flatten_metrics(record.get("result"))})

    return {
        "notebook": str(path),
        "blocks_found": len(blocks),
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "hint": None if blocks else
                "no record blocks in the output — run the notebook with "
                "colab_sync.py run, then import the <name>_output.ipynb it writes",
    }


def flatten_metrics(obj, prefix: str = "") -> dict:
    """Numeric leaves of a result payload, as dotted keys."""
    flat: dict = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            flat.update(flatten_metrics(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, bool):
        pass
    elif isinstance(obj, (int, float)):
        flat[prefix] = obj
    return flat


def provenance_summary(run: dict) -> dict | None:
    prov = run.get("provenance")
    if not prov:
        return None
    git = prov.get("git") or {}
    return {
        "via": prov.get("via"),
        "experiment": prov.get("experiment"),
        "script": prov.get("script"),
        "args": prov.get("args"),
        "code_commit": git.get("code_commit") or git.get("head"),
        "dirty": git.get("dirty"),
        "datasets": {k: v.get("sha256") for k, v in (prov.get("datasets") or {}).items()},
    }


def summarize(run: dict) -> dict:
    gpu = (run.get("env") or {}).get("gpu") or {}
    return {
        "name": run.get("name"),
        "saved_at": run.get("saved_at"),
        "dir": run.get("_dir"),
        "provenance": provenance_summary(run),
        "validation": [v.get("candidate") for v in run.get("validation") or []],
        "gpu": gpu.get("name"),
        "device": (run.get("result") or {}).get("device"),
        "metrics": flatten_metrics(run.get("result")),
        "files": run.get("_files"),
    }


def compare(runs: list[dict]) -> dict:
    """Per-metric values across runs, oldest first, plus the change."""
    rows = [summarize(r) for r in reversed(runs)]
    keys = sorted({k for r in rows for k in r["metrics"]})
    table = {}
    for k in keys:
        series = [{"run": r["saved_at"], "value": r["metrics"].get(k)} for r in rows]
        present = [s["value"] for s in series if s["value"] is not None]
        table[k] = {
            "series": series,
            "first": present[0] if present else None,
            "last": present[-1] if present else None,
            "delta": (present[-1] - present[0]) if len(present) > 1 else None,
        }
    return {"runs": [r["saved_at"] for r in rows], "metrics": table}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--last", action="store_true", help="full record of the newest run")
    ap.add_argument("--name", help="filter by substring of the run name")
    ap.add_argument("--compare", action="store_true", help="metric table across runs")
    ap.add_argument("--ledger", action="store_true",
                    help="external-validation scorings from .research/validation-ledger.jsonl")
    ap.add_argument("--import-notebook", type=Path, metavar="FILE",
                    help="harvest run records from a notebook's saved cell output")
    args = ap.parse_args()

    if args.import_notebook:
        path = args.import_notebook
        emit(import_notebook(path if path.is_absolute() else WORKSPACE / path))
        return

    if args.ledger:
        from colab_env import read_ledger
        entries = read_ledger(WORKSPACE / LEDGER_REL)
        by_candidate: dict = {}
        for e in entries:
            by_candidate.setdefault(e.get("candidate"), []).append(e)
        emit({"entries": len(entries), "candidates": {
            c: {"times_scored": len(es), "runs": [e.get("run") for e in es],
                "rescore_reasons": [e.get("reason") for e in es if e.get("reason")]}
            for c, es in by_candidate.items()}})
        return

    runs = load_runs(args.name)
    if not runs:
        emit({
            "count": 0,
            "runs_dir": str(runs_dir()),
            "hint": "no run records. Run an experiment with colab_sync.py run; "
                    "records are pulled back automatically.",
        })
        return

    if args.last:
        emit(runs[0])
    elif args.compare:
        emit(compare(runs))
    else:
        emit({"count": len(runs), "runs": [summarize(r) for r in runs]})


if __name__ == "__main__":
    main()
