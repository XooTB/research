#!/usr/bin/env python3
"""Run this workspace on a Google Colab runtime through Google's `colab` CLI.

The local working tree is the source of truth. Code and datasets are uploaded
straight into a persistent Colab session — incrementally, so after the first
push only changed files travel — and run records come back automatically.
Nothing is committed, pushed, or cloned to make a run happen.

The loop (session name defaults to colab.session in .research/config.yaml):

    colab_sync.py start --dataset os-training-pool --dataset os-validation
    colab_sync.py run agent/experiments/colab_smoke.py      # edit, run, read, repeat
    colab_sync.py stop

`run` syncs changed files, executes the script in the session kernel as if it
were `python script.py args` from the workspace root, streams its output to
stderr, pulls new .research/colab/runs/ records, prints a JSON summary and
exits with the script's exit code. A `.ipynb` runs cell by cell; the executed
copy lands next to the input as <name>_output.ipynb and its records are
imported.

Long jobs (beyond colab.exec_timeout) run detached on the VM:

    colab_sync.py job <name> <script.py> [args...]
    colab_sync.py logs <name> [-n 40]    # tail + running/exit status; pulls records when done

Also: push [--dataset ...], pull, status. Every command takes -s NAME.

Provenance: before `run` / `job` executes, the synced code roots are
snapshotted into git without touching the branch (HEAD when they are clean,
otherwise a commit kept under refs/runs/<stamp>) and each pushed dataset is
fingerprinted (sha256, cached by size+mtime). The runtime receives this in
$RESEARCH_RUN_CONTEXT and colab_env.save_run() stores it in the record, so any
result can be traced to `git checkout <code_commit>` plus exact data hashes.
Validation-ledger entries registered on the runtime are merged into
.research/validation-ledger.jsonl on every pull.

Environment overrides, for testing against a fake CLI: COLAB_BIN,
COLAB_SYNC_RUNTIME_DIR, COLAB_SYNC_STAGING, COLAB_SYNC_NO_INSTALL=1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

from common import WORKSPACE, cfg, emit, eprint, slugify

MARK = "===COLAB-SYNC-RESULT==="
REMOTE = os.environ.get("COLAB_SYNC_RUNTIME_DIR") or cfg("colab.runtime_dir", "/content/research")
STAGING = os.environ.get("COLAB_SYNC_STAGING") or "/content/.colab-sync"
MANIFEST = f"{REMOTE}/.colab-sync.json"
RUNS_REL = ".research/colab/runs"
JOBS_REL = ".research/colab/jobs"
LEDGER_REL = ".research/validation-ledger.jsonl"
HASH_CACHE = WORKSPACE / ".research" / "colab" / "hash-cache.json"
SESSIONS_DIR = WORKSPACE / ".research" / "colab" / "sessions"
PACK_MANIFEST = WORKSPACE / ".research" / "github-pack.json"
SKIP_DIRS = {".git", ".venv", "__pycache__", ".ipynb_checkpoints", "node_modules"}
AUTH_HINT = ("The colab CLI could not authenticate. Ask the user to run "
             "`colab --auth=<colab.auth> sessions` in a terminal and finish the "
             "login (see the colab-compute skill). Do not retry in a loop.")


class ColabError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# colab CLI
# ---------------------------------------------------------------------------
def colab_cmd(*args: str) -> list[str]:
    exe = os.environ.get("COLAB_BIN") or shutil.which("colab")
    if not exe:
        raise ColabError("colab CLI not found. Install it: uv tool install google-colab-cli")
    return [exe, f"--auth={cfg('colab.auth', 'oauth2')}", *args]


def _tail(proc: subprocess.CompletedProcess, n: int = 2000) -> str:
    return ((proc.stderr or "") + (proc.stdout or "")).strip()[-n:]


def colab(*args: str, check: bool = True, timeout: float | None = None) -> subprocess.CompletedProcess:
    proc = subprocess.run(colab_cmd(*args), capture_output=True, text=True,
                          timeout=timeout, check=False)
    if check and proc.returncode != 0:
        raise ColabError(f"colab {' '.join(args)} failed ({proc.returncode}):\n{_tail(proc)}")
    return proc


def snippet(template: str, **values) -> str:
    """Fill @@NAME@@ placeholders with Python literals."""
    for key, value in values.items():
        template = template.replace(f"@@{key}@@", repr(value))
    return template


def remote_py(session: str, code: str, *, timeout: float = 600, echo: bool = False) -> dict:
    """Execute `code` in the session kernel; return the dict it assigns to `_result`.

    The code runs in a private namespace so helper names never leak into the
    kernel that experiment scripts share. With `echo`, remote output streams to
    stderr as it arrives.
    """
    wrapped = (
        "import json as _cs_json, traceback as _cs_tb\n"
        "_cs_ns = {}\n"
        "try:\n"
        f"    exec(compile({code!r}, '<colab_sync>', 'exec'), _cs_ns)\n"
        "    _cs_out = _cs_ns.get('_result', {})\n"
        "except BaseException:\n"
        "    _cs_out = {'error': _cs_tb.format_exc()}\n"
        f"print({MARK!r} + _cs_json.dumps(_cs_out, default=str), flush=True)\n"
    )
    proc = subprocess.Popen(colab_cmd("exec", "-s", session, "--timeout", str(timeout)),
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    assert proc.stdin and proc.stdout
    proc.stdin.write(wrapped)
    proc.stdin.close()

    result, tail = None, []
    for line in proc.stdout:
        if MARK in line:
            result = json.loads(line.split(MARK, 1)[1])
            continue
        tail = (tail + [line])[-60:]
        if echo:
            sys.stderr.write(line)
            sys.stderr.flush()
    proc.wait()

    if result is None:
        raise ColabError(
            f"no result from session {session!r} (colab exec exit {proc.returncode}). "
            "Is it running? `colab_sync.py start` recreates it.\n" + "".join(tail)[-2000:])
    if "error" in result:
        raise ColabError(f"remote step failed:\n{result['error']}")
    return result


def _session_exists(session: str) -> bool:
    out = colab("sessions").stdout
    return re.search(rf"(?<![\w-]){re.escape(session)}(?![\w-])", out) is not None


# ---------------------------------------------------------------------------
# Local inventory
# ---------------------------------------------------------------------------
def _pack_manifest() -> tuple[set[str], set[str]]:
    """(archive paths never to upload, packed originals) from github-pack.json."""
    try:
        items = json.loads(PACK_MANIFEST.read_text(encoding="utf-8"))["items"]
    except (OSError, ValueError, KeyError):
        return set(), set()
    archives = {p for i in items for p in [i["zip"], *(i.get("parts") or [])]}
    return archives, {i["original"] for i in items}


def dataset_rel(spec: str) -> str:
    """`slug`, `topic/slug`, or a sub-path like `slug/labels.csv` -> workspace-relative path."""
    base = Path(cfg("paths.datasets_dir", "datasets"))
    for cand in (base / cfg("colab.default_topic", "") / spec, base / spec):
        if (WORKSPACE / cand).exists():
            return cand.as_posix()
    raise ColabError(f"dataset not found locally: {spec}")


def _in_roots(rel: str, roots: list[str]) -> bool:
    return any(rel == r or rel.startswith(r.rstrip("/") + "/") for r in roots)


def inventory(roots: list[str]) -> dict[str, list[int]]:
    """{relative path: [size, mtime_ns]} for every file under the sync roots."""
    archives, originals = _pack_manifest()
    files: dict[str, list[int]] = {}
    for rel in roots:
        missing = [o for o in originals if _in_roots(o, [rel]) and not (WORKSPACE / o).exists()]
        if missing:
            raise ColabError(f"packed originals missing locally under {rel}: {missing}. "
                             "Run: .venv/bin/python agent/scripts/github_pack.py unpack")
        root = WORKSPACE / rel
        if root.is_file():
            candidates = [root]
        elif root.is_dir():
            candidates = []
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
                candidates += [Path(dirpath) / f for f in filenames]
        else:
            eprint(f"skipping missing sync path {rel}")
            continue
        for path in candidates:
            r = path.relative_to(WORKSPACE).as_posix()
            if r in archives or r.endswith("_output.ipynb"):
                continue
            st = path.stat()
            files[r] = [st.st_size, st.st_mtime_ns]
    return files


# ---------------------------------------------------------------------------
# Provenance (local side)
# ---------------------------------------------------------------------------
def _git(*args: str, env: dict | None = None) -> str:
    proc = subprocess.run(["git", "-C", str(WORKSPACE), *args], capture_output=True,
                          text=True, env=env, check=False)
    if proc.returncode != 0:
        raise ColabError(f"git {' '.join(args)} failed: {proc.stderr.strip()[-500:]}")
    return proc.stdout.strip()


def code_snapshot(code_roots: list[str], label: str) -> dict:
    """Commit the working-tree state of `code_roots` without touching the branch.

    Uses a throwaway index on top of HEAD, so nothing is staged and no branch
    moves. Clean roots resolve to HEAD itself; otherwise the commit is kept
    alive by refs/runs/<stamp>-<label> (local refs, not pushed by default),
    reusing an existing run ref when the tree is identical.
    """
    if not (WORKSPACE / ".git").exists() or not shutil.which("git"):
        return {"error": "not a git checkout"}
    try:
        head = _git("rev-parse", "HEAD")
        branch = _git("rev-parse", "--abbrev-ref", "HEAD")
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
            _git("read-tree", head, env=env)
            present = [r for r in code_roots if (WORKSPACE / r).exists()]
            if present:
                _git("add", "-A", "--", *present, env=env)
            tree = _git("write-tree", env=env)
        out = {"head": head, "branch": branch, "dirty": tree != _git("rev-parse", f"{head}^{{tree}}"),
               "code_commit": head, "code_ref": None}
        if not out["dirty"]:
            return out
        for line in _git("for-each-ref", "refs/runs", "--format=%(objectname) %(tree) %(refname)").splitlines():
            commit, ref_tree, ref = line.split(" ", 2)
            if ref_tree == tree:
                return {**out, "code_commit": commit, "code_ref": ref}
        commit = _git("commit-tree", tree, "-p", head, "-m", f"run snapshot: {label}")
        ref = f"refs/runs/{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{slugify(label, 40)}"
        _git("update-ref", ref, commit)
        return {**out, "code_commit": commit, "code_ref": ref}
    except ColabError as exc:
        return {"error": str(exc)}


def data_fingerprints(roots: list[str]) -> dict:
    """{root: {files, bytes, sha256}} over every synced file, hashes cached by size+mtime."""
    try:
        cache = json.loads(HASH_CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    files = inventory(roots)
    out = {}
    for root in roots:
        digest, total, n = hashlib.sha256(), 0, 0
        for rel in sorted(r for r in files if _in_roots(r, [root])):
            size, mtime = files[rel]
            hit = cache.get(rel)
            if not hit or hit[:2] != [size, mtime]:
                h = hashlib.sha256()
                with (WORKSPACE / rel).open("rb") as fh:
                    while block := fh.read(1 << 20):
                        h.update(block)
                cache[rel] = hit = [size, mtime, h.hexdigest()]
            digest.update(f"{rel}\t{hit[2]}\n".encode())
            total, n = total + size, n + 1
        out[root] = {"files": n, "bytes": total, "sha256": digest.hexdigest()[:16]}
    HASH_CACHE.parent.mkdir(parents=True, exist_ok=True)
    HASH_CACHE.write_text(json.dumps(cache), encoding="utf-8")
    return out


def run_context(command: str, session: str, script: str, args: list[str], roots: list[str]) -> dict:
    # The ledger is bookkeeping, not code or data: keeping it out stops every pull
    # from producing a new snapshot.
    code_roots = [r for r in cfg("colab.sync_paths", ["agent"]) if r in roots and r != LEDGER_REL]
    data_roots = [r for r in roots if r not in code_roots and r != LEDGER_REL]
    try:
        rel = Path(script).resolve().relative_to(WORKSPACE).as_posix()
    except ValueError:
        rel = script
    return {
        "via": "colab_sync",
        "command": command,
        "session": session,
        "script": rel,
        "args": list(args),
        "invoked_at": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "git": code_snapshot(code_roots, Path(rel).stem),
        "datasets": data_fingerprints(data_roots),
    }


def stamp_provenance(run_names: list[str], ctx: dict) -> list[str]:
    """Fill in provenance on pulled records that arrived without it."""
    stamped = []
    for name in run_names:
        path = WORKSPACE / RUNS_REL / name / "run.json"
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if (record.get("provenance") or {}).get("via") in (None, "unknown"):
            record["provenance"] = {**ctx, "stamped_locally": True}
            path.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
            stamped.append(name)
    return stamped


def merge_ledger(entries: list[dict]) -> int:
    from colab_env import upsert_ledger
    return upsert_ledger(entries, WORKSPACE / LEDGER_REL) if entries else 0


# ---------------------------------------------------------------------------
# Remote steps
# ---------------------------------------------------------------------------
READ_MANIFEST = """
import json, os
os.makedirs(@@STAGING@@, exist_ok=True)
try:
    with open(@@MANIFEST@@) as fh:
        _result = json.load(fh)
except (OSError, ValueError):
    _result = {"files": {}, "roots": []}
"""

EXTRACT = """
import glob, json, os, subprocess, sys, tarfile
bundle = @@BUNDLE@@
with open(bundle, "wb") as out:
    for part in sorted(glob.glob(bundle + ".part*")):
        with open(part, "rb") as fh:
            while block := fh.read(1 << 24):
                out.write(block)
        os.remove(part)
os.makedirs(@@REMOTE@@, exist_ok=True)
with tarfile.open(bundle) as tar:
    tar.extractall(@@REMOTE@@, filter="data")
os.remove(bundle)
try:
    with open(@@MANIFEST@@) as fh:
        manifest = json.load(fh)
except (OSError, ValueError):
    manifest = {"files": {}, "roots": []}
manifest["files"].update(@@FILES@@)
manifest["roots"] = @@ROOTS@@
with open(@@MANIFEST@@, "w") as fh:
    json.dump(manifest, fh)
scripts = os.path.join(@@REMOTE@@, "agent", "scripts")
if scripts not in sys.path:
    sys.path.insert(0, scripts)
installed = None
if @@INSTALL@@:
    proc = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", @@REQ@@],
                          capture_output=True, text=True)
    installed = {"ok": proc.returncode == 0, "tail": (proc.stdout + proc.stderr)[-1500:]}
_result = {"extracted": len(@@FILES@@), "installed": installed}
"""

ENV = """
import os, sys
scripts = os.path.join(@@REMOTE@@, "agent", "scripts")
if scripts not in sys.path:
    sys.path.insert(0, scripts)
import colab_env
_result = colab_env.report()
"""

RUN = """
import os, runpy, sys, traceback
ws = @@REMOTE@@
scripts = os.path.join(ws, "agent", "scripts")
if scripts not in sys.path:
    sys.path.insert(0, scripts)
# Re-import workspace modules fresh so code edits take effect (colab_env.memo survives).
for name, mod in list(sys.modules.items()):
    if (getattr(mod, "__file__", None) or "").startswith(ws + os.sep):
        del sys.modules[name]
os.chdir(ws)
saved_argv, code = sys.argv, 0
sys.argv = [@@PATH@@, *@@ARGS@@]
os.environ["RESEARCH_RUN_CONTEXT"] = @@CTX@@
try:
    runpy.run_path(@@PATH@@, run_name="__main__")
except SystemExit as exc:
    code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
except BaseException:
    traceback.print_exc()
    code = 1
finally:
    sys.argv = saved_argv
    os.environ.pop("RESEARCH_RUN_CONTEXT", None)
    sys.stdout.flush()
    sys.stderr.flush()
_result = {"exit_code": code}
"""

SET_CTX = """
import os
if @@CTX@@ is None:
    os.environ.pop("RESEARCH_RUN_CONTEXT", None)
else:
    os.environ["RESEARCH_RUN_CONTEXT"] = @@CTX@@
_result = {}
"""

PULL = """
import json, os, tarfile
root = os.path.join(@@REMOTE@@, @@RUNS@@)
have = set(@@HAVE@@)
new = sorted(d for d in (os.listdir(root) if os.path.isdir(root) else [])
             if d not in have and os.path.isfile(os.path.join(root, d, "run.json")))
archive = os.path.join(@@STAGING@@, "runs.tgz")
if new:
    os.makedirs(@@STAGING@@, exist_ok=True)
    with tarfile.open(archive, "w:gz") as tar:
        for d in new:
            tar.add(os.path.join(root, d), arcname=@@RUNS@@ + "/" + d)
ledger = []
ledger_file = os.path.join(@@REMOTE@@, @@LEDGER@@)
if os.path.isfile(ledger_file):
    with open(ledger_file) as fh:
        ledger = [json.loads(line) for line in fh if line.strip()]
_result = {"new": new, "archive": archive if new else None, "ledger": ledger}
"""

JOB = """
import os, shlex, subprocess, sys
ws = @@REMOTE@@
jobs = os.path.join(ws, @@JOBS@@)
os.makedirs(jobs, exist_ok=True)
base = os.path.join(jobs, @@NAME@@)
if os.path.exists(base + ".pid") and not os.path.exists(base + ".exit"):
    raise RuntimeError("job " + @@NAME@@ + " is still running; pick another name or wait")
for ext in (".exit", ".log"):
    if os.path.exists(base + ext):
        os.remove(base + ext)
cmd = "cd {ws} && PYTHONPATH={scripts} {py} -u {script} {args} > {log} 2>&1; echo $? > {status}".format(
    ws=shlex.quote(ws), scripts=shlex.quote(os.path.join(ws, "agent", "scripts")),
    py=shlex.quote(sys.executable), script=shlex.quote(@@PATH@@),
    args=" ".join(shlex.quote(a) for a in @@ARGS@@),
    log=shlex.quote(base + ".log"), status=shlex.quote(base + ".exit"))
proc = subprocess.Popen(["bash", "-c", cmd], start_new_session=True, stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        env=dict(os.environ, RESEARCH_RUN_CONTEXT=@@CTX@@))
with open(base + ".pid", "w") as fh:
    fh.write(str(proc.pid))
_result = {"pid": proc.pid, "log": base + ".log"}
"""

LOGS = """
import os
base = os.path.join(@@REMOTE@@, @@JOBS@@, @@NAME@@)
lines = []
if os.path.exists(base + ".log"):
    with open(base + ".log", errors="replace") as fh:
        lines = fh.readlines()[-@@N@@:]
exit_code = None
if os.path.exists(base + ".exit"):
    with open(base + ".exit") as fh:
        text = fh.read().strip()
    exit_code = int(text) if text.lstrip("-").isdigit() else 1
_result = {"found": os.path.exists(base + ".pid"), "exit_code": exit_code,
           "running": os.path.exists(base + ".pid") and exit_code is None, "tail": "".join(lines)}
"""


def push(session: str, datasets: list[str] | None = None) -> dict:
    """Upload whatever changed under the sync roots since the session last saw it."""
    remote = remote_py(session, snippet(READ_MANIFEST, STAGING=STAGING, MANIFEST=MANIFEST))
    roots = list(dict.fromkeys([*cfg("colab.sync_paths", ["agent"]), *remote.get("roots", []),
                                *(dataset_rel(d) for d in datasets or [])]))
    local = inventory(roots)
    known = remote.get("files", {})
    changed = sorted(r for r, sig in local.items() if known.get(r) != sig)
    if not changed:
        return {"changed": 0, "roots": roots}

    raw_mb = sum(local[r][0] for r in changed) / 1e6
    eprint(f"syncing {len(changed)} file(s), {raw_mb:.1f} MB before compression")
    chunk = int(cfg("colab.upload_chunk_mb", 40)) * 1024 * 1024
    bundle = f"{STAGING}/{time.strftime('%Y%m%dT%H%M%S')}.tgz"
    with tempfile.TemporaryDirectory() as tmp:
        local_bundle = Path(tmp) / "bundle.tgz"
        with tarfile.open(local_bundle, "w:gz", compresslevel=1) as tar:
            for r in changed:
                tar.add(WORKSPACE / r, arcname=r, recursive=False)
        parts = []
        with local_bundle.open("rb") as fh:
            while block := fh.read(chunk):
                part = Path(tmp) / f"part{len(parts):03d}"
                part.write_bytes(block)
                parts.append(part)
        local_bundle.unlink()
        for i, part in enumerate(parts, 1):
            eprint(f"  upload {i}/{len(parts)} ({part.stat().st_size / 1e6:.1f} MB)")
            colab("upload", "-s", session, str(part), f"{bundle}.{part.name}", timeout=1800)

    req = cfg("colab.requirements", "agent/requirements-colab.txt")
    install = req in changed and not os.environ.get("COLAB_SYNC_NO_INSTALL")
    res = remote_py(session, snippet(
        EXTRACT, BUNDLE=bundle, REMOTE=REMOTE, MANIFEST=MANIFEST,
        FILES={r: local[r] for r in changed}, ROOTS=roots, INSTALL=install,
        REQ=f"{REMOTE}/{req}"), timeout=1800)
    if res.get("installed") and not res["installed"]["ok"]:
        eprint(f"! requirements install failed:\n{res['installed']['tail']}")
    return {"changed": len(changed), "mb_raw": round(raw_mb, 1), "parts": len(parts),
            "installed": res.get("installed"), "roots": roots}


def pull(session: str) -> list[str]:
    """Copy run records the local runs/ folder doesn't have yet."""
    runs_local = WORKSPACE / RUNS_REL
    have = sorted(p.name for p in runs_local.iterdir()) if runs_local.is_dir() else []
    res = remote_py(session, snippet(PULL, REMOTE=REMOTE, RUNS=RUNS_REL, HAVE=have,
                                     STAGING=STAGING, LEDGER=LEDGER_REL))
    merge_ledger(res.get("ledger") or [])
    if not res["new"]:
        return []
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "runs.tgz"
        colab("download", "-s", session, res["archive"], str(archive), timeout=1800)
        with tarfile.open(archive) as tar:
            members = [m for m in tar.getmembers() if m.name.startswith(RUNS_REL + "/")]
            tar.extractall(WORKSPACE, members=members, filter="data")
    for name in res["new"]:  # entries saved with a run id, in case the ledger file lagged
        try:
            record = json.loads((WORKSPACE / RUNS_REL / name / "run.json").read_text(encoding="utf-8"))
            merge_ledger(record.get("validation") or [])
        except (OSError, ValueError):
            pass
    return res["new"]


def _remote_script(script: str, roots: list[str]) -> str:
    path = Path(script).resolve()
    try:
        rel = path.relative_to(WORKSPACE).as_posix()
    except ValueError:
        raise ColabError(f"{script} is outside the workspace") from None
    if not _in_roots(rel, roots):
        raise ColabError(f"{rel} is not under colab.sync_paths {roots}")
    return f"{REMOTE}/{rel}"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_start(session: str, datasets: list[str], gpu: str) -> None:
    inventory([dataset_rel(d) for d in datasets])  # fail before renting a VM
    try:
        existing = _session_exists(session)
    except ColabError as exc:
        raise ColabError(f"{exc}\n\n{AUTH_HINT}") from None

    created, gpu_granted = False, None
    if not existing:
        proc = colab("new", "-s", session, *(["--gpu", gpu] if gpu else []),
                     check=False, timeout=900)
        if proc.returncode != 0 and gpu:
            eprint(f"! {gpu} not granted, falling back to CPU:\n{_tail(proc, 600)}")
            colab("new", "-s", session, timeout=900)
            gpu_granted = False
        elif proc.returncode != 0:
            raise ColabError(f"colab new failed:\n{_tail(proc)}")
        else:
            gpu_granted = bool(gpu)
        created = True

    sync = push(session, datasets)
    env = remote_py(session, snippet(ENV, REMOTE=REMOTE))
    if gpu_granted is None:  # reused session: report what it actually has
        gpu_granted = bool((env.get("gpu") or {}).get("available"))
    emit({"session": session, "created": created, "gpu_requested": gpu or None,
          "gpu_granted": gpu_granted, "sync": sync, "env": env})


def cmd_run(session: str, script: str, args: list[str], timeout: float) -> int:
    sync = push(session)
    ctx = run_context("run", session, script, args, sync["roots"])
    if "error" in ctx["git"]:
        eprint(f"! code snapshot failed, provenance incomplete: {ctx['git']['error']}")
    ctx_json = json.dumps(ctx)
    if script.endswith(".ipynb"):
        nb = Path(script).resolve()
        remote_py(session, snippet(SET_CTX, CTX=ctx_json))
        proc = subprocess.run(colab_cmd("exec", "-s", session, "--timeout", str(timeout),
                                        "-f", str(nb)),
                              stdout=sys.stderr, stderr=sys.stderr, check=False)
        executed = next((p for p in (nb.with_name(f"{nb.stem}_output.ipynb"),
                                     Path.cwd() / f"{nb.stem}_output.ipynb") if p.exists()), None)
        imported = None
        if executed:
            from colab_runs import import_notebook
            imported = import_notebook(executed)
        remote_py(session, snippet(SET_CTX, CTX=None))
        new_runs = pull(session)
        names = new_runs + [Path(i["dir"]).name for i in (imported or {}).get("imported", [])]
        emit({"notebook": str(nb), "exit_code": proc.returncode, "sync": sync,
              "code_commit": ctx["git"].get("code_commit"),
              "executed_copy": str(executed) if executed else None,
              "imported": imported, "new_runs": new_runs,
              "provenance_stamped_locally": stamp_provenance(names, ctx)})
        return proc.returncode

    remote_path = _remote_script(script, sync["roots"])
    res = remote_py(session, snippet(RUN, REMOTE=REMOTE, PATH=remote_path, ARGS=list(args),
                                     CTX=ctx_json), timeout=timeout, echo=True)
    new_runs = pull(session)
    emit({"script": remote_path, "exit_code": res["exit_code"], "sync": sync,
          "code_commit": ctx["git"].get("code_commit"), "new_runs": new_runs,
          "provenance_stamped_locally": stamp_provenance(new_runs, ctx)})
    return res["exit_code"]


def cmd_job(session: str, name: str, script: str, args: list[str]) -> None:
    sync = push(session)
    remote_path = _remote_script(script, sync["roots"])
    ctx = run_context("job", session, script, args, sync["roots"])
    res = remote_py(session, snippet(JOB, REMOTE=REMOTE, JOBS=JOBS_REL, NAME=name,
                                     PATH=remote_path, ARGS=list(args), CTX=json.dumps(ctx)))
    emit({"job": name, "script": remote_path, "sync": sync, **res,
          "code_commit": ctx["git"].get("code_commit"),
          "next": f"colab_sync.py logs {name}"})


def cmd_logs(session: str, name: str, n: int) -> None:
    res = remote_py(session, snippet(LOGS, REMOTE=REMOTE, JOBS=JOBS_REL, NAME=name, N=n))
    if not res["found"]:
        raise ColabError(f"no job named {name!r} on session {session!r}")
    res["new_runs"] = pull(session) if res["exit_code"] is not None else []
    emit({"job": name, **res})


def cmd_stop(session: str) -> None:
    out: dict = {"session": session}
    try:
        out["new_runs"] = pull(session)
    except ColabError as exc:
        out["pull_error"] = str(exc)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = SESSIONS_DIR / f"{time.strftime('%Y%m%dT%H%M%S')}-{session}.ipynb"
    log = colab("log", "-s", session, "-o", str(log_path), check=False)
    out["session_log"] = str(log_path) if log.returncode == 0 and log_path.exists() else None
    colab("stop", "-s", session)
    out["stopped"] = True
    emit(out)


def cmd_status(session: str) -> None:
    st = colab("status", "-s", session, check=False)
    out = {"session": session, "status": (st.stdout or st.stderr).strip()}
    try:
        manifest = remote_py(session, snippet(READ_MANIFEST, STAGING=STAGING, MANIFEST=MANIFEST))
        out.update(synced_roots=manifest.get("roots"), synced_files=len(manifest.get("files", {})))
    except ColabError as exc:
        out["error"] = str(exc)
    emit(out)


def main() -> None:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-s", "--session", default=cfg("colab.session", "research"))

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("start", parents=[common], help="create/reuse a session and sync")
    p.add_argument("--dataset", action="append", default=[])
    p.add_argument("--gpu", default=cfg("colab.gpu", ""), help="T4, L4, ... (default colab.gpu)")
    p.add_argument("--cpu", action="store_true", help="do not request an accelerator")

    p = sub.add_parser("push", parents=[common], help="upload changed files")
    p.add_argument("--dataset", action="append", default=[])

    p = sub.add_parser("run", parents=[common], help="push, run a script/notebook, pull records")
    p.add_argument("--timeout", type=float, default=float(cfg("colab.exec_timeout", 3600)))
    p.add_argument("script")
    p.add_argument("args", nargs=argparse.REMAINDER)

    p = sub.add_parser("job", parents=[common], help="push, start a detached script")
    p.add_argument("name")
    p.add_argument("script")
    p.add_argument("args", nargs=argparse.REMAINDER)

    p = sub.add_parser("logs", parents=[common], help="tail a detached job")
    p.add_argument("name")
    p.add_argument("-n", type=int, default=40)

    sub.add_parser("pull", parents=[common], help="copy new run records back")
    sub.add_parser("status", parents=[common], help="session status and sync state")
    sub.add_parser("stop", parents=[common], help="pull, save session log, release the VM")

    args = ap.parse_args()
    code = 0
    try:
        if args.cmd == "start":
            cmd_start(args.session, args.dataset, "" if args.cpu else args.gpu)
        elif args.cmd == "push":
            emit({"session": args.session, **push(args.session, args.dataset)})
        elif args.cmd == "run":
            code = cmd_run(args.session, args.script, args.args, args.timeout)
        elif args.cmd == "job":
            cmd_job(args.session, args.name, args.script, args.args)
        elif args.cmd == "logs":
            cmd_logs(args.session, args.name, args.n)
        elif args.cmd == "pull":
            emit({"session": args.session, "new_runs": pull(args.session)})
        elif args.cmd == "status":
            cmd_status(args.session)
        elif args.cmd == "stop":
            cmd_stop(args.session)
    except (ColabError, subprocess.TimeoutExpired) as exc:
        emit({"error": str(exc)})
        code = 2
    raise SystemExit(code)


if __name__ == "__main__":
    main()
