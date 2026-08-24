"""Runtime-side helpers for working in a Google Colab kernel.

Imported *on the Colab VM*, after the bootstrap cell has put this repo on the
runtime's disk (see `.cursor/skills/colab-compute/SKILL.md`). It reuses the
same `common.cfg` config and the same `datasets/<topic>/<slug>/` layout as the
local scripts, so notebook code and local code address data identically.

The module is import-safe off-Colab: every helper degrades to the local
workspace, which makes it usable for dry runs before spending runtime minutes.

Typical notebook use:

    import colab_env as ce
    print(ce.summary())
    ce.require("torch", "scikit-learn")
    X, y, meta = ce.geo_xy("gse14764-ovarian-expression-series-matrix",
                           label="overall survival event")
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path

from common import WORKSPACE, cfg, eprint

# Colab preinstalls these under names that differ from their pip names.
_PIP_NAME = {
    "sklearn": "scikit-learn",
    "scikit-learn": "scikit-learn",
    "cv2": "opencv-python-headless",
    "yaml": "pyyaml",
}
_IMPORT_NAME = {"scikit-learn": "sklearn", "pyyaml": "yaml"}


# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------
def _has_module(name: str) -> bool:
    """find_spec() raises rather than returning None for a missing parent."""
    try:
        return find_spec(name) is not None
    except (ImportError, AttributeError, ValueError):
        return False


def in_colab() -> bool:
    return _has_module("google.colab")


def gpu_info() -> dict:
    """Accelerator facts, from nvidia-smi first and torch second.

    nvidia-smi is authoritative about what the VM was given; torch tells us
    whether the installed build can actually reach it. They disagree when the
    runtime has a GPU but torch was installed CPU-only, which is worth seeing.
    """
    info: dict = {"available": False, "name": None, "memory_mb": None,
                  "driver": None, "torch_cuda": None}

    smi = shutil.which("nvidia-smi")
    if smi:
        try:
            out = subprocess.run(
                [smi, "--query-gpu=name,memory.total,driver_version",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=30, check=False).stdout.strip()
            if out:
                name, mem, driver = (p.strip() for p in out.splitlines()[0].split(","))
                info.update(available=True, name=name, memory_mb=int(float(mem)),
                            driver=driver)
        except (OSError, ValueError, subprocess.SubprocessError):
            pass

    if _has_module("torch"):
        try:
            torch = import_module("torch")
            info["torch_cuda"] = bool(torch.cuda.is_available())
            info["torch_version"] = torch.__version__
            if info["torch_cuda"] and not info["available"]:
                info.update(available=True, name=torch.cuda.get_device_name(0))
        except Exception as exc:  # a broken torch install must not kill the cell
            info["torch_error"] = str(exc)

    return info


def report() -> dict:
    """Machine-readable snapshot of the runtime."""
    ram_gb = None
    try:
        ram_gb = round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1e9, 1)
    except (ValueError, OSError):
        pass

    ws = workspace()
    return {
        "colab": in_colab(),
        "python": sys.version.split()[0],
        "workspace": str(ws),
        "workspace_present": (ws / "agent" / "scripts").is_dir(),
        "cpu_count": os.cpu_count(),
        "ram_gb": ram_gb,
        "disk_free_gb": round(shutil.disk_usage(ws if ws.exists() else "/").free / 1e9, 1),
        "gpu": gpu_info(),
    }


def summary() -> str:
    """Same as report(), formatted for a human reading notebook output."""
    r = report()
    gpu = r["gpu"]
    if gpu["available"]:
        mem = f", {gpu['memory_mb'] / 1024:.0f} GB" if gpu.get("memory_mb") else ""
        accel = f"{gpu['name']}{mem}"
        if gpu["torch_cuda"] is False:
            accel += "  [WARNING: torch cannot see it — CPU-only build?]"
    elif r["colab"]:
        accel = "none (CPU only) — pick a GPU runtime in the kernel selector"
    else:
        accel = "none (CPU only)"

    lines = [
        f"{'Colab runtime' if r['colab'] else 'Local machine'} · Python {r['python']}",
        f"Accelerator : {accel}",
        f"CPU / RAM   : {r['cpu_count']} cores, {r['ram_gb']} GB",
        f"Disk free   : {r['disk_free_gb']} GB",
        f"Workspace   : {r['workspace']}"
        + ("" if r["workspace_present"] else "  [MISSING — run the bootstrap cell]"),
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
def workspace() -> Path:
    """Workspace root: the runtime copy on Colab, the checkout locally.

    `common.WORKSPACE` already resolves correctly in both places (it walks up
    from this file), so the config value is only a fallback for the odd case
    where this module is loaded from outside the tree.
    """
    if (WORKSPACE / "agent" / "scripts" / "colab_env.py").exists():
        return WORKSPACE
    return Path(cfg("colab.runtime_dir", "/content/research"))


def datasets_root() -> Path:
    p = Path(cfg("paths.datasets_dir", "datasets"))
    return p if p.is_absolute() else workspace() / p


def dataset_dir(slug: str, topic: str | None = None) -> Path:
    return datasets_root() / (topic or cfg("colab.default_topic", "")) / slug


def dataset_csv(slug: str, name: str, topic: str | None = None) -> Path:
    """Path to a converted CSV, e.g. dataset_csv(slug, 'expression.csv')."""
    return dataset_dir(slug, topic) / "csv" / name


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------
def require(*packages: str, quiet: bool = True) -> dict:
    """Install only the packages that are actually missing.

    Colab already ships torch, pandas, numpy and scikit-learn, so the common
    case is a no-op. Accepts import names or pip names interchangeably.
    """
    installed, already = [], []
    for pkg in packages:
        mod = _IMPORT_NAME.get(pkg, pkg).replace("-", "_")
        if _has_module(mod):
            already.append(pkg)
            continue
        target = _PIP_NAME.get(pkg, pkg)
        cmd = [sys.executable, "-m", "pip", "install", target]
        if quiet:
            cmd.insert(4, "-q")
        subprocess.run(cmd, check=True)
        installed.append(target)
    return {"installed": installed, "already_present": already}


def install_requirements(path: str | None = None) -> dict:
    req = workspace() / (path or cfg("colab.requirements", "agent/requirements-colab.txt"))
    if not req.exists():
        return {"skipped": f"{req} not found"}
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(req)],
                   check=True)
    return {"installed_from": str(req)}


# ---------------------------------------------------------------------------
# Data on demand
# ---------------------------------------------------------------------------
def ensure_dataset(slug: str, topic: str | None = None, *, csv_only: bool = True) -> Path:
    """Make a tracked dataset present on the runtime, fetching it if needed.

    The bootstrap clone is sparse and blobless, so `datasets/` starts empty.
    This widens the sparse-checkout to one dataset and lets git fetch just
    those blobs — tens of MB instead of the whole tree. Off-Colab (or in a
    normal full checkout) it simply validates that the folder exists.
    """
    target = dataset_dir(slug, topic)
    pattern = f"{Path(cfg('paths.datasets_dir', 'datasets'))}/" \
              f"{topic or cfg('colab.default_topic', '')}/{slug}"
    if csv_only:
        pattern += "/csv"

    ws = workspace()
    if not target.exists() and (ws / ".git").exists():
        subprocess.run(["git", "-C", str(ws), "sparse-checkout", "add", pattern],
                       check=True, capture_output=True, text=True)

    if not target.exists():
        raise FileNotFoundError(
            f"dataset not found: {target}\n"
            "If the repo is private, set the GitHub token secret (see the "
            "colab-compute skill). If it was never converted, run "
            "datasets_to_csv.py locally and push."
        )
    restore_packed()
    return target


def restore_packed() -> list[dict]:
    """Rebuild files that git tracks only as zips.

    Anything over GitHub's 100 MB blob limit is gitignored and committed as
    `<name>.zip` (or `.zip.partNN`) per the github-file-size rule, so a fresh
    clone has the archive but not the file itself. Large expression matrices
    land in that bucket, so a runtime checkout has to unpack before loading.
    """
    ws = workspace()
    if not (ws / ".research" / "github-pack.json").exists():
        return []  # nothing has ever been packed
    try:
        import github_pack
    except ImportError:
        eprint("packed files present but github_pack.py is not importable")
        return []

    results = github_pack.unpack_all().get("unpacked", [])
    for r in results:
        if r.get("status") == "unpacked":
            eprint(f"restored {r['path']} from its archive")
    return results


def load_geo(slug: str, topic: str | None = None, *, index_col: int = 0):
    """Load a converted GEO dataset as (expression, phenotype) DataFrames.

    `expression` is probes x samples (as written by datasets_to_csv.py);
    `phenotype` is indexed by `geo_accession` so it aligns with the expression
    column headers without any key munging.
    """
    require("pandas")
    pd = import_module("pandas")
    ensure_dataset(slug, topic)

    expr = pd.read_csv(dataset_csv(slug, "expression.csv", topic), index_col=index_col)
    pheno = pd.read_csv(dataset_csv(slug, "phenotype.csv", topic))
    if "geo_accession" in pheno.columns:
        pheno = pheno.set_index("geo_accession")
    return expr, pheno


def geo_xy(slug: str, label: str, topic: str | None = None, *,
           positive: str | None = None, dropna: bool = True):
    """Build a samples x probes feature matrix and an aligned label vector.

    Returns (X, y, meta). X is a DataFrame indexed by GSM accession; y is a
    Series of ints when `label` is already 0/1, otherwise a 0/1 indicator for
    `positive`. Samples missing a label are dropped unless dropna=False.
    """
    require("pandas")
    pd = import_module("pandas")
    expr, pheno = load_geo(slug, topic)

    if label not in pheno.columns:
        raise KeyError(f"{label!r} not in phenotype columns: {sorted(pheno.columns)}")

    X = expr.T                                   # samples x probes
    labels = pheno.loc[X.index.intersection(pheno.index), label]

    if positive is None:
        y = pd.to_numeric(labels, errors="coerce")
    else:
        y = labels.astype(str).str.strip().eq(positive).astype("float")

    if dropna:
        y = y.dropna()
    y = y.astype(int)
    X = X.loc[y.index]

    meta = {
        "dataset": slug,
        "label": label,
        "n_samples": int(len(y)),
        "n_features": int(X.shape[1]),
        "class_balance": {str(k): int(v) for k, v in y.value_counts().sort_index().items()},
        "dropped_samples": int(expr.shape[1] - len(y)),
    }
    return X, y, meta


# ---------------------------------------------------------------------------
# Getting results back off the runtime
# ---------------------------------------------------------------------------
def save_run(name: str, payload: dict, *, files: list[str] | None = None) -> Path:
    """Write a run record under .research/colab/runs/<utc>-<name>/.

    The runtime disk is wiped when the session ends, so anything worth keeping
    has to leave: commit and push from the runtime, or copy to a mounted
    Drive. Both are one-liners documented in the colab-compute skill.
    """
    from datetime import datetime, timezone
    from json import dumps
    from common import slugify

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = workspace() / ".research" / "colab" / "runs" / f"{stamp}-{slugify(name)}"
    out.mkdir(parents=True, exist_ok=True)

    record = {"name": name, "saved_at": stamp, "env": report(), "result": payload}
    (out / "run.json").write_text(dumps(record, indent=2, default=str), encoding="utf-8")

    for f in files or []:
        src = Path(f)
        if src.exists():
            shutil.copy2(src, out / src.name)
        else:
            eprint(f"save_run: skipping missing file {src}")
    return out


def mount_drive(path: str = "/content/drive"):
    """Mount Google Drive. Colab-only; raises a clear error elsewhere."""
    if not in_colab():
        raise RuntimeError("mount_drive() only works inside a Colab runtime")
    from google.colab import drive  # type: ignore[import-not-found]
    drive.mount(path)
    return Path(path) / cfg("colab.drive_dir", "MyDrive/research-colab")
