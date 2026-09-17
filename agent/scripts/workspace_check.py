#!/usr/bin/env python3
"""Workspace health check: library DB, disk, packed files, OS tables, runs, ledger, agent config.

The workspace has several descriptions of itself — the SQLite library, the
files on disk, github_pack's manifest, the compiled OS tables and the docs
that quote their numbers, Colab run records and the validation ledger — and
nothing else keeps them in step. This reconciles them. Stdlib only, so it runs
in the local .venv.

Usage:
    workspace_check.py                    # everything (OS table verifies take ~15 s)
    workspace_check.py --quick            # skip the expression-matrix verifies
    workspace_check.py --only library,runs,research
    workspace_check.py --fix              # apply safe fixes, then report what is left

Sections: library, pack, tables, docs, runs, research, agent, git.

--fix only does mechanical, reversible repairs: make DB paths workspace-relative,
remove empty paper folders, unpack missing packed originals, pack files over
the GitHub limit, merge validation entries from run records into the ledger,
link runs to the experiment their provenance names, and regenerate
research/NOW.md. Everything else is reported for a human or the agent to decide.

Prints JSON to stdout, one line per finding to stderr; exits 1 when any error
remains.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import db
from common import WORKSPACE, cfg, emit, eprint, ws_path, ws_rel

SECTIONS = ("library", "pack", "tables", "docs", "runs", "research", "agent", "git")
TOPIC_OS = "ovarian-cancer-prognosis-ml"
POOL = WORKSPACE / "datasets" / TOPIC_OS / "os-training-pool"
VALIDATION = WORKSPACE / "datasets" / TOPIC_OS / "os-validation"
FOCUS_DOC = WORKSPACE / "research" / "os-hgsoc" / "workstream.md"
LEDGER = WORKSPACE / ".research" / "validation-ledger.jsonl"
# Records saved before provenance existed are reported as info, not warnings.
PROVENANCE_SINCE = "20260917T000000Z"
NEAR_LIMIT_BYTES = 90 * 1024 * 1024


class Report:
    def __init__(self) -> None:
        self.findings: list[dict] = []
        self.fixed: list[str] = []

    def add(self, section: str, level: str, code: str, message: str, **extra) -> None:
        self.findings.append({"section": section, "level": level, "code": code,
                              "message": message, **extra})

    def error(self, section, code, message, **extra):
        self.add(section, "error", code, message, **extra)

    def warn(self, section, code, message, **extra):
        self.add(section, "warning", code, message, **extra)

    def info(self, section, code, message, **extra):
        self.add(section, "info", code, message, **extra)


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(WORKSPACE), *args], capture_output=True,
                          text=True, check=False)


# ---------------------------------------------------------------------------
# library: SQLite DB vs disk
# ---------------------------------------------------------------------------
def check_library(rep: Report, fix: bool) -> None:
    S = "library"
    conn = db.connect()

    if fix:
        n = 0
        for table, col in (("datasets", "local_path"), ("papers", "pdf_path")):
            for r in conn.execute(f"SELECT id, {col} FROM {table} WHERE {col} LIKE '/%'").fetchall():
                rel = ws_rel(r[col])
                if not rel.startswith("/"):
                    conn.execute(f"UPDATE {table} SET {col}=? WHERE id=?", (rel, r["id"]))
                    n += 1
        conn.commit()
        if n:
            rep.fixed.append(f"made {n} DB paths workspace-relative")

    datasets = conn.execute("SELECT * FROM datasets").fetchall()
    for r in datasets:
        label = f"dataset {r['id']} ({r['name'] or 'no name'})"
        if not (r["name"] or "").strip():
            rep.error(S, "dataset-blank", f"{label}: row has no name", id=r["id"])
        path = r["local_path"]
        if path and path.startswith("/"):
            rep.error(S, "abs-path", f"{label}: absolute local_path {path}", id=r["id"], fixable=True)
        if path and not (WORKSPACE / path).exists():
            rep.error(S, "dataset-missing", f"{label}: local_path not on disk: {path}", id=r["id"])
        if not path and r["status"] in ("downloaded", "verified"):
            rep.warn(S, "status-no-path", f"{label}: status {r['status']} but no local_path", id=r["id"])
        if bool(r["verified"]) != (r["status"] == "verified"):
            rep.warn(S, "verified-mismatch",
                     f"{label}: verified={r['verified']} but status={r['status']}", id=r["id"])
        if path and (WORKSPACE / path / "REPORT.md").is_file() and r["status"] != "verified":
            rep.warn(S, "report-not-verified",
                     f"{label}: REPORT.md exists but status is {r['status']}", id=r["id"])

    dupes = conn.execute(
        "SELECT source, source_id, COUNT(*) n FROM datasets WHERE source_id IS NOT NULL "
        "GROUP BY source, source_id HAVING n > 1").fetchall()
    for d in dupes:
        rep.error(S, "dataset-dup", f"{d['n']} dataset rows share {d['source']}:{d['source_id']}")
    for r in conn.execute("SELECT id, name FROM datasets WHERE source_id IS NULL").fetchall():
        rep.warn(S, "no-source-id",
                 f"dataset {r['id']} ({r['name']}) has no source_id; upserts cannot match it by source",
                 id=r["id"])

    known = {ws_rel(r["local_path"]) for r in datasets if r["local_path"]}
    ds_root = ws_path("paths.datasets_dir", "datasets")
    if ds_root.is_dir():
        for topic in sorted(p for p in ds_root.iterdir() if p.is_dir()):
            for slug in sorted(p for p in topic.iterdir() if p.is_dir()):
                rel = ws_rel(slug)
                if rel not in known:
                    empty = not any(slug.iterdir())
                    rep.error(S, "dataset-unregistered",
                              f"{rel} is on disk but not in the library DB"
                              + (" (empty folder)" if empty else ""), path=rel)

    papers = conn.execute("SELECT id, title, pdf_path FROM papers").fetchall()
    with_pdf = set()
    for r in papers:
        path = r["pdf_path"]
        if not path:
            continue
        with_pdf.add(path)
        if path.startswith("/"):
            rep.error(S, "abs-path", f"paper {r['id']}: absolute pdf_path {path}", id=r["id"], fixable=True)
        if not (WORKSPACE / path).is_file():
            rep.error(S, "pdf-missing", f"paper {r['id']}: pdf_path not on disk: {path}", id=r["id"])

    papers_root = ws_path("paths.papers_dir", "papers")
    if papers_root.is_dir():
        for pdf in sorted(papers_root.rglob("*.pdf")):
            if ws_rel(pdf) not in with_pdf:
                rep.warn(S, "pdf-unregistered", f"{ws_rel(pdf)} is not referenced by any paper row")
        empties = [d for d in papers_root.glob("*/*") if d.is_dir() and not any(d.iterdir())]
        if empties and fix:
            for d in empties:
                d.rmdir()
            rep.fixed.append(f"removed {len(empties)} empty paper folders")
        elif empties:
            rep.warn(S, "empty-paper-dirs",
                     f"{len(empties)} empty paper folders (failed PDF downloads)", fixable=True,
                     paths=[ws_rel(d) for d in empties[:10]])

    dangling = conn.execute(
        "SELECT pd.id FROM paper_datasets pd LEFT JOIN papers p ON p.id = pd.paper_id "
        "LEFT JOIN datasets d ON d.id = pd.dataset_id WHERE p.id IS NULL OR d.id IS NULL").fetchall()
    if dangling:
        rep.error(S, "dangling-link", f"{len(dangling)} paper_datasets rows point at missing rows",
                  ids=[r["id"] for r in dangling])

    bib = ws_path("paths.bib_path", ".research/references.bib")
    n_keys = conn.execute("SELECT COUNT(*) FROM papers WHERE bibkey IS NOT NULL").fetchone()[0]
    n_bib = len(re.findall(r"^@\w+\{", bib.read_text(encoding="utf-8"), re.M)) if bib.is_file() else 0
    if n_bib != n_keys:
        rep.warn(S, "bib-stale", f"references.bib has {n_bib} entries, DB has {n_keys} papers with bibkeys "
                                 "(papers_add.py re-exports it)")
    conn.close()


# ---------------------------------------------------------------------------
# pack: github_pack manifest, >100 MB files, .gitignore block
# ---------------------------------------------------------------------------
def check_pack(rep: Report, fix: bool) -> None:
    S = "pack"
    import github_pack

    if fix:
        restored = [r for r in github_pack.unpack_all()["unpacked"] if r["status"] == "unpacked"]
        if restored:
            rep.fixed.append(f"unpacked {len(restored)} missing originals")
        packed = github_pack.scan_and_pack().get("packed") or []
        if packed:
            rep.fixed.append(f"packed {len(packed)} files over the GitHub limit")

    st = github_pack.status()
    for item in st["items"]:
        if not item["unpacked_on_disk"]:
            rep.error(S, "unpacked-missing",
                      f"{item['original']} exists only as an archive; scripts and colab_sync need it "
                      "unpacked", path=item["original"], fixable=True)
        archive_ok = item["parts_on_disk"] == item["parts"] if item["parts"] else item["zip_on_disk"]
        if not archive_ok:
            rep.error(S, "archive-missing", f"{item['original']}: its zip/parts are missing, so git "
                                            "does not carry this file", path=item["original"])
    for path in st["still_over_limit"]:
        rep.error(S, "over-limit", f"{path} is over 100 MB and not packed", path=path, fixable=True)

    gitignore = (WORKSPACE / ".gitignore").read_text(encoding="utf-8")
    block = gitignore.split(github_pack.BEGIN, 1)[-1].split(github_pack.END, 1)[0]
    ignored = {line.strip() for line in block.splitlines()}
    for item in st["items"]:
        if item["original"] not in ignored:
            rep.error(S, "not-ignored", f"{item['original']} is packed but not in the .gitignore block; "
                                        "the >100 MB original could be committed", path=item["original"])

    tracked = _git("ls-files", "-z")
    if tracked.returncode == 0:
        for rel in filter(None, tracked.stdout.split("\0")):
            p = WORKSPACE / rel
            try:
                size = p.stat().st_size
            except OSError:
                continue
            if NEAR_LIMIT_BYTES < size <= github_pack.THRESHOLD and not github_pack.is_pack_artifact(p):
                rep.warn(S, "near-limit", f"{rel} is {size / 2**20:.1f} MiB, close to the 100 MiB pack "
                                          "threshold; the next rebuild may push it over", path=rel)


# ---------------------------------------------------------------------------
# tables: the OS workstream's own verify commands
# ---------------------------------------------------------------------------
def check_tables(rep: Report, quick: bool) -> None:
    S = "tables"
    scripts = WORKSPACE / "agent" / "scripts"
    checks = [("os_pool_labels.py", POOL), ("os_validation_labels.py", VALIDATION),
              ("os_clinical.py", POOL)]
    if not quick:
        checks += [("os_pool_expression.py", POOL), ("os_validation_expression.py", VALIDATION)]
    for script, needs in checks:
        if not needs.is_dir():
            rep.info(S, "table-absent", f"{script} skipped: {ws_rel(needs)} not on disk")
            continue
        proc = subprocess.run([sys.executable, str(scripts / script), "verify"],
                              capture_output=True, text=True, cwd=WORKSPACE, check=False)
        if proc.returncode != 0:
            tail = (proc.stdout + proc.stderr).strip().splitlines()[-8:]
            rep.error(S, "verify-failed", f"{script} verify exited {proc.returncode}", tail=tail)
        else:
            rep.info(S, "verify-ok", f"{script} verify passed")
    if quick:
        rep.info(S, "quick", "expression-matrix verifies skipped (--quick)")


# ---------------------------------------------------------------------------
# docs: headline numbers quoted in the focus doc vs the compiled tables
# ---------------------------------------------------------------------------
def _label_counts(labels: Path) -> tuple[int, int] | None:
    import csv
    if not labels.is_file():
        return None
    with labels.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return len(rows), sum(1 for r in rows if str(r.get("os_event", "")).strip() == "1")


def check_docs(rep: Report) -> None:
    S = "docs"
    if not FOCUS_DOC.is_file():
        rep.info(S, "no-focus-doc", f"{ws_rel(FOCUS_DOC)} not found")
        return
    text = FOCUS_DOC.read_text(encoding="utf-8")
    for name, root, symbols_file in (("training pool", POOL, "expression_pool.symbols.txt"),
                                     ("validation set", VALIDATION, "expression_validation.symbols.txt")):
        counts = _label_counts(root / "labels.csv")
        if counts is None:
            continue
        n, d = counts
        if not re.search(rf"\b{n}\s*(patients\s*)?/\s*{d}\b", text):
            rep.warn(S, "stale-count", f"{ws_rel(FOCUS_DOC)} never quotes the {name} as {n} / {d} "
                                       f"(labels.csv has {n} patients, {d} deaths)")
        sym = root / symbols_file
        if sym.is_file():
            k = sum(1 for line in sym.read_text(encoding="utf-8").splitlines() if line.strip())
            if f"{k:,}" not in text and str(k) not in text:
                rep.warn(S, "stale-symbols", f"{ws_rel(FOCUS_DOC)} never quotes the {name} symbol "
                                             f"count {k:,}")


# ---------------------------------------------------------------------------
# runs: run records, provenance, validation ledger
# ---------------------------------------------------------------------------
def check_runs(rep: Report, fix: bool) -> None:
    S = "runs"
    from colab_env import read_ledger, upsert_ledger

    runs_root = WORKSPACE / ".research" / "colab" / "runs"
    records = {}
    for d in sorted(runs_root.iterdir()) if runs_root.is_dir() else []:
        if not d.is_dir():
            continue
        try:
            records[d.name] = json.loads((d / "run.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            rep.error(S, "record-unreadable", f"{d.name}: run.json unreadable ({exc})")

    legacy = 0
    for name, rec in records.items():
        prov = rec.get("provenance") or {}
        if prov.get("via") in (None, "unknown"):
            if str(rec.get("saved_at", "")) < PROVENANCE_SINCE:
                legacy += 1
            else:
                rep.warn(S, "no-provenance", f"{name}: no provenance; the result cannot be tied to code "
                                             "and data (run it through colab_sync.py)")
            continue
        git = prov.get("git") or {}
        if git.get("error"):
            rep.warn(S, "snapshot-error", f"{name}: code snapshot failed: {git['error']}")
        commit = git.get("code_commit")
        if commit and _git("cat-file", "-e", f"{commit}^{{commit}}").returncode != 0:
            rep.warn(S, "snapshot-missing", f"{name}: code commit {commit[:12]} is not in this clone "
                                            "(refs/runs/* are local unless pushed)")
    if legacy:
        rep.info(S, "legacy-records", f"{legacy} records predate provenance tracking")

    if not LEDGER.is_file():
        rep.warn(S, "no-ledger", f"{ws_rel(LEDGER)} missing; colab_env.register_validation creates it")
        ledger = []
    else:
        ledger = read_ledger(LEDGER)

    from_records = [e for rec in records.values() for e in rec.get("validation") or []]
    ids = {e.get("id") for e in ledger}
    missing = [e for e in from_records if e.get("id") not in ids]
    if missing and fix:
        upsert_ledger(missing, LEDGER)
        rep.fixed.append(f"merged {len(missing)} validation entries from run records into the ledger")
        ledger = read_ledger(LEDGER)
    elif missing:
        rep.error(S, "ledger-behind", f"{len(missing)} validation scorings in run records are not in "
                                      "the ledger", fixable=True)

    for e in ledger:
        if not e.get("run"):
            rep.warn(S, "ledger-unsaved", f"candidate {e.get('candidate')!r} was registered for validation "
                                          f"at {e.get('registered_at')} but no run record was saved")
        elif e["run"] not in records:
            rep.warn(S, "ledger-orphan", f"ledger entry for {e.get('candidate')!r} points at missing run "
                                         f"{e['run']}")
        if e.get("rescore_of") and not e.get("reason"):
            rep.error(S, "rescore-no-reason", f"candidate {e.get('candidate')!r} re-scored on validation "
                                              "without a recorded reason")
    by_candidate: dict[str, int] = {}
    for e in ledger:
        by_candidate[e.get("candidate")] = by_candidate.get(e.get("candidate"), 0) + 1
    if ledger:
        rep.info(S, "ledger", f"{len(ledger)} validation scorings across {len(by_candidate)} candidates",
                 rescored={c: n for c, n in by_candidate.items() if n > 1})


# ---------------------------------------------------------------------------
# research: the tracker under research/ (research.py check)
# ---------------------------------------------------------------------------
def check_research(rep: Report, fix: bool) -> None:
    import research

    res = research.check(fix=fix)
    rep.fixed.extend(res["fixed"])
    for prob in res["problems"]:
        rep.add("research", prob["level"], prob["code"], f"{prob['ref']}: {prob['message']}")


# ---------------------------------------------------------------------------
# agent: shared Cursor / Claude Code config, colab sync paths
# ---------------------------------------------------------------------------
def check_agent(rep: Report) -> None:
    S = "agent"
    cursor = WORKSPACE / ".cursor"
    links = [(WORKSPACE / ".claude" / "skills", cursor / "skills"),
             (WORKSPACE / ".mcp.json", cursor / "mcp.json")]
    rules = sorted((cursor / "rules").glob("*")) if (cursor / "rules").is_dir() else []
    for rule in rules:
        if rule.suffix != ".md":
            rep.error(S, "rule-not-md", f"{ws_rel(rule)}: Claude Code only loads .md rules")
        links.append((WORKSPACE / ".claude" / "rules" / rule.name, rule))
    for link, target in links:
        if not link.is_symlink():
            state = "is a copy" if link.exists() else "is missing"
            rep.error(S, "not-symlink", f"{ws_rel(link)} {state}; it must symlink to {ws_rel(target)}")
        elif link.resolve() != target.resolve():
            rep.error(S, "wrong-symlink", f"{ws_rel(link)} points at {link.resolve()}, not {ws_rel(target)}")
    claude_rules = WORKSPACE / ".claude" / "rules"
    for extra in sorted(claude_rules.glob("*")) if claude_rules.is_dir() else []:
        if not (cursor / "rules" / extra.name).exists():
            rep.warn(S, "orphan-rule", f"{ws_rel(extra)} has no .cursor/rules original")

    for rel in cfg("colab.sync_paths", []) or []:
        if not (WORKSPACE / rel).exists():
            rep.warn(S, "sync-path-missing", f"colab.sync_paths entry {rel} does not exist")


# ---------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------
def check_git(rep: Report) -> None:
    S = "git"
    if _git("rev-parse", "--git-dir").returncode != 0:
        rep.info(S, "no-git", "not a git checkout")
        return
    dirty = [line for line in _git("status", "--porcelain").stdout.splitlines() if line.strip()]
    if dirty:
        rep.info(S, "uncommitted", f"{len(dirty)} uncommitted changes")
    ahead = _git("rev-list", "--count", "@{upstream}..HEAD")
    if ahead.returncode == 0 and ahead.stdout.strip() not in ("", "0"):
        rep.warn(S, "unpushed", f"{ahead.stdout.strip()} local commits not pushed")
    refs = [line for line in _git("for-each-ref", "refs/runs").stdout.splitlines() if line.strip()]
    if refs:
        rep.info(S, "run-snapshots", f"{len(refs)} run code snapshots under refs/runs/ (local only; "
                                     "git push origin 'refs/runs/*' to share them)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", help=f"comma-separated sections: {','.join(SECTIONS)}")
    ap.add_argument("--quick", action="store_true", help="skip the expression-matrix verifies")
    ap.add_argument("--fix", action="store_true", help="apply safe mechanical fixes first")
    args = ap.parse_args()

    only = [s.strip() for s in args.only.split(",")] if args.only else list(SECTIONS)
    unknown = [s for s in only if s not in SECTIONS]
    if unknown:
        ap.error(f"unknown section(s) {unknown}; choose from {SECTIONS}")

    rep = Report()
    runners = {
        "library": lambda: check_library(rep, args.fix),
        "pack": lambda: check_pack(rep, args.fix),
        "tables": lambda: check_tables(rep, args.quick),
        "docs": lambda: check_docs(rep),
        "runs": lambda: check_runs(rep, args.fix),
        "research": lambda: check_research(rep, args.fix),
        "agent": lambda: check_agent(rep),
        "git": lambda: check_git(rep),
    }
    for section in SECTIONS:
        if section in only:
            try:
                runners[section]()
            except Exception as exc:  # noqa: BLE001 — one broken section must not hide the rest
                rep.error(section, "check-crashed", f"{type(exc).__name__}: {exc}")

    counts = {lvl: sum(1 for f in rep.findings if f["level"] == lvl)
              for lvl in ("error", "warning", "info")}
    marks = {"error": "✗", "warning": "!", "info": "·"}
    for f in rep.findings:
        eprint(f"{marks[f['level']]} [{f['section']}] {f['message']}")
    for msg in rep.fixed:
        eprint(f"✓ fixed: {msg}")
    eprint(f"{counts['error']} errors, {counts['warning']} warnings")
    emit({"ok": counts["error"] == 0, "counts": counts, "fixed": rep.fixed, "findings": rep.findings})
    raise SystemExit(1 if counts["error"] else 0)


if __name__ == "__main__":
    main()
