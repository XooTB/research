#!/usr/bin/env python3
"""Smoke test for a Colab session: runtime report, datasets present, a run record.

    colab_sync.py start --dataset os-training-pool
    colab_sync.py run agent/experiments/colab_smoke.py --dataset os-training-pool

Exits 1 if a requested dataset is missing on the runtime.
"""
import argparse

import colab_env as ce

ap = argparse.ArgumentParser()
ap.add_argument("--dataset", action="append", default=[])
args = ap.parse_args()

print(ce.summary())
present = {slug: ce.dataset_dir(slug).exists() for slug in args.dataset}
print("datasets present:", present)

run_dir = ce.save_run("colab-smoke", {
    "gpu": ce.gpu_info(),
    "ram_gb": ce.report()["ram_gb"],
    "datasets_present": present,
})
print(run_dir)
raise SystemExit(0 if all(present.values()) else 1)
