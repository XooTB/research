#!/usr/bin/env python3
"""Read back results from Colab sessions. Emits JSON.

Closes the loop for an agent that cannot execute notebook cells itself: the
notebook pushes a run record, and this reads it, so "verify the result" and
"did the change help" are answerable from the terminal instead of by asking the
user what the output said.

Records are written by colab_env.save_run() into
.research/colab/runs/<utc>-<name>/run.json.

Usage:
    colab_runs.py                       # list runs, newest first
    colab_runs.py --last                # full record of the newest run
    colab_runs.py --name <substr>       # filter by run name
    colab_runs.py --compare             # metric table across runs
    colab_runs.py --compare --name <s>  # ... restricted to matching runs
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import emit, eprint, ws_path


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


def summarize(run: dict) -> dict:
    gpu = (run.get("env") or {}).get("gpu") or {}
    return {
        "name": run.get("name"),
        "saved_at": run.get("saved_at"),
        "dir": run.get("_dir"),
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
    args = ap.parse_args()

    runs = load_runs(args.name)
    if not runs:
        emit({
            "count": 0,
            "runs_dir": str(runs_dir()),
            "hint": "no run records. Run a notebook in notebooks/ on a Colab "
                    "kernel, let its last cell push, then git pull.",
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
