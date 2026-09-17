#!/usr/bin/env python3
"""T006: do the three Agilent (GPL6480) validators share patients?

E003's verdict rests on GSE32062 and GSE17260 clearing DC >= 0.03, plus GSE49997.
GSE32062, GSE17260 and GSE53963 are all Yoshihara GPL6480 series, and GEO gives a
re-hybridised patient a fresh GSM id, so sample-id checks cannot rule out overlap
(F010). Duplicate profiles of the same tumour correlate far above unrelated pairs.

Cross-correlates every sample of each GPL6480 cohort against every sample of the
others (Spearman on the top-variance genes, Pearson on ranks as a cross-check),
flags pairs above --threshold, and prints the clinical fields of flagged pairs so a
match can be confirmed or dismissed. Writes a run record with metric rows.

    colab_sync.py run agent/experiments/t006_validator_overlap.py [--threshold 0.95]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import colab_env as ce

AGILENT = ["gse32062", "gse53963", "gse17260"]
CLIN = ["age_years", "figo_stage", "residual_disease", "os_time_days", "os_event"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.95, help="flag pairs above this correlation")
    ap.add_argument("--n-genes", type=int, default=3000, help="top-variance genes used for correlation")
    args = ap.parse_args()

    ce.require("pandas", "numpy")
    import numpy as np
    import pandas as pd

    val = ce.ensure_dataset("os-validation", csv_only=False)
    lab = pd.read_csv(val / "labels.csv")
    lab["sample_id"] = lab["sample_id"].astype(str)
    lab = lab.set_index("sample_id")
    expr = pd.read_csv(val / "expression_validation.csv", index_col=0)
    expr.columns = expr.columns.astype(str)
    ce.eprint(f"validation expression {expr.shape}, labels {lab.shape}")

    keep = [s for s in expr.columns if lab.loc[s, "cohort"] in AGILENT]
    X = expr[keep]
    cohorts = lab.loc[keep, "cohort"]
    print({"cohort_sizes": cohorts.value_counts().to_dict(), "genes": int(X.shape[0])})

    # Within-sample ranks first (platform-native scales differ between the two-colour
    # GSE53963 and the one-colour series), then the most variable genes, then Pearson
    # on those ranks == Spearman on the shared genes.
    R = X.rank(axis=0, pct=True)
    R = R.dropna(axis=0, how="any")
    var = R.var(axis=1)
    R = R.loc[var.nlargest(min(args.n_genes, len(var))).index]
    ce.eprint(f"correlating on {R.shape[0]} genes complete in all {R.shape[1]} Agilent samples")

    Z = (R - R.mean()) / R.std(ddof=0)
    C = pd.DataFrame((Z.to_numpy().T @ Z.to_numpy()) / len(Z), index=R.columns, columns=R.columns)

    rows, pairs = [], []
    for i, a in enumerate(AGILENT):
        for b in AGILENT[i + 1:]:
            sub = C.loc[cohorts[cohorts == a].index, cohorts[cohorts == b].index]
            vals = sub.to_numpy().ravel()
            best = sub.max(axis=1)
            hits = [(ra, sub.columns[int(np.argmax(sub.loc[ra].to_numpy()))], float(best[ra]))
                    for ra in sub.index if best[ra] >= args.threshold]
            rows.append({
                "pair": f"{a}|{b}", "n_a": int(sub.shape[0]), "n_b": int(sub.shape[1]),
                "max": float(vals.max()), "p99": float(np.percentile(vals, 99)),
                "median": float(np.median(vals)), "n_flagged": len(hits),
            })
            pairs.extend({"cohort_a": a, "cohort_b": b, "sample_a": x, "sample_b": y, "r": r}
                         for x, y, r in hits)

    # Within-cohort maxima give the scale of "same platform, different patient".
    within = {}
    for a in AGILENT:
        idx = cohorts[cohorts == a].index
        sub = C.loc[idx, idx].to_numpy().copy()
        np.fill_diagonal(sub, np.nan)
        within[a] = {"max": float(np.nanmax(sub)), "p99": float(np.nanpercentile(sub, 99)),
                     "median": float(np.nanmedian(sub))}

    table = pd.DataFrame(rows)
    print("\ncross-cohort sample correlations (Spearman on top-variance genes)")
    print(table.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\nwithin-cohort (different patients, same platform) for scale")
    print(pd.DataFrame(within).T.to_string(float_format=lambda x: f"{x:.3f}"))

    print(f"\nflagged pairs (r >= {args.threshold}): {len(pairs)}")
    for p in sorted(pairs, key=lambda d: -d["r"])[:40]:
        a, b = lab.loc[p["sample_a"]], lab.loc[p["sample_b"]]
        fields = "  ".join(f"{c}={a.get(c)}/{b.get(c)}" for c in CLIN)
        print(f"  r={p['r']:.3f}  {p['sample_a']}({p['cohort_a']}) ~ {p['sample_b']}({p['cohort_b']})  {fields}")

    # Batch effects between series compress cross-cohort correlation, so the threshold alone
    # is weak evidence. Show the strongest pairs whatever their r, with the clinical fields
    # that would have to agree for the same patient.
    print("\ntop 5 cross-cohort pairs per cohort pair, threshold or not")
    top = []
    for i, a in enumerate(AGILENT):
        for b in AGILENT[i + 1:]:
            sub = C.loc[cohorts[cohorts == a].index, cohorts[cohorts == b].index]
            flat = sub.stack().sort_values(ascending=False)
            for (x, y), r in flat.head(5).items():
                la, lb = lab.loc[x], lab.loc[y]
                fields = "  ".join(f"{c}={la.get(c)}/{lb.get(c)}" for c in CLIN)
                print(f"  {a}|{b}  r={r:.3f}  {x} ~ {y}  {fields}")
                top.append({"cohort_a": a, "cohort_b": b, "sample_a": x, "sample_b": y, "r": float(r)})

    # Clinical fingerprint: the same patient in two series carries the same survival time,
    # stage, residual disease and vital status. Exact OS-day agreement is the strong signal.
    print("\nclinical fingerprint matches across cohorts (same os_time_days +-1, event, stage, residual)")
    fingerprints = []
    for i, a in enumerate(AGILENT):
        for b in AGILENT[i + 1:]:
            ga, gb = lab.loc[cohorts[cohorts == a].index], lab.loc[cohorts[cohorts == b].index]
            for x, ra in ga.iterrows():
                for y, rb in gb.iterrows():
                    if not np.isfinite(ra["os_time_days"]) or not np.isfinite(rb["os_time_days"]):
                        continue
                    if abs(float(ra["os_time_days"]) - float(rb["os_time_days"])) > 1:
                        continue
                    if int(ra["os_event"]) != int(rb["os_event"]):
                        continue
                    if str(ra["figo_stage"]) != str(rb["figo_stage"]):
                        continue
                    if str(ra["residual_disease"]) != str(rb["residual_disease"]):
                        continue
                    fingerprints.append({"cohort_a": a, "cohort_b": b, "sample_a": x, "sample_b": y,
                                         "os_time_days": float(ra["os_time_days"]),
                                         "os_event": int(ra["os_event"]),
                                         "r": float(C.loc[x, y])})
    print(f"  {len(fingerprints)} candidate matches")
    for f in sorted(fingerprints, key=lambda d: -d["r"])[:20]:
        print(f"  {f['cohort_a']}|{f['cohort_b']}  {f['sample_a']} ~ {f['sample_b']}  "
              f"os={f['os_time_days']:.0f}d event={f['os_event']}  r={f['r']:.3f}")

    # Cross-check the confirmed clinical-fingerprint duplicates (t006_geo_fingerprint.py):
    # if those pairs are the same tumour, their correlation should stand out against the
    # cross-cohort background even with the two series processed differently.
    fp_stats = None
    fp_file = pathlib.Path(__file__).with_name("t006_fingerprint_pairs.json")
    if fp_file.exists():
        fp = json.loads(fp_file.read_text())
        sub = C.loc[cohorts[cohorts == "gse32062"].index, cohorts[cohorts == "gse17260"].index]
        bg = sub.to_numpy().ravel()
        vals, ranks = [], []
        for x, ms in fp.items():
            for m in ms:
                if x in sub.columns and m in sub.index:
                    r = float(sub.loc[m, x])
                    vals.append(r)
                    ranks.append(int((sub[x].to_numpy() > r).sum()) + 1)  # 1 = best match of 260
        if vals:
            fp_stats = {
                "n_pairs": len(vals), "median_r": float(np.median(vals)),
                "max_r": float(max(vals)), "background_median_r": float(np.median(bg)),
                "background_p99_r": float(np.percentile(bg, 99)),
                "pct_above_background_p99": float(np.mean([v > np.percentile(bg, 99) for v in vals])),
                "median_rank_of_partner_in_260": float(np.median(ranks)),
                "n_partner_is_top1": int(sum(1 for r in ranks if r == 1)),
                "n_partner_in_top10": int(sum(1 for r in ranks if r <= 10)),
            }
            print("\nclinical-fingerprint duplicate pairs vs correlation background")
            for k, v in fp_stats.items():
                print(f"  {k}: {v}")

    # How many GSE17260 patients are in GSE32062 in total? A re-hybridised tumour should be
    # each other's best match in both directions; for unrelated samples that happens by
    # chance about 1/260 of the time. Mutual best matches therefore size the overlap, and
    # the confirmed fingerprint pairs calibrate it.
    ga = cohorts[cohorts == "gse17260"].index
    gb = cohorts[cohorts == "gse32062"].index
    M = C.loc[ga, gb]
    best_b = M.idxmax(axis=1)          # for each GSE17260 sample, its best GSE32062 partner
    best_a = M.idxmax(axis=0)          # and the reverse
    mutual = [(x, best_b[x]) for x in ga if best_a[best_b[x]] == x]
    fp_set = set()
    if fp_file.exists():
        fp_set = {(x, m) for x, ms in json.loads(fp_file.read_text()).items() for m in ms}
    mutual_stats = {
        "n_gse17260": int(len(ga)), "n_gse32062": int(len(gb)),
        "n_mutual_best": len(mutual),
        "expected_by_chance": round(len(ga) / len(gb), 2),
        "n_mutual_also_fingerprint_confirmed": sum(1 for p in mutual if p in fp_set),
        "n_fingerprint_confirmed": len(fp_set),
        "median_r_mutual": float(np.median([C.loc[x, y] for x, y in mutual])) if mutual else None,
    }
    print("\nmutual best matches GSE17260 <-> GSE32062")
    for k, v in mutual_stats.items():
        print(f"  {k}: {v}")

    metrics = []
    for r in rows:
        a, b = r["pair"].split("|")
        metrics.append(ce.metric_row("profile_correlation", f"{a}-vs-{b}", "external",
                                     "max_cross_cohort_r", r["max"], n=r["n_a"] * r["n_b"]))
        metrics.append(ce.metric_row("profile_correlation", f"{a}-vs-{b}", "external",
                                     "n_samples_flagged", r["n_flagged"], n=r["n_a"]))
    metrics += [ce.metric_row("clinical_fingerprint", f"{a}-vs-{b}", "external", "n_candidate_matches",
                              sum(1 for f in fingerprints if f["cohort_a"] == a and f["cohort_b"] == b))
                for i, a in enumerate(AGILENT) for b in AGILENT[i + 1:]]
    ce.save_run("t006-validator-overlap", {
        "task": "T006 patient overlap between GPL6480 validators",
        "threshold": args.threshold, "n_genes": int(R.shape[0]),
        "cohort_sizes": cohorts.value_counts().to_dict(),
        "cross_cohort": rows, "within_cohort": within, "flagged_pairs": pairs,
        "fingerprint_pair_correlations": fp_stats,
        "mutual_best_matches": mutual_stats,
        "mutual_pairs": [{"gse17260": x, "gse32062": y} for x, y in mutual],
        "top_pairs": top, "clinical_fingerprint_matches": fingerprints,
    }, metrics=metrics)
    return 0


if __name__ == "__main__":
    sys.exit(main())
