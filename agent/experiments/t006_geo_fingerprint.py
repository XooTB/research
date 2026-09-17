#!/usr/bin/env python3
"""T006: patient-level fingerprint match between GSE17260 and GSE32062 (stdlib, local).

The expression-correlation arm of T006 (t006_validator_overlap.py, on Colab) is blunt
here: the two series were processed differently, so even a repeated patient correlates
only ~0.3-0.5, while single-field matches (equal OS day) are meaningless because both
series record survival in whole months on the same grid.

Both GEO series matrices carry the same seven clinical fields per sample: stage, residual
/ cytoreduction, grade, PFS months, recurrence, OS months, death. The same patient must
agree on all seven. This counts exact 7-field matches and compares that against a
permutation null (fields shuffled within each series), which is what tells a real overlap
from coincidence.

    .venv/bin/python agent/experiments/t006_geo_fingerprint.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
DATA = WORKSPACE / "datasets" / "ovarian-cancer-prognosis-ml"
SERIES = {
    "gse17260": (DATA / "gse17260-ovarian-expression-series-matrix" / "GSE17260_series_matrix.txt",
                 {"stage": "stage", "residual": "cytoreductive surgery", "grade": "tumor grade",
                  "pfs_m": "progression-free survival (m)", "rec": "recurrence (1)",
                  "os_m": "overall survival (m)", "death": "death (1)"}),
    "gse32062": (DATA / "gse32062-gpl6480-ovarian-expression-series-matrix" / "GSE32062-GPL6480_series_matrix.txt",
                 {"stage": "stage", "residual": "surgery status", "grade": "grading",
                  "pfs_m": "pfs (m)", "rec": "rec (1)",
                  "os_m": "os (m)", "death": "death (1)"}),
}
# "not optimal" (GSE17260) and "suboptimal" (GSE32062) are the same category.
RESIDUAL = {"not optimal": "suboptimal", "sub-optimal": "suboptimal", "suboptimal": "suboptimal",
            "optimal": "optimal"}
FIELDS = ["stage", "residual", "grade", "pfs_m", "rec", "os_m", "death"]


def parse(path: Path, keys: dict[str, str]) -> dict[str, dict[str, str]]:
    samples: list[str] = []
    rows: dict[str, list[str]] = {}
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("!Sample_geo_accession"):
            samples = [c.strip('"') for c in line.split("\t")[1:]]
        elif line.startswith("!Sample_characteristics_ch1"):
            cells = [c.strip('"') for c in line.split("\t")[1:]]
            head = cells[0].split(":", 1)[0].strip().lower() if cells and ":" in cells[0] else None
            if head:
                rows[head] = [c.split(":", 1)[1].strip().lower() if ":" in c else "" for c in cells]
        elif line.startswith("!series_matrix_table_begin"):
            break
    out: dict[str, dict[str, str]] = {}
    for i, gsm in enumerate(samples):
        rec = {}
        for field, key in keys.items():
            vals = rows.get(key.lower())
            v = vals[i] if vals and i < len(vals) else ""
            if field == "residual":
                v = RESIDUAL.get(v, v)
            if field == "stage":
                v = v.upper().replace("STAGE", "").strip()
            rec[field] = v
        out[gsm] = rec
    return out


def key(rec: dict[str, str]) -> tuple:
    return tuple(rec[f] for f in FIELDS)


def count_matches(a: dict, b: dict) -> tuple[int, int, list]:
    bkeys: dict[tuple, list[str]] = {}
    for gsm, rec in b.items():
        bkeys.setdefault(key(rec), []).append(gsm)
    hits = [(gsm, bkeys[key(rec)]) for gsm, rec in a.items() if key(rec) in bkeys]
    return len(hits), sum(len(v) for _, v in hits), hits


def main() -> int:
    parsed = {name: parse(path, keys) for name, (path, keys) in SERIES.items()}
    for name, recs in parsed.items():
        complete = sum(1 for r in recs.values() if all(r[f] for f in FIELDS))
        print(f"{name}: {len(recs)} samples, {complete} with all 7 fields", file=sys.stderr)

    a, b = parsed["gse17260"], parsed["gse32062"]
    a = {k: v for k, v in a.items() if all(v[f] for f in FIELDS)}
    b = {k: v for k, v in b.items() if all(v[f] for f in FIELDS)}
    n_matched, n_pairs, hits = count_matches(a, b)

    # Permutation null: shuffle each field independently within GSE32062, keeping every
    # field's marginal distribution, and recount. This is what coincidence looks like.
    rng = random.Random(0)
    null = []
    bl = list(b.values())
    for _ in range(200):
        cols = {f: [r[f] for r in bl] for f in FIELDS}
        for f in FIELDS:
            rng.shuffle(cols[f])
        shuffled = {f"s{i}": {f: cols[f][i] for f in FIELDS} for i in range(len(bl))}
        null.append(count_matches(a, shuffled)[0])
    null.sort()
    exceed = sum(1 for v in null if v >= n_matched)

    result = {
        "gse17260_complete": len(a), "gse32062_complete": len(b),
        "matched_gse17260_samples": n_matched, "matched_pairs": n_pairs,
        "null_median": null[len(null) // 2], "null_p95": null[int(len(null) * 0.95)],
        "null_max": null[-1], "permutations": len(null),
        "p_value": (exceed + 1) / (len(null) + 1),
        "examples": [{"gse17260": g, "gse32062": m, **a[g]} for g, m in hits[:10]],
    }
    print(json.dumps(result, indent=2))
    # The Colab arm reads these pairs back to ask whether confirmed duplicates also look
    # alike in expression (agent/ is synced to the runtime).
    pairs_path = Path(__file__).with_name("t006_fingerprint_pairs.json")
    pairs_path.write_text(json.dumps({g: m for g, m in hits}, indent=1))
    print(f"wrote {pairs_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
