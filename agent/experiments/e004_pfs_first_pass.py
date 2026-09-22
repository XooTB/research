#!/usr/bin/env python3
"""E004: does expression add to clinical factors for PROGRESSION, as it did for death?

Mirrors E003's design on the progression endpoint so the two are comparable: a two-stage
model (Coxnet expression score, then a Cox on residual + stage + that score, fit on the
pool and stratified by cohort) against the same Cox without the score.

Two phases, deliberately separated so tuning cannot see validation outcomes:

    run --experiment E004 e004_pfs_first_pass.py --phase tune     # pool CV only; picks the model
    run --experiment E004 e004_pfs_first_pass.py --phase final --n-genes 500 --l1-ratio 1.0

`tune` never loads the validation labels. `final` registers the frozen candidate
(pfs-first-pass-v1) before it touches them and scores them once. `--dry-run` on `final`
replaces validation outcomes with noise and registers nothing, for smoke-testing the path.

Success rule (pre-registered, research/os-hgsoc/experiments/E004-pfs-pfi-endpoint.md):
    e004_success_indicator = 1 if (cohorts with dC >= 0.03) >= 2 and pooled_ci_lo > 0 else 0
on the three INDEPENDENT validators; GSE17260 is scored but excluded from the rule (D010).
"""
from __future__ import annotations

import argparse
import sys

import colab_env as ce

POOL_DS, VAL_DS = "pfs-training-pool", "pfs-validation"
EXPR_POOL = ("os-training-pool", "expression_pool.csv")
EXPR_VAL = ("os-validation", "expression_validation.csv")
CLIN = ["residual_subopt", "stage_ord"]
# GSE17260 is scored for comparability but excluded from the rule: 37% of its patients are
# also in GSE32062 (F012, D010).
RULE_COHORTS = ["gse32062", "gse140082", "gse49997"]
REDUNDANT = ["gse17260"]
CANDIDATE = "pfs-first-pass-v1"
SEED, N_BOOT = 0, 300


def load(ds, expr_ds, expr_name):
    import numpy as np
    import pandas as pd
    import os_clinical

    root = ce.ensure_dataset(ds, csv_only=False)
    lab = pd.read_csv(root / "labels.csv")
    lab["sample_id"] = lab["sample_id"].astype(str)
    lab = lab.set_index("sample_id")
    lab["residual_subopt"] = lab["residual_disease"].map(os_clinical.recode_residual)
    lab["stage_ord"] = lab["figo_stage"].map(os_clinical.recode_stage)
    lab["time"] = pd.to_numeric(lab["pfs_time_days"], errors="coerce")
    lab["event"] = pd.to_numeric(lab["pfs_event"], errors="coerce").astype(int)
    lab = lab.loc[lab["time"].notna() & (lab["time"] > 0)]

    expr_root = ce.ensure_dataset(expr_ds, csv_only=False)
    expr = pd.read_csv(expr_root / expr_name, index_col=0)
    expr.columns = expr.columns.astype(str)
    keep = [s for s in expr.columns if s in lab.index]
    missing = [s for s in lab.index if s not in expr.columns]
    if missing:
        ce.eprint(f"{ds}: {len(missing)} labelled samples have no expression column; dropped")
    lab = lab.loc[keep]
    return lab, expr[keep].T.astype(np.float32)


def prepare(X_tr, X_va, n_genes):
    """Within-sample ranks, top-variance genes on the POOL only, z-scored on the pool."""
    import numpy as np
    import pandas as pd
    from sklearn.preprocessing import StandardScaler

    R_tr = X_tr.rank(axis=1, pct=True, method="average")
    keep = R_tr.var(axis=0, ddof=0).nlargest(n_genes).index
    scaler = StandardScaler()
    Z_tr = pd.DataFrame(scaler.fit_transform(R_tr[keep]), index=X_tr.index, columns=keep,
                        dtype=np.float32)
    Z_va = None
    if X_va is not None:
        R_va = X_va.rank(axis=1, pct=True, method="average").fillna(0.5)
        Z_va = pd.DataFrame(scaler.transform(R_va[keep]), index=X_va.index, columns=keep,
                            dtype=np.float32)
    return Z_tr, Z_va, list(keep)


# --- metrics ---------------------------------------------------------------------------

def _helpers():
    import numpy as np
    from lifelines.utils import concordance_index

    def cindex(t, e, r):
        import numpy as np
        t, e, r = np.asarray(t, float), np.asarray(e, int), np.asarray(r, float)
        ok = np.isfinite(t) & np.isfinite(r) & np.isfinite(e)
        if ok.sum() < 10 or e[ok].sum() < 2:
            return float("nan")
        return float(concordance_index(t[ok], -r[ok], e[ok]))

    def boot_c(t, e, r):
        try:
            return concordance_index(t, -r, e)
        except ZeroDivisionError:
            return np.nan

    def cindex_ci(t, e, r, n_boot=N_BOOT, seed=SEED):
        t, e, r = np.asarray(t, float), np.asarray(e, int), np.asarray(r, float)
        ok = np.isfinite(t) & np.isfinite(r) & np.isfinite(e)
        t, e, r = t[ok], e[ok], r[ok]
        point = cindex(t, e, r)
        gen = np.random.default_rng(seed)
        stats = []
        for _ in range(n_boot):
            ix = gen.integers(0, len(t), len(t))
            if e[ix].sum() < 2:
                continue
            v = boot_c(t[ix], e[ix], r[ix])
            if np.isfinite(v):
                stats.append(v)
        if len(stats) < 20:
            return point, None, None
        lo, hi = np.percentile(stats, [2.5, 97.5])
        return point, float(lo), float(hi)

    def delta_ci(t, e, a, b, n_boot=N_BOOT, seed=SEED):
        t, e = np.asarray(t, float), np.asarray(e, int)
        a, b = np.asarray(a, float), np.asarray(b, float)
        ok = np.isfinite(t) & np.isfinite(e) & np.isfinite(a) & np.isfinite(b)
        t, e, a, b = t[ok], e[ok], a[ok], b[ok]
        point = cindex(t, e, a) - cindex(t, e, b)
        if not np.isfinite(point):
            return None, None, None, None
        gen = np.random.default_rng(seed)
        stats = []
        for _ in range(n_boot):
            ix = gen.integers(0, len(t), len(t))
            if e[ix].sum() < 2:
                continue
            d = boot_c(t[ix], e[ix], a[ix]) - boot_c(t[ix], e[ix], b[ix])
            if np.isfinite(d):
                stats.append(d)
        if len(stats) < 20:
            return float(point), None, None, None
        lo, hi = np.percentile(stats, [2.5, 97.5])
        return float(point), float(lo), float(hi), float(np.std(stats, ddof=1))

    def random_effects(est, ses):
        y = np.asarray([np.nan if v is None else v for v in est], float)
        s = np.asarray([np.nan if v is None else v for v in ses], float)
        ok = np.isfinite(y) & np.isfinite(s) & (s > 0)
        y, s = y[ok], s[ok]
        if len(y) < 2:
            return None
        w = 1 / s**2
        fixed = np.sum(w * y) / np.sum(w)
        q = float(np.sum(w * (y - fixed) ** 2))
        df = len(y) - 1
        c = np.sum(w) - np.sum(w**2) / np.sum(w)
        tau2 = max(0.0, (q - df) / c) if c > 0 else 0.0
        wr = 1 / (s**2 + tau2)
        est_ = float(np.sum(wr * y) / np.sum(wr))
        se = float(np.sqrt(1 / np.sum(wr)))
        return {"estimate": est_, "ci_lo": est_ - 1.96 * se, "ci_hi": est_ + 1.96 * se,
                "se": se, "tau2": float(tau2),
                "i2": max(0.0, (q - df) / q) if q > 0 else 0.0, "k": int(len(y))}

    return cindex, cindex_ci, delta_ci, random_effects


def _models():
    import numpy as np
    import pandas as pd
    from lifelines import CoxPHFitter
    from sklearn.model_selection import StratifiedKFold
    from sksurv.linear_model import CoxnetSurvivalAnalysis
    from sksurv.util import Surv

    def lp(cph, feat):
        cols = list(cph.params_.index)
        return feat[cols].astype(float).to_numpy() @ cph.params_.to_numpy()

    def fit_pool_cox(feat, lab, penalizer=0.05):
        df = feat.astype(float).assign(
            duration=lab.loc[feat.index, "time"].values,
            status=lab.loc[feat.index, "event"].values,
            stratum=lab.loc[feat.index, "cohort"].values)
        cph = CoxPHFitter(penalizer=penalizer)
        cph.fit(df, duration_col="duration", event_col="status", strata=["stratum"],
                show_progress=False)
        return cph

    def oof_pool_cox(feat, lab, penalizer=0.05, seed=SEED):
        ev = lab.loc[feat.index, "event"].astype(int)
        groups = lab.loc[feat.index, "cohort"].astype(str) + "_" + ev.astype(str)
        out = pd.Series(index=feat.index, dtype=float)
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=seed).split(feat, groups):
            out.iloc[te] = lp(fit_pool_cox(feat.iloc[tr], lab, penalizer), feat.iloc[te])
        return out

    def coxnet(alphas=None, l1_ratio=1.0, **kw):
        return CoxnetSurvivalAnalysis(l1_ratio=l1_ratio, alphas=alphas, max_iter=100_000,
                                      tol=1e-7, fit_baseline_model=False, **kw)

    return lp, fit_pool_cox, oof_pool_cox, coxnet, Surv, StratifiedKFold


def stratified_cindex(lab, risk, cindex):
    import numpy as np
    num = den = 0.0
    for _, g in lab.groupby("cohort"):
        c = cindex(g["time"], g["event"], risk.loc[g.index])
        if np.isfinite(c):
            w = float(g["event"].sum())
            num, den = num + w * c, den + w
    return num / den if den else float("nan")


def coxnet_oof(Z, lab, l1_ratio, coxnet, Surv, StratifiedKFold, cindex):
    """Pool-CV C-index along the alpha path. Training data only."""
    import numpy as np
    import pandas as pd

    y = Surv.from_arrays(lab["event"].to_numpy().astype(bool), lab["time"].to_numpy())
    alphas = [float(a) for a in coxnet(l1_ratio=l1_ratio, alpha_min_ratio=0.05, n_alphas=12)
              .fit(Z.to_numpy(), y).alphas_]
    oof = {a: pd.Series(index=Z.index, dtype=float) for a in alphas}
    groups = lab["cohort"].astype(str) + "_" + lab["event"].astype(str)
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=SEED).split(Z, groups):
        fold = coxnet(alphas=alphas, l1_ratio=l1_ratio).fit(Z.iloc[tr].to_numpy(), y[tr])
        for a in alphas:
            oof[a].iloc[te] = fold.predict(Z.iloc[te].to_numpy(), alpha=a)
    scored = [{"alpha": a, "l1_ratio": l1_ratio,
               "oof_cindex": stratified_cindex(lab, oof[a], cindex)} for a in alphas]
    return alphas, oof, scored


# --- phases ----------------------------------------------------------------------------

def phase_tune(args):
    """Pool cross-validation only. Validation labels are never loaded here."""
    cindex, _, _, _ = _helpers()
    _, _, _, coxnet, Surv, SKF = _models()

    lab_tr, X_tr = load(POOL_DS, *EXPR_POOL)
    print({"pool_n": int(len(lab_tr)), "events": int(lab_tr["event"].sum()),
           "cohorts": lab_tr["cohort"].value_counts().to_dict()})

    rows, best = [], None
    for n_genes in args.gene_grid:
        Z_tr, _, _ = prepare(X_tr, None, n_genes)
        for l1 in args.l1_grid:
            _, _, scored = coxnet_oof(Z_tr, lab_tr, l1, coxnet, Surv, SKF, cindex)
            top = max(scored, key=lambda d: d["oof_cindex"])
            top["n_genes"] = n_genes
            rows.append(top)
            print(f"  n_genes={n_genes:5d} l1_ratio={l1:.1f}  best alpha={top['alpha']:.4f}"
                  f"  pool CV C={top['oof_cindex']:.3f}")
            if best is None or top["oof_cindex"] > best["oof_cindex"]:
                best = top
    print(f"\nchosen on pool CV: {best}")

    # The number that decides the experiment is not the gene score on its own, it is what the
    # score adds to residual + stage. Both are pool CV, so this spends no validation scoring.
    import pandas as pd
    lp, fit_pool_cox, oof_pool_cox, _, _, _ = _models()
    Z_best, _, _ = prepare(X_tr, None, best["n_genes"])
    _, oof_best, _ = coxnet_oof(Z_best, lab_tr, best["l1_ratio"], coxnet, Surv, SKF, cindex)
    s = oof_best[best["alpha"]]
    s_z = (s - s.mean()) / s.std(ddof=0)
    mask = lab_tr[CLIN].notna().all(axis=1)
    clin_feat = lab_tr.loc[mask, CLIN].astype(float)
    comb_feat = clin_feat.assign(expr_score=s_z.loc[clin_feat.index].values)
    sub = lab_tr.loc[clin_feat.index]
    internal = {
        "n": int(len(sub)), "events": int(sub["event"].sum()),
        "clinical_oof_cindex": stratified_cindex(sub, oof_pool_cox(clin_feat, lab_tr), cindex),
        "combined_oof_cindex": stratified_cindex(sub, oof_pool_cox(comb_feat, lab_tr), cindex),
        "expr_only_oof_cindex": stratified_cindex(sub, s.loc[sub.index], cindex),
    }
    internal["delta_c_pool_cv"] = internal["combined_oof_cindex"] - internal["clinical_oof_cindex"]
    print("\npool CV, complete cases (NOT evidence, but it is what we can see before freezing):")
    for k, v in internal.items():
        print(f"  {k}: {round(v, 4) if isinstance(v, float) else v}")
    stage2 = fit_pool_cox(comb_feat, lab_tr)
    print("\nstage 2 on the pool:")
    print(stage2.summary[["coef", "exp(coef)", "p"]].round(3).to_string())

    rows_out = [ce.metric_row("expr_pfs_coxnet", POOL_DS, "cv", "cindex", r["oof_cindex"],
                              n=int(len(lab_tr))) for r in rows]
    rows_out += [
        ce.metric_row("clinical_transported", POOL_DS, "cv", "cindex",
                      internal["clinical_oof_cindex"], n=internal["n"]),
        ce.metric_row("expr_clin_pfs_cox", POOL_DS, "cv", "cindex",
                      internal["combined_oof_cindex"], n=internal["n"]),
        ce.metric_row("expr_clin_pfs_cox", POOL_DS, "cv", "delta_c_vs_clinical_transported",
                      internal["delta_c_pool_cv"], baseline="clinical_transported",
                      n=internal["n"]),
    ]
    ce.save_run("e004-pfs-tune", {"phase": "tune", "grid": rows, "chosen": best,
                                  "pool_n": int(len(lab_tr)), "pool_internal": internal,
                                  "stage2_coef": {k: float(v) for k, v in stage2.params_.items()},
                                  "stage2_p": {k: float(v) for k, v in stage2.summary["p"].items()}},
                metrics=rows_out)
    print("\nNext: --phase final --n-genes %d --l1-ratio %s" % (best["n_genes"], best["l1_ratio"]))
    return 0


def phase_final(args):
    import numpy as np
    import pandas as pd
    from lifelines import CoxPHFitter

    cindex, cindex_ci, delta_ci, random_effects = _helpers()
    lp, fit_pool_cox, oof_pool_cox, coxnet, Surv, SKF = _models()

    lab_tr, X_tr = load(POOL_DS, *EXPR_POOL)
    lab_va, X_va = load(VAL_DS, *EXPR_VAL)
    if args.dry_run:
        rng = np.random.default_rng(12345)
        lab_va["time"] = np.ceil(rng.exponential(600.0, len(lab_va)))
        lab_va["event"] = rng.binomial(1, 0.6, len(lab_va)).astype(int)
        print("DRY RUN: validation outcomes are synthetic; nothing registered or saved")

    Z_tr, Z_va, genes = prepare(X_tr, X_va, args.n_genes)
    y_tr = Surv.from_arrays(lab_tr["event"].to_numpy().astype(bool), lab_tr["time"].to_numpy())

    # Stage 1, refit at the frozen setting; the alpha still comes from pool CV.
    alphas, oof, scored = coxnet_oof(Z_tr, lab_tr, args.l1_ratio, coxnet, Surv, SKF, cindex)
    best = max(scored, key=lambda d: d["oof_cindex"])
    full = coxnet(alphas=alphas, l1_ratio=args.l1_ratio).fit(Z_tr.to_numpy(), y_tr)
    coef = pd.Series(full.coef_[:, alphas.index(best["alpha"])], index=Z_tr.columns)
    sig = coef[coef.abs() > 1e-8]
    print(f"stage 1: alpha={best['alpha']:.4f} l1={args.l1_ratio} genes kept={len(sig)}/{len(genes)}"
          f"  pool CV C={best['oof_cindex']:.3f}")
    if not len(sig):
        raise SystemExit("Coxnet kept no genes")

    def score(Z):
        return Z[coef.index].to_numpy() @ coef.to_numpy()

    mu, sd = float(score(Z_tr).mean()), float(score(Z_tr).std(ddof=0))
    oof_z = (oof[best["alpha"]] - oof[best["alpha"]].mean()) / oof[best["alpha"]].std(ddof=0)

    # Stage 2 and the baseline: same covariates, same strata, one differs only by the score.
    mask = lab_tr[CLIN].notna().all(axis=1)
    clin_feat = lab_tr.loc[mask, CLIN].astype(float)
    comb_feat = clin_feat.assign(expr_score=oof_z.loc[clin_feat.index].values)
    clin_cph = fit_pool_cox(clin_feat, lab_tr)
    comb_cph = fit_pool_cox(comb_feat, lab_tr)
    print(f"stage 2 on n={len(comb_feat)} events={int(lab_tr.loc[mask,'event'].sum())}")
    print(comb_cph.summary[["coef", "exp(coef)", "p"]].round(3).to_string())

    pool_sub = lab_tr.loc[clin_feat.index]
    internal = {
        "clinical_oof_cindex": stratified_cindex(pool_sub, oof_pool_cox(clin_feat, lab_tr), cindex),
        "combined_oof_cindex": stratified_cindex(pool_sub, oof_pool_cox(comb_feat, lab_tr), cindex),
        "n": int(len(pool_sub)), "events": int(pool_sub["event"].sum()),
    }
    print("pool internal (not evidence):", {k: round(v, 3) if isinstance(v, float) else v
                                            for k, v in internal.items()})

    cohorts = [c for c in RULE_COHORTS + REDUNDANT if (lab_va["cohort"] == c).any()]
    if not args.dry_run:
        ce.register_validation(CANDIDATE, cohorts, config={
            "endpoint": "pfs/pfi, native per-cohort definitions",
            "n_genes": args.n_genes, "l1_ratio": args.l1_ratio, "alpha": best["alpha"],
            "seed": SEED, "n_boot": N_BOOT, "clinical": CLIN, "strata": "cohort",
            "primary": "expr_clin_pfs_cox", "rule_cohorts": RULE_COHORTS,
            "rule": "cohorts_passing >= 2 AND pooled_ci_lo > 0",
        })

    rows, external, table = [], {}, []
    for cohort in cohorts:
        g = lab_va.loc[lab_va["cohort"] == cohort]
        sub = g.loc[g[CLIN].notna().all(axis=1)]
        if len(sub) < 20:
            ce.eprint(f"{cohort}: only {len(sub)} complete-case patients; skipped")
            continue
        feat = sub[CLIN].astype(float)
        base_risk = pd.Series(lp(clin_cph, feat), index=sub.index)
        comb_risk = pd.Series(lp(comb_cph, feat.assign(
            expr_score=(score(Z_va.loc[sub.index]) - mu) / sd)), index=sub.index)
        expr_only = pd.Series(score(Z_va.loc[sub.index]), index=sub.index)

        for name, risk in (("clinical_transported", base_risk),
                           ("expr_clin_pfs_cox", comb_risk),
                           ("expr_pfs_coxnet", expr_only)):
            c, lo, hi = cindex_ci(sub["time"], sub["event"], risk)
            rows.append(ce.metric_row(name, cohort, "external", "cindex", c, ci_lo=lo, ci_hi=hi,
                                      n=int(len(sub))))
            rec = external.setdefault(cohort, {"n": int(len(sub)),
                                               "events": int(sub["event"].sum())})
            rec[name] = {"cindex": c, "ci_lo": lo, "ci_hi": hi}
            if name != "clinical_transported":
                d, dlo, dhi, dse = delta_ci(sub["time"], sub["event"], risk, base_risk)
                rows.append(ce.metric_row(name, cohort, "external",
                                          "delta_c_vs_clinical_transported", d, ci_lo=dlo,
                                          ci_hi=dhi, baseline="clinical_transported"))
                rec[name].update({"delta": d, "delta_ci": [dlo, dhi], "delta_se": dse})
        table.append({"cohort": cohort, "n": rec["n"], "events": rec["events"],
                      "in_rule": cohort in RULE_COHORTS,
                      "clinical": rec["clinical_transported"]["cindex"],
                      "combined": rec["expr_clin_pfs_cox"]["cindex"],
                      "delta": rec["expr_clin_pfs_cox"].get("delta")})

    print("\nexternal validation")
    print(pd.DataFrame(table).to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # The pre-registered rule, computed from the rows above.
    ruled = [external[c] for c in RULE_COHORTS if c in external]
    pooled = random_effects([r["expr_clin_pfs_cox"].get("delta") for r in ruled],
                            [r["expr_clin_pfs_cox"].get("delta_se") for r in ruled])
    passing = sum(1 for r in ruled
                  if (r["expr_clin_pfs_cox"].get("delta") or -1) >= 0.03)
    indicator = 1 if (passing >= 2 and pooled and pooled["ci_lo"] > 0) else 0
    print(f"\ncohorts passing 0.03: {passing}/{len(ruled)}")
    if pooled:
        print(f"pooled dC {pooled['estimate']:+.3f} [{pooled['ci_lo']:+.3f}, {pooled['ci_hi']:+.3f}]"
              f"  I2={pooled['i2']:.2f}")
    print(f"e004_success_indicator = {indicator}")

    if pooled:
        rows.append(ce.metric_row("expr_clin_pfs_cox", VAL_DS, "external",
                                  "delta_c_vs_clinical_transported_pooled", pooled["estimate"],
                                  ci_lo=pooled["ci_lo"], ci_hi=pooled["ci_hi"], n=pooled["k"],
                                  baseline="clinical_transported"))
    rows.append(ce.metric_row("expr_clin_pfs_cox", VAL_DS, "external", "e004_success_indicator",
                              indicator, n=len(ruled)))
    rows += [ce.metric_row(m, POOL_DS, "cv", "cindex", internal[k], n=internal["n"])
             for m, k in (("clinical_transported", "clinical_oof_cindex"),
                          ("expr_clin_pfs_cox", "combined_oof_cindex"))]

    if args.dry_run:
        print(f"DRY RUN: {sum(r is not None for r in rows)} rows built, "
              f"problems={ce._check_metric_rows([r for r in rows if r])}; nothing saved")
        return 0
    out = ce.save_run("e004-pfs-first-pass", {
        "phase": "final", "endpoint": "pfs", "n_genes": args.n_genes,
        "l1_ratio": args.l1_ratio, "alpha": best["alpha"], "signature_size": int(len(sig)),
        "signature_top": {k: float(v) for k, v in sig.abs().nlargest(20).items()},
        "stage2_coef": {k: float(v) for k, v in comb_cph.params_.items()},
        "pool_internal": internal, "external": external, "pooled": pooled,
        "cohorts_passing": passing, "e004_success_indicator": indicator,
        "rule_cohorts": RULE_COHORTS, "redundant_scored": REDUNDANT,
    }, metrics=rows)
    print(out)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("tune", "final"), required=True)
    ap.add_argument("--gene-grid", type=int, nargs="+", default=[250, 500, 1000])
    ap.add_argument("--l1-grid", type=float, nargs="+", default=[1.0, 0.5])
    ap.add_argument("--n-genes", type=int, default=500)
    ap.add_argument("--l1-ratio", type=float, default=1.0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ce.require("pandas", "numpy", "scikit-learn", "lifelines", "scikit-survival")
    return phase_tune(args) if args.phase == "tune" else phase_final(args)


if __name__ == "__main__":
    sys.exit(main())
