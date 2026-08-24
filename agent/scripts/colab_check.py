#!/usr/bin/env python3
"""Pre-flight check for the Colab workflow. Run locally before a session.

A Colab runtime gets this workspace by cloning the *remote*, so anything that
exists only in the local working tree is invisible there. This catches that
class of failure — unpushed commits, an untracked dataset, a config pointing
at the wrong remote — before it turns into a confusing FileNotFoundError
halfway through a notebook.

Usage:
    colab_check.py                          # config + sync state
    colab_check.py --dataset <slug>         # also check one dataset is on the remote
    colab_check.py --topic <t> --dataset <slug>
"""
from __future__ import annotations

import argparse
import subprocess

from common import WORKSPACE, cfg, emit


def git(*args: str) -> tuple[int, str]:
    proc = subprocess.run(["git", "-C", str(WORKSPACE), *args],
                          capture_output=True, text=True, check=False)
    return proc.returncode, (proc.stdout or proc.stderr).strip()


def check_config() -> tuple[list[dict], str | None]:
    checks: list[dict] = []
    repo_url = cfg("colab.repo_url", "")
    branch = cfg("colab.branch", "main")

    _, remotes = git("remote", "get-url", "origin")
    # Compare hosts+paths, not full URLs: origin is usually SSH, the runtime
    # clones over HTTPS with a token.
    normalized = remotes.replace("git@", "").replace(":", "/", 1) \
                        .replace("https///", "").replace("https://", "")
    ok = bool(repo_url) and normalized.rstrip("/") == repo_url.rstrip("/")
    checks.append({
        "check": "config.colab.repo_url matches git origin",
        "ok": ok,
        "detail": f"config={repo_url or '(unset)'} origin={normalized or '(none)'}",
        "fix": None if ok else "point colab.repo_url in .research/config.yaml at origin",
    })

    for key in ("mode", "runtime_dir", "sparse_paths", "requirements"):
        val = cfg(f"colab.{key}")
        checks.append({"check": f"config.colab.{key} set", "ok": val not in (None, "", []),
                       "detail": str(val),
                       "fix": None if val else f"add colab.{key} to .research/config.yaml"})
    return checks, branch


def check_sync(branch: str) -> list[dict]:
    checks: list[dict] = []

    _, dirty = git("status", "--porcelain")
    changed = [l for l in dirty.splitlines() if l.strip()]
    checks.append({
        "check": "working tree clean",
        "ok": not changed,
        "detail": f"{len(changed)} changed path(s)" + (f": {changed[:5]}" if changed else ""),
        "fix": None if not changed else "commit and push, or the runtime won't see these",
    })

    code, _ = git("rev-parse", "--verify", f"refs/remotes/origin/{branch}")
    if code != 0:
        checks.append({"check": f"origin/{branch} known locally", "ok": False,
                       "detail": "no remote-tracking ref",
                       "fix": f"git fetch origin {branch}"})
        return checks

    _, ahead = git("rev-list", "--count", f"origin/{branch}..HEAD")
    n_ahead = int(ahead) if ahead.isdigit() else -1
    checks.append({
        "check": f"HEAD pushed to origin/{branch}",
        "ok": n_ahead == 0,
        "detail": f"{n_ahead} local commit(s) not on the remote",
        "fix": None if n_ahead == 0 else f"git push origin {branch}",
    })
    return checks


def check_dataset(slug: str, topic: str, branch: str) -> list[dict]:
    rel = f"{cfg('paths.datasets_dir', 'datasets')}/{topic}/{slug}"
    checks: list[dict] = []

    local = (WORKSPACE / rel).is_dir()
    checks.append({"check": f"{rel} exists locally", "ok": local, "detail": str(local),
                   "fix": None if local else "check the topic/slug spelling"})

    _, tracked = git("ls-files", f"{rel}/csv")
    csv_files = [l for l in tracked.splitlines() if l.strip()]
    checks.append({
        "check": f"{rel}/csv tracked in git",
        "ok": bool(csv_files),
        "detail": f"{len(csv_files)} file(s)",
        "fix": None if csv_files else
               "run datasets_to_csv.py, then git add the csv/ folder",
    })

    code, listing = git("ls-tree", "-r", "--name-only", f"origin/{branch}", f"{rel}/csv")
    on_remote = [l for l in listing.splitlines() if l.strip()] if code == 0 else []
    checks.append({
        "check": f"{rel}/csv present on origin/{branch}",
        "ok": bool(on_remote),
        "detail": f"{len(on_remote)} file(s)",
        "fix": None if on_remote else
               "push the csv/ folder — the runtime clones the remote, not your disk",
    })

    # Files over GitHub's blob limit have to be zipped before they can be
    # pushed at all, which is what makes them reachable from a runtime. An
    # oversize file that is already gitignored is fine — that is what a packed
    # working copy looks like, with the committed zip sitting beside it.
    try:
        import github_pack
    except ImportError:
        return checks

    pushable = [p.name for p in github_pack.iter_large_files(WORKSPACE / rel)
                if git("check-ignore", "-q", str(p))[0] != 0]
    checks.append({
        "check": f"no pushable file in {rel} over GitHub's 100 MB limit",
        "ok": not pushable,
        "detail": f"{len(pushable)} file(s)" + (f": {pushable}" if pushable else ""),
        "fix": None if not pushable else
               f"python agent/scripts/github_pack.py pack --path {rel}",
    })
    return checks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", help="dataset slug to verify is reachable from Colab")
    ap.add_argument("--topic", default=cfg("colab.default_topic", ""))
    args = ap.parse_args()

    checks, branch = check_config()
    checks += check_sync(branch)
    if args.dataset:
        checks += check_dataset(args.dataset, args.topic, branch)

    failures = [c for c in checks if not c["ok"]]
    emit({
        "ready": not failures,
        "branch": branch,
        "runtime_dir": cfg("colab.runtime_dir"),
        "checks": checks,
        "next_steps": [c["fix"] for c in failures if c.get("fix")],
    })
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
