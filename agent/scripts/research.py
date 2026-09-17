#!/usr/bin/env python3
"""Research tracker: workstreams, experiments, tasks, findings, decisions, handoffs.

Source of truth is plain text under research/ (git-tracked). Every query
rebuilds an in-memory SQLite index from those files plus the metric rows in
.research/colab/runs/*/run.json, so the index can never drift and nothing
binary is committed. Agents query instead of reading files; outputs are small
and capped.

    research/NOW.md                       generated overview (research.py status)
    research/<ws>/workstream.md           goal, success rule, milestones   (+++ TOML +++ body)
    research/<ws>/experiments/E###-*.md   one approach / hypothesis        (+++ TOML +++ body)
    research/<ws>/tasks/T###-*.md         non-experiment work (acquisition, write-up)
    research/<ws>/findings.md             append-only  ## F### · date · title
    research/<ws>/decisions.md            append-only  ## D### · date · title
    research/<ws>/journal.md              append-only session handoffs

Read:   status | next | list | show | find | refs | results | verdict | sql | check
Write:  new | set | criterion | log | link-run   (never hand-edit NOW.md, verdicts or runs lists)

Verdicts are computed, never judged: an experiment's success rule (its own
[criterion] table, or the workstream's) is applied to the latest metric row
per (model, cohort) from its linked runs. The rule's hash is stored when the
first run is linked; changing the rule afterwards is a check error.

Stdlib only. Prints JSON to stdout, progress to stderr.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import tomllib
from datetime import datetime
from pathlib import Path

from common import WORKSPACE, eprint

ROOT = WORKSPACE / "research"
NOW_PATH = ROOT / "NOW.md"
RUNS_DIR = WORKSPACE / ".research" / "colab" / "runs"

EXPERIMENT_STATUSES = ("planned", "running", "done", "abandoned")
CLOSED = ("done", "abandoned")
WORKSTREAM_STATUSES = ("active", "paused", "done", "dropped")
SPLITS = ("train", "cv", "external")
OPS = {">=": lambda a, b: a >= b, ">": lambda a, b: a > b,
       "<=": lambda a, b: a <= b, "<": lambda a, b: a < b}
SETTABLE = {"title", "status", "priority", "depends_on", "summary", "hypothesis", "outcome",
            "tags", "validation_candidate"}
SUMMARY_MAX, OUTCOME_MAX = 200, 300
STALE_RUNNING_DAYS = 14
# Runs saved from this date on must be linked to an experiment (earlier ones are history).
TRACKER_SINCE = "20260917T000000Z"
DEFAULT_ROWS = 30


class TrackerError(RuntimeError):
    pass


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def rel(path: Path) -> str:
    return path.relative_to(WORKSPACE).as_posix()


# ---------------------------------------------------------------------------
# Files: +++ TOML +++ front matter
# ---------------------------------------------------------------------------
def split_doc(text: str) -> tuple[str, str]:
    if not text.startswith("+++\n"):
        raise TrackerError("missing +++ TOML front matter")
    end = text.find("\n+++\n", 3)
    if end < 0:
        raise TrackerError("unterminated +++ front matter")
    return text[4:end + 1], text[end + 5:]


def toml_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(toml_value(v) for v in value) + "]"
    return json.dumps(str(value), ensure_ascii=False)


def write_fields(path: Path, updates: dict) -> None:
    """Set top-level scalar/array keys in place, keeping every other line (readable diffs)."""
    text = path.read_text(encoding="utf-8")
    fm, body = split_doc(text)
    lines = fm.splitlines()
    table_at = next((i for i, ln in enumerate(lines) if ln.lstrip().startswith("[")), len(lines))
    for key, value in updates.items():
        line = f"{key} = {toml_value(value)}"
        hit = next((i for i in range(table_at) if re.match(rf"{re.escape(key)}\s*=", lines[i])), None)
        if hit is None:
            lines.insert(table_at, line)
            table_at += 1
        else:
            lines[hit] = line
    new_fm = "\n".join(lines) + "\n"
    tomllib.loads(new_fm)  # never write a file we can't read back
    path.write_text(f"+++\n{new_fm}+++\n{body}", encoding="utf-8")


ENTRY_HEAD = re.compile(r"^## ([FD]\d{3}) · (\d{4}-\d{2}-\d{2}) · (.+)$", re.M)


def parse_entries(path: Path) -> list[dict]:
    """Append-only findings/decisions: '## F001 · 2026-08-25 · title', then 'key: a, b' lines, then prose."""
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    heads = list(ENTRY_HEAD.finditer(text))
    out = []
    for i, m in enumerate(heads):
        chunk = text[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)].strip("\n")
        meta, body_lines = {}, []
        for line in chunk.splitlines():
            km = re.match(r"^(refs|tags|supersedes):\s*(.*)$", line)
            if km and not body_lines:
                meta[km.group(1)] = [v.strip() for v in km.group(2).split(",") if v.strip()]
            else:
                body_lines.append(line)
        out.append({"id": m.group(1), "date": m.group(2), "title": m.group(3).strip(),
                    "refs": meta.get("refs", []), "tags": meta.get("tags", []),
                    "supersedes": meta.get("supersedes", []), "body": "\n".join(body_lines).strip()})
    return out


JOURNAL_HEAD = re.compile(r"^## (\d{4}-\d{2}-\d{2})(?: (\d{2}:\d{2}))?(?: · (.+))?$", re.M)


def parse_journal(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    heads = list(JOURNAL_HEAD.finditer(text))
    return [{"date": m.group(1), "time": m.group(2), "label": m.group(3),
             "body": text[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)].strip()}
            for i, m in enumerate(heads)]


def load_run(name: str) -> dict | None:
    try:
        return json.loads((RUNS_DIR / name / "run.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def metric_row_problems(row) -> list[str]:
    if not isinstance(row, dict):
        return ["row is not an object"]
    probs = [f"missing {k}" for k in ("model", "cohort", "split", "metric", "value") if k not in row]
    if "value" in row and (isinstance(row["value"], bool) or not isinstance(row["value"], (int, float))):
        probs.append("value is not a number")
    if row.get("split") is not None and row["split"] not in SPLITS:
        probs.append(f"split {row['split']!r} not in {SPLITS}")
    for k in ("model", "cohort", "metric"):
        v = row.get(k)
        if isinstance(v, str) and v != v.lower():
            probs.append(f"{k} {v!r} must be lowercase")
    return probs


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE item(id TEXT, kind TEXT, ws TEXT, title TEXT, status TEXT, priority INT, summary TEXT,
                  outcome TEXT, verdict TEXT, created TEXT, updated TEXT, path TEXT, superseded_by TEXT,
                  meta TEXT);
CREATE TABLE edge(src TEXT, rel TEXT, dst TEXT);
CREATE TABLE metric(run TEXT, experiment TEXT, model TEXT, cohort TEXT, split TEXT, metric TEXT,
                    value REAL, ci_lo REAL, ci_hi REAL, baseline TEXT, n INT);
CREATE TABLE problem(level TEXT, code TEXT, ref TEXT, message TEXT);
CREATE VIRTUAL TABLE fts USING fts5(id UNINDEXED, kind UNINDEXED, text);
"""


class Index:
    def __init__(self) -> None:
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.workstreams: dict[str, dict] = {}
        self.workstream_bodies: dict[str, str] = {}
        self.items: dict[str, dict] = {}
        self.journals: dict[str, list[dict]] = {}
        self._build()

    # -- helpers --------------------------------------------------------------
    def problem(self, level: str, code: str, ref: str, message: str) -> None:
        self.db.execute("INSERT INTO problem VALUES (?,?,?,?)", (level, code, ref, message))

    def q(self, sql: str, *params) -> list[sqlite3.Row]:
        return self.db.execute(sql, params).fetchall()

    def _add_item(self, rec: dict) -> None:
        if rec["id"] in self.items:
            self.problem("error", "duplicate-id", rec["id"],
                         f"{rec['id']} defined in {rec['path']} and {self.items[rec['id']]['path']}")
            return
        self.items[rec["id"]] = rec
        self.db.execute("INSERT INTO item VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            rec["id"], rec["kind"], rec["ws"], rec.get("title"), rec.get("status"), rec.get("priority"),
            rec.get("summary"), rec.get("outcome"), rec.get("verdict"), rec.get("created"),
            rec.get("updated"), rec["path"], None, json.dumps(rec.get("meta", {}), default=str)))
        for relname, key in (("depends_on", "depends_on"), ("run", "runs"), ("tag", "tags"),
                             ("ref", "refs"), ("supersedes", "supersedes")):
            for dst in rec.get(key) or []:
                self.db.execute("INSERT INTO edge VALUES (?,?,?)", (rec["id"], relname, str(dst)))
        text = " ".join(str(x) for x in (rec.get("title"), rec.get("summary"), rec.get("hypothesis"),
                                         rec.get("outcome"), " ".join(rec.get("tags") or []),
                                         " ".join(rec.get("refs") or []), rec.get("body")) if x)
        self.db.execute("INSERT INTO fts VALUES (?,?,?)", (rec["id"], rec["kind"], text))

    # -- build ------------------------------------------------------------------
    def _build(self) -> None:
        if not ROOT.is_dir():
            return
        for ws_dir in sorted(p for p in ROOT.iterdir() if p.is_dir()):
            self._build_workstream(ws_dir)
        for rec in self.items.values():
            if rec["kind"] in ("experiment", "task"):
                for dep in rec.get("depends_on") or []:
                    if dep not in self.items:
                        self.problem("error", "unknown-dependency", rec["id"], f"{rec['id']} depends on unknown {dep}")
            for ref in rec.get("refs") or []:
                self._check_ref(rec["id"], ref)
            for old in rec.get("supersedes") or []:
                if old in self.items:
                    self.db.execute("UPDATE item SET superseded_by=? WHERE id=?", (rec["id"], old))
                else:
                    self.problem("error", "unknown-ref", rec["id"], f"{rec['id']} supersedes unknown {old}")
        for ws, meta in self.workstreams.items():
            for ms in meta.get("milestones", []):
                for it in ms.get("items", []):
                    if it not in self.items:
                        self.problem("error", "unknown-ref", ws, f"milestone {ms.get('id')} lists unknown {it}")
        self._check_cycles()

    def _check_ref(self, src: str, ref: str) -> None:
        if re.fullmatch(r"[EFDT]\d{3}", ref):
            if ref not in self.items:
                self.problem("error", "unknown-ref", src, f"{src} refers to unknown {ref}")
        elif ref.startswith("run:"):
            if not (RUNS_DIR / ref[4:] / "run.json").is_file():
                self.problem("error", "unknown-ref", src, f"{src} refers to missing run {ref[4:]}")
        elif "/" in ref and not (WORKSPACE / ref.split("#")[0]).exists():
            self.problem("error", "unknown-ref", src, f"{src} refers to missing path {ref}")

    def _build_workstream(self, ws_dir: Path) -> None:
        ws = ws_dir.name
        ws_file = ws_dir / "workstream.md"
        try:
            fm, body = split_doc(ws_file.read_text(encoding="utf-8"))
            meta = tomllib.loads(fm)
        except (OSError, TrackerError, tomllib.TOMLDecodeError) as exc:
            self.problem("error", "parse", rel(ws_file), str(exc))
            return
        if meta.get("status") not in WORKSTREAM_STATUSES:
            self.problem("error", "bad-field", ws, f"workstream status must be one of {WORKSTREAM_STATUSES}")
        self.workstreams[ws] = meta
        self.workstream_bodies[ws] = body
        crit = meta.get("criterion")
        if crit is not None:
            for p in criterion_problems(crit):
                self.problem("error", "bad-criterion", ws, p)
        self.db.execute("INSERT INTO item VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            ws, "workstream", ws, meta.get("title"), meta.get("status"), None, meta.get("summary"),
            None, None, None, meta.get("updated"), rel(ws_file), None, json.dumps(meta, default=str)))
        self.db.execute("INSERT INTO fts VALUES (?,?,?)", (ws, "workstream", " ".join(
            str(x) for x in (meta.get("title"), meta.get("summary"), meta.get("question"), body) if x)))

        for kind, folder, prefix in (("experiment", "experiments", "E"), ("task", "tasks", "T")):
            for f in sorted((ws_dir / folder).glob("*.md")):
                self._build_work_item(ws, kind, prefix, f)
        for kind, fname in (("finding", "findings.md"), ("decision", "decisions.md")):
            path = ws_dir / fname
            for e in parse_entries(path):
                if not e["id"].startswith(kind[0].upper()):
                    self.problem("error", "bad-id", e["id"], f"{e['id']} in {fname} has the wrong prefix")
                self._add_item({**e, "kind": kind, "ws": ws, "status": "active", "summary": e["title"],
                                "created": e["date"], "updated": e["date"], "path": rel(path)})
        self.journals[ws] = parse_journal(ws_dir / "journal.md")
        for n, j in enumerate(self.journals[ws], 1):  # handoffs are searchable, not items
            self.db.execute("INSERT INTO fts VALUES (?,?,?)", (
                f"{ws}/journal#{n}", "journal", " ".join(x for x in (j["date"], j["label"], j["body"]) if x)))

    def _build_work_item(self, ws: str, kind: str, prefix: str, f: Path) -> None:
        try:
            fm, body = split_doc(f.read_text(encoding="utf-8"))
            meta = tomllib.loads(fm)
        except (OSError, TrackerError, tomllib.TOMLDecodeError) as exc:
            self.problem("error", "parse", rel(f), str(exc))
            return
        iid = str(meta.get("id", ""))
        if not re.fullmatch(rf"{prefix}\d{{3}}", iid):
            self.problem("error", "bad-id", rel(f), f"id {iid!r} must look like {prefix}001")
        elif not f.name.startswith(iid + "-"):
            self.problem("error", "bad-id", iid, f"{rel(f)} should be named {iid}-<slug>.md")
        for key in ("title", "status", "priority", "summary"):
            if key not in meta:
                self.problem("error", "missing-field", iid or rel(f), f"missing {key}")
        status = meta.get("status")
        if status not in EXPERIMENT_STATUSES:
            self.problem("error", "bad-field", iid, f"status {status!r} not in {EXPERIMENT_STATUSES}")
        if not isinstance(meta.get("priority", 0), int):
            self.problem("error", "bad-field", iid, "priority must be an integer (1 = highest)")
        if len(meta.get("summary", "")) > SUMMARY_MAX:
            self.problem("warning", "long-summary", iid, f"summary over {SUMMARY_MAX} chars")
        if len(meta.get("outcome", "") or "") > OUTCOME_MAX:
            self.problem("warning", "long-outcome", iid, f"outcome over {OUTCOME_MAX} chars")
        if status in CLOSED and not meta.get("outcome"):
            self.problem("error", "no-outcome", iid, f"{iid} is {status} but has no outcome")
        if kind == "task" and ("criterion" in meta or "runs" in meta):
            self.problem("error", "bad-field", iid, "tasks have no criterion or runs; make it an experiment")
        crit = meta.get("criterion")
        if isinstance(crit, dict):
            for p in criterion_problems(crit):
                self.problem("error", "bad-criterion", iid, p)
        elif crit is not None and crit != "none":
            self.problem("error", "bad-criterion", iid, 'criterion must be a [criterion] table or "none"')

        rec = {**meta, "id": iid, "kind": kind, "ws": ws, "path": rel(f), "body": body, "meta": meta}
        self._add_item(rec)
        for run in meta.get("runs") or []:
            record = load_run(run)
            if record is None:
                self.problem("error", "missing-run", iid, f"{iid} lists run {run} but its run.json is missing")
                continue
            for n, row in enumerate(record.get("metrics") or []):
                probs = metric_row_problems(row)
                if probs:
                    self.problem("error", "bad-metric-row", run, f"metrics[{n}]: {'; '.join(probs)}")
                    continue
                self.db.execute("INSERT INTO metric VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
                    run, iid, row["model"], row["cohort"], row["split"], row["metric"], float(row["value"]),
                    row.get("ci_lo"), row.get("ci_hi"), row.get("baseline"), row.get("n")))

    def _check_cycles(self) -> None:
        graph = {i: r.get("depends_on") or [] for i, r in self.items.items() if r["kind"] in ("experiment", "task")}
        state: dict[str, int] = {}

        def visit(node: str, path: list[str]) -> None:
            state[node] = 1
            for dep in graph.get(node, []):
                if state.get(dep) == 1:
                    self.problem("error", "dependency-cycle", node, " -> ".join(path + [node, dep]))
                elif dep in graph and not state.get(dep):
                    visit(dep, path + [node])
            state[node] = 2

        for node in graph:
            if not state.get(node):
                visit(node, [])

    # -- derived ------------------------------------------------------------------
    def criterion_for(self, iid: str) -> dict | None:
        rec = self.items[iid]
        crit = rec.get("criterion")
        if crit == "none":
            return None
        if isinstance(crit, dict):
            return crit
        return (self.workstreams.get(rec["ws"]) or {}).get("criterion")

    def verdict(self, iid: str) -> dict:
        rec = self.items.get(iid)
        if not rec or rec["kind"] != "experiment":
            raise TrackerError(f"{iid} is not an experiment")
        crit = self.criterion_for(iid)
        out = {"experiment": iid, "criterion": crit, "criterion_hash": criterion_hash(crit)}
        if crit is None:
            return {**out, "verdict": "n/a",
                    "basis": "no numeric success rule (criterion = \"none\"): judged by its outcome line, not a rule",
                    "outcome": rec.get("outcome")}
        rows = self.q("SELECT run, model, cohort, value FROM metric WHERE experiment=? AND metric=? AND split=? "
                      "ORDER BY run", iid, crit["metric"], crit["split"])
        latest: dict[tuple, sqlite3.Row] = {}
        for r in rows:  # runs sort by UTC stamp: keep the latest value per (model, cohort)
            if crit.get("models") and r["model"] not in crit["models"]:
                continue
            if crit.get("cohorts") and r["cohort"] not in crit["cohorts"]:
                continue
            latest[(r["model"], r["cohort"])] = r
        if not latest:
            return {**out, "verdict": "no-data", "basis": f"no {crit['metric']}/{crit['split']} rows"}
        passing: dict[str, list[str]] = {}
        scored: dict[str, int] = {}
        for (model, cohort), r in latest.items():
            scored[model] = scored.get(model, 0) + 1
            if OPS[crit["op"]](r["value"], crit["threshold"]):
                passing.setdefault(model, []).append(cohort)
        need = int(crit.get("min_cohorts", 1))
        best = max(passing.items(), key=lambda kv: len(kv[1]), default=(None, []))
        verdict = "supported" if len(best[1]) >= need else "not-supported"
        basis = "; ".join(f"{m}: {len(passing.get(m, []))}/{scored[m]}"
                          + (f" ({','.join(sorted(passing[m]))})" if passing.get(m) else "")
                          for m in sorted(scored))
        return {**out, "verdict": verdict, "basis": f"need {need} cohorts {crit['op']} {crit['threshold']}: {basis}"}


def criterion_problems(crit: dict) -> list[str]:
    probs = [f"criterion missing {k}" for k in ("metric", "split", "op", "threshold") if k not in crit]
    if crit.get("split") not in SPLITS:
        probs.append(f"criterion split must be one of {SPLITS}")
    if crit.get("op") not in OPS:
        probs.append(f"criterion op must be one of {tuple(OPS)}")
    if "threshold" in crit and not isinstance(crit["threshold"], (int, float)):
        probs.append("criterion threshold must be a number")
    return probs


def criterion_hash(crit: dict | None) -> str:
    return hashlib.sha256(json.dumps(crit or "none", sort_keys=True).encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def out(payload: dict) -> None:
    """Compact JSON, one row per line: cheap for agents, still scannable by humans."""
    lists = {k: v for k, v in payload.items() if isinstance(v, list) and v and isinstance(v[0], dict)}
    scalars = {k: v for k, v in payload.items() if k not in lists}
    parts = [json.dumps(scalars, ensure_ascii=False, separators=(",", ":"), default=str)[:-1]]
    for k, rows in lists.items():
        inner = ",\n ".join(json.dumps(r, ensure_ascii=False, separators=(",", ":"), default=str) for r in rows)
        parts.append(f'"{k}":[\n {inner}\n]')
    text = parts[0] + ("," if len(parts) > 1 and len(parts[0]) > 1 else "") + ",".join(parts[1:]) + "}"
    print(text)


def capped(rows: list, limit: int) -> dict:
    data = [dict(r) for r in rows]
    res = {"count": len(data)}
    if len(data) > limit:
        res["truncated"] = f"showing {limit} of {len(data)}; narrow the query or pass --limit"
    res["rows"] = data[:limit]
    return res


def ready_and_blocked(ix: Index, ws: str | None) -> tuple[list[dict], list[dict], list[dict]]:
    ready, blocked, running = [], [], []
    for it in sorted(ix.items.values(), key=lambda r: (r.get("priority") or 99, r["id"])):
        if it["kind"] not in ("experiment", "task") or (ws and it["ws"] != ws):
            continue
        line = {"id": it["id"], "p": it.get("priority"), "summary": it.get("summary")}
        if it["status"] == "running":
            running.append(line)
        elif it["status"] == "planned":
            waiting = [d for d in it.get("depends_on") or []
                       if (ix.items.get(d) or {}).get("status") not in CLOSED]
            (blocked if waiting else ready).append({**line, **({"waiting_on": waiting} if waiting else {})})
    return ready, blocked, running


# ---------------------------------------------------------------------------
# NOW.md
# ---------------------------------------------------------------------------
def render_now(ix: Index) -> str:
    dates = [r.get("updated") or r.get("created") or "" for r in ix.items.values()]
    dates += [j["date"] for js in ix.journals.values() for j in js]
    stamp = max([d for d in dates if d] or ["—"])
    L = ["<!-- GENERATED by `agent/scripts/research.py status` from research/**. Do not edit. -->",
         f"# Research: now (as of {stamp})", ""]
    active = {ws: m for ws, m in ix.workstreams.items() if m.get("status") == "active"}
    others = [f"{ws} ({m.get('status')})" for ws, m in ix.workstreams.items() if ws not in active]
    for ws, meta in active.items():
        L += [f"## {meta.get('title')}  ·  `{ws}`", "", meta.get("summary", ""), ""]
        crit = meta.get("criterion")
        if crit:
            L.append(f"**Success rule:** `{crit['metric']}` {crit['op']} {crit['threshold']} on ≥ "
                     f"{crit.get('min_cohorts', 1)} {crit['split']} cohorts (same model)")
        ms_bits = []
        for ms in meta.get("milestones", []):
            items = ms.get("items", [])
            done = bool(ms.get("done")) or (items and all((ix.items.get(i) or {}).get("status") in CLOSED for i in items))
            open_items = [i for i in items if (ix.items.get(i) or {}).get("status") not in CLOSED]
            ms_bits.append(f"{ms.get('id')} {'✓' if done else '☐'}" + (f" ({', '.join(open_items)})" if not done and open_items else ""))
        if ms_bits:
            L.append("**Milestones:** " + " · ".join(ms_bits))
        L.append("")
        ready, blocked, running = ready_and_blocked(ix, ws)
        L += ["### In flight"] + ([f"- **{r['id']}** p{r['p']}: {r['summary']}" for r in running] or ["- (nothing running)"])
        L += ["", "### Next up (ready, by priority)"] + ([f"- **{r['id']}** p{r['p']}: {r['summary']}" for r in ready[:6]] or ["- ⚠ nothing planned: add the next experiment"])
        if len(ready) > 6:
            L.append(f"- … {len(ready) - 6} more: `research.py next`")
        if blocked:
            L += ["", "### Blocked"] + [f"- {r['id']} ← waiting on {', '.join(r['waiting_on'])}" for r in blocked[:6]]
        closed = sorted((r for r in ix.items.values() if r["ws"] == ws and r["kind"] in ("experiment", "task")
                         and r["status"] in CLOSED), key=lambda r: (r.get("updated") or "", r["id"]), reverse=True)
        if closed:
            L += ["", "### Latest outcomes"]
            for r in closed[:5]:
                v = f" [{r['verdict']}]" if r.get("verdict") and r["verdict"] != "n/a" else ""
                L.append(f"- {r['id']} ({r['status']}{v}): {r.get('outcome', '')}")
        for kind, label, n in (("finding", "Recent findings", 5), ("decision", "Recent decisions", 3)):
            rows = ix.q("SELECT id, created, title FROM item WHERE ws=? AND kind=? AND superseded_by IS NULL "
                        "ORDER BY created DESC, id DESC LIMIT ?", ws, kind, n)
            if rows:
                L += ["", f"### {label}"] + [f"- {r['id']} ({r['created']}): {r['title']}" for r in rows]
        journal = ix.journals.get(ws) or []
        if journal:
            last = journal[-1]
            body = last["body"] if len(last["body"]) <= 600 else last["body"][:600].rstrip() + " …"
            head = " ".join(x for x in (last["date"], last["time"], last["label"] and f"· {last['label']}") if x)
            L += ["", f"### Last handoff ({head})", body]
        L.append("")
    if others:
        L += [f"Other workstreams: {', '.join(others)}", ""]
    L += ["---",
          "Query, don't read files: `research.py next` · `show E003` · `find <words>` · `refs <cohort|dataset|id>` · "
          "`results --metric <m> --split external` · `verdict E003`. Guide: `.cursor/skills/research-tracker/SKILL.md`.", ""]
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------
def next_id(ix: Index, prefix: str) -> str:
    nums = [int(i[1:]) for i in ix.items if i.startswith(prefix) and i[1:].isdigit()]
    return f"{prefix}{max(nums, default=0) + 1:03d}"


def ws_dir(ws: str) -> Path:
    path = ROOT / ws
    if not (path / "workstream.md").is_file():
        known = sorted(p.name for p in ROOT.iterdir() if (p / "workstream.md").is_file()) if ROOT.is_dir() else []
        raise TrackerError(f"unknown workstream {ws!r}; known: {known}")
    return path


def default_ws(ix: Index, ws: str | None) -> str:
    if ws:
        return ws
    active = [w for w, m in ix.workstreams.items() if m.get("status") == "active"]
    if len(active) != 1:
        raise TrackerError(f"pass --ws (active workstreams: {active})")
    return active[0]


def slugify(text: str, n: int = 48) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:n].strip("-") or "item"


def parse_list(value: str | None) -> list[str]:
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def check_summary(text: str | None, limit: int, what: str) -> None:
    if text and len(text) > limit:
        raise TrackerError(f"{what} is {len(text)} chars; keep it under {limit} (details go in the body)")


def cmd_new(ix: Index, a) -> dict:
    ws = default_ws(ix, a.ws)
    wdir = ws_dir(ws)
    check_summary(a.summary, SUMMARY_MAX, "summary")
    if a.kind in ("experiment", "task"):
        if not a.summary:
            raise TrackerError("--summary is required (one line, the thing a query shows)")
        deps = parse_list(a.depends_on)
        missing = [d for d in deps if d not in ix.items]
        if missing:
            raise TrackerError(f"unknown dependencies {missing}")
        prefix, folder = ("E", "experiments") if a.kind == "experiment" else ("T", "tasks")
        iid = next_id(ix, prefix)
        fields = {"id": iid, "title": a.title, "status": "planned", "priority": a.priority,
                  "depends_on": deps, "summary": a.summary}
        if a.kind == "experiment":
            fields["hypothesis"] = a.hypothesis or ""
            fields["runs"] = []
        fields["tags"] = parse_list(a.tags)
        fields.update(created=today(), updated=today())
        fm = "".join(f"{k} = {toml_value(v)}\n" for k, v in fields.items())
        if a.kind == "experiment" and a.criterion_none:
            fm += 'criterion = "none"\n'
        sections = (["## Plan", a.plan or "", "", "## Notes", "", "## Interpretation",
                     "<!-- when done: what the computed verdict means; numbers come from `research.py results --experiment "
                     f"{iid}` -->", ""] if a.kind == "experiment" else ["## Plan", a.plan or "", "", "## Notes", ""])
        path = wdir / folder / f"{iid}-{slugify(a.title)}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"+++\n{fm}+++\n" + "\n".join(sections), encoding="utf-8")
        return {"created": iid, "path": rel(path)}

    prefix, fname = ("F", "findings.md") if a.kind == "finding" else ("D", "decisions.md")
    if not a.body:
        raise TrackerError("--body is required: the claim/decision and why, 1-5 lines")
    refs = parse_list(a.refs)
    if a.kind == "finding" and not refs:
        raise TrackerError("findings need --refs (evidence: run:<name>, E###, dataset slug, doc path)")
    iid = next_id(ix, prefix)
    lines = [f"## {iid} · {today()} · {a.title}"]
    if refs:
        lines.append("refs: " + ", ".join(refs))
    if a.tags:
        lines.append("tags: " + ", ".join(parse_list(a.tags)))
    if a.supersedes:
        lines.append("supersedes: " + ", ".join(parse_list(a.supersedes)))
    lines.append(a.body.strip())
    path = wdir / fname
    existing = path.read_text(encoding="utf-8") if path.is_file() else f"# {'Findings' if prefix == 'F' else 'Decisions'}\n"
    path.write_text(existing.rstrip("\n") + "\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return {"created": iid, "path": rel(path)}


def cmd_set(ix: Index, a) -> dict:
    rec = ix.items.get(a.id)
    if not rec or rec["kind"] not in ("experiment", "task"):
        raise TrackerError(f"{a.id} is not an experiment or task (findings/decisions are append-only: add a new one "
                           "with supersedes)")
    if a.field not in SETTABLE:
        raise TrackerError(f"field {a.field!r} is not settable; allowed: {sorted(SETTABLE)} "
                           "(verdicts are computed; runs are linked with link-run)")
    value: object = a.value
    if a.field == "priority":
        value = int(a.value)
    elif a.field in ("depends_on", "tags"):
        value = parse_list(a.value)
        if a.field == "depends_on":
            missing = [d for d in value if d not in ix.items]
            if missing:
                raise TrackerError(f"unknown dependencies {missing}")
    elif a.field == "status" and a.value not in EXPERIMENT_STATUSES:
        raise TrackerError(f"status must be one of {EXPERIMENT_STATUSES}")
    check_summary(value if a.field == "summary" else None, SUMMARY_MAX, "summary")
    check_summary(value if a.field == "outcome" else None, OUTCOME_MAX, "outcome")

    updates = {a.field: value, "updated": today()}
    if a.field == "status" and value in CLOSED and not (rec.get("outcome") or a.outcome):
        raise TrackerError(f"closing {a.id} needs an outcome: pass --outcome \"<one line>\"")
    if a.outcome:
        check_summary(a.outcome, OUTCOME_MAX, "outcome")
        updates["outcome"] = a.outcome
    result = {"updated": a.id, "path": rec["path"]}
    if a.field == "status" and value == "done" and rec["kind"] == "experiment":
        v = ix.verdict(a.id)
        if v["verdict"] == "no-data":
            raise TrackerError(f"{a.id} has a success rule but no matching metric rows ({v['basis']}); link its "
                               "runs first, or close it as abandoned with an outcome saying why")
        updates.update(verdict=v["verdict"], verdict_basis=v["basis"], criterion_hash=v["criterion_hash"])
        result["verdict"] = v["verdict"]
        result["basis"] = v["basis"]
    write_fields(WORKSPACE / rec["path"], updates)
    return result


def cmd_log(ix: Index, a) -> dict:
    ws = default_ws(ix, a.ws)
    path = ws_dir(ws) / "journal.md"
    head = f"## {today()} {datetime.now().strftime('%H:%M')}" + (f" · {a.label}" if a.label else "")
    existing = path.read_text(encoding="utf-8") if path.is_file() else "# Journal (append-only session handoffs)\n"
    path.write_text(existing.rstrip("\n") + "\n\n" + head + "\n" + a.text.strip() + "\n", encoding="utf-8")
    return {"logged": rel(path)}


def cmd_criterion(ix: Index, a) -> dict:
    """Set an experiment's own success rule (or "none", or inherit) — only before its first run."""
    rec = ix.items.get(a.id)
    if not rec or rec["kind"] != "experiment":
        raise TrackerError(f"{a.id} is not an experiment")
    if rec.get("runs") or rec.get("criterion_hash"):
        raise TrackerError(f"{a.id} already has results; its success rule is frozen. Abandon it and plan a new "
                           "experiment with the rule you want")
    if a.none and a.inherit:
        raise TrackerError("pass only one of --none / --inherit")
    if a.none or a.inherit:
        table = None
    else:
        table = {"metric": a.metric, "split": a.split, "op": a.op, "threshold": a.threshold,
                 "min_cohorts": a.min_cohorts}
        if a.models:
            table["models"] = parse_list(a.models)
        if a.cohorts:
            table["cohorts"] = parse_list(a.cohorts)
        probs = criterion_problems({k: v for k, v in table.items() if v is not None})
        if probs:
            raise TrackerError("; ".join(probs) + " (need --metric --split --op --threshold)")
    path = WORKSPACE / rec["path"]
    fm, body = split_doc(path.read_text(encoding="utf-8"))
    lines, out_lines, skip = fm.splitlines(), [], False
    for ln in lines:  # drop any existing criterion (scalar line or [criterion] table)
        if re.match(r"^criterion\s*=", ln):
            continue
        if ln.strip().startswith("["):
            skip = ln.strip() == "[criterion]"
            if skip:
                continue
        if not skip:
            out_lines.append(ln)
    while out_lines and not out_lines[-1].strip():
        out_lines.pop()
    if a.none:
        table_at = next((i for i, ln in enumerate(out_lines) if ln.strip().startswith("[")), len(out_lines))
        out_lines.insert(table_at, 'criterion = "none"')
    elif table:
        out_lines += ["", "[criterion]"] + [f"{k} = {toml_value(v)}" for k, v in table.items()]
    new_fm = "\n".join(out_lines) + "\n"
    tomllib.loads(new_fm)
    path.write_text(f"+++\n{new_fm}+++\n{body}", encoding="utf-8")
    write_fields(path, {"updated": today()})
    effective = Index().criterion_for(a.id)
    return {"updated": a.id, "criterion": effective or "none",
            "source": "own" if table else ("none" if a.none else "workstream")}


def link_run(run: str, experiment: str | None = None, ix: Index | None = None) -> dict:
    """Attach a pulled run to its experiment (from provenance.experiment unless given)."""
    record = load_run(run)
    if record is None:
        raise TrackerError(f"no run record {run}")
    exp = experiment or (record.get("provenance") or {}).get("experiment")
    if not exp:
        return {"run": run, "linked": None, "note": "run has no experiment; pass --experiment"}
    ix = ix or Index()
    rec = ix.items.get(exp)
    if not rec or rec["kind"] != "experiment":
        raise TrackerError(f"{exp} is not an experiment")
    runs = list(rec.get("runs") or [])
    if run in runs:
        return {"run": run, "linked": exp, "already": True}
    updates: dict = {"runs": runs + [run], "updated": today()}
    if not rec.get("criterion_hash"):  # pre-registration: freeze the rule at the first result
        updates["criterion_hash"] = criterion_hash(ix.criterion_for(exp))
    if rec["status"] == "planned":
        updates["status"] = "running"
    bad = [p for row in record.get("metrics") or [] for p in metric_row_problems(row)]
    write_fields(WORKSPACE / rec["path"], updates)
    return {"run": run, "linked": exp, "metric_rows": len(record.get("metrics") or []),
            **({"metric_row_problems": bad[:5]} if bad else {})}


def write_now(ix: Index) -> bool:
    text = render_now(ix)
    if NOW_PATH.is_file() and NOW_PATH.read_text(encoding="utf-8") == text:
        return False
    NOW_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOW_PATH.write_text(text, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Check (also used by workspace_check.py)
# ---------------------------------------------------------------------------
def check(fix: bool = False) -> dict:
    fixed: list[str] = []
    ix = Index()
    if fix:
        for run_dir in sorted(RUNS_DIR.iterdir()) if RUNS_DIR.is_dir() else []:
            record = load_run(run_dir.name) or {}
            exp = (record.get("provenance") or {}).get("experiment")
            if exp and exp in ix.items and run_dir.name not in (ix.items[exp].get("runs") or []):
                link_run(run_dir.name, exp, ix)
                fixed.append(f"linked {run_dir.name} -> {exp}")
                ix = Index()
    probs = [dict(r) for r in ix.q("SELECT level, code, ref, message FROM problem")]

    linked = {r for it in ix.items.values() for r in it.get("runs") or []}
    for run_dir in sorted(RUNS_DIR.iterdir()) if RUNS_DIR.is_dir() else []:
        record = load_run(run_dir.name)
        if record is None:
            continue
        exp = (record.get("provenance") or {}).get("experiment")
        if exp and run_dir.name not in (ix.items.get(exp) or {}).get("runs", []):
            probs.append({"level": "error", "code": "run-not-linked", "ref": run_dir.name,
                          "message": f"run says experiment {exp} but isn't in its runs list (research.py link-run)"})
        elif run_dir.name not in linked and str(record.get("saved_at", "")) >= TRACKER_SINCE:
            probs.append({"level": "warning", "code": "run-orphan", "ref": run_dir.name,
                          "message": "run is not linked to any experiment (colab_sync.py run --experiment E###)"})

    for iid, it in ix.items.items():
        if it["kind"] != "experiment":
            continue
        crit = ix.criterion_for(iid)
        stored_hash = it.get("criterion_hash")
        if stored_hash and stored_hash != criterion_hash(crit):
            probs.append({"level": "error", "code": "criterion-changed", "ref": iid,
                          "message": f"{iid}'s success rule changed after results were linked; restore it, or "
                                     "abandon this experiment and pre-register a new one"})
        if it["status"] == "done":
            v = ix.verdict(iid)
            if v["verdict"] == "no-data":
                probs.append({"level": "error", "code": "done-without-data", "ref": iid,
                              "message": f"{iid} is done but its success rule has no metric rows; "
                                         "link the runs or mark it abandoned"})
            if it.get("verdict") != v["verdict"]:
                probs.append({"level": "error", "code": "verdict-mismatch", "ref": iid,
                              "message": f"stored verdict {it.get('verdict')!r} != computed {v['verdict']!r} "
                                         f"(research.py set {iid} status done recomputes it)"})
        if it["status"] == "running" and it.get("updated"):
            age = (datetime.now() - datetime.strptime(it["updated"], "%Y-%m-%d")).days
            if age > STALE_RUNNING_DAYS:
                probs.append({"level": "warning", "code": "stale-running", "ref": iid,
                              "message": f"running with no update for {age} days"})

    for ws, meta in ix.workstreams.items():
        if meta.get("status") != "active":
            continue
        ready, blocked, running = ready_and_blocked(ix, ws)
        if not (ready or running):
            probs.append({"level": "warning", "code": "no-next-step", "ref": ws,
                          "message": "active workstream has nothing running or ready: plan the next experiment"})

    if fix and write_now(ix):
        fixed.append("regenerated research/NOW.md")
    elif not NOW_PATH.is_file() or NOW_PATH.read_text(encoding="utf-8") != render_now(ix):
        probs.append({"level": "error", "code": "now-stale", "ref": "research/NOW.md",
                      "message": "NOW.md is out of date (research.py status)"})
    return {"problems": probs, "fixed": fixed}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("status", help="regenerate research/NOW.md")
    p.add_argument("--print", action="store_true", help="print NOW.md instead of a summary")
    p = sub.add_parser("next", help="running, ready (by priority) and blocked work")
    p.add_argument("--ws")
    p = sub.add_parser("list", help="one line per item")
    p.add_argument("--kind", choices=["experiment", "task", "finding", "decision", "workstream"])
    p.add_argument("--status")
    p.add_argument("--ws")
    p.add_argument("--all", action="store_true", help="include superseded findings/decisions")
    p.add_argument("--limit", type=int, default=DEFAULT_ROWS)
    p = sub.add_parser("show", help="one item: fields, links, metric count, backlinks")
    p.add_argument("id")
    p.add_argument("--body", action="store_true", help="include the prose body")
    p.add_argument("--section", help="only this ## section of the body")
    p = sub.add_parser("find", help="full-text search (BM25) with snippets")
    p.add_argument("words", nargs="+")
    p.add_argument("--kind", help="experiment | task | finding | decision | workstream | journal")
    p.add_argument("--any", action="store_true", help="match any word instead of all")
    p.add_argument("--limit", type=int, default=15)
    p = sub.add_parser("refs", help="everything that mentions a key: id, run, dataset slug, cohort, tag")
    p.add_argument("key")
    p.add_argument("--limit", type=int, default=DEFAULT_ROWS)
    p = sub.add_parser("results", help="metric rows from linked runs, filtered")
    for flag in ("metric", "split", "model", "cohort", "experiment", "run"):
        p.add_argument(f"--{flag}")
    p.add_argument("--min", type=float)
    p.add_argument("--max", type=float)
    p.add_argument("--all-runs", action="store_true", help="every run, not just the latest per key")
    p.add_argument("--limit", type=int, default=DEFAULT_ROWS)
    p = sub.add_parser("verdict", help="compute an experiment's verdict from its success rule + metrics")
    p.add_argument("id")
    p = sub.add_parser("sql", help="read-only SQL over tables item, edge, metric, fts")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=50)
    sub.add_parser("check", help="consistency problems (workspace_check.py runs this too)")

    p = sub.add_parser("new", help="create an experiment/task, or append a finding/decision")
    p.add_argument("kind", choices=["experiment", "task", "finding", "decision"])
    p.add_argument("--ws")
    p.add_argument("--title", required=True)
    p.add_argument("--summary", help="experiment/task: one line (≤200 chars)")
    p.add_argument("--priority", type=int, default=3, help="1 = highest")
    p.add_argument("--depends-on", help="comma-separated ids")
    p.add_argument("--hypothesis")
    p.add_argument("--plan", help="initial Plan section text")
    p.add_argument("--criterion-none", action="store_true",
                   help="experiment has no metric success rule (verdict n/a)")
    p.add_argument("--tags")
    p.add_argument("--refs", help="finding/decision evidence: E###, run:<name>, dataset slug, doc path")
    p.add_argument("--supersedes", help="finding/decision ids this replaces")
    p.add_argument("--body", help="finding/decision text")
    p = sub.add_parser("criterion", help="set an experiment's own success rule before its first run")
    p.add_argument("id")
    p.add_argument("--metric")
    p.add_argument("--split", choices=SPLITS)
    p.add_argument("--op", choices=tuple(OPS))
    p.add_argument("--threshold", type=float)
    p.add_argument("--min-cohorts", type=int, default=1)
    p.add_argument("--models", help="comma-separated model filter")
    p.add_argument("--cohorts", help="comma-separated cohort filter")
    p.add_argument("--none", action="store_true", help='no numeric rule (verdict "n/a", judged by outcome)')
    p.add_argument("--inherit", action="store_true", help="drop the experiment's own rule; use the workstream's")
    p = sub.add_parser("set", help="change one field of an experiment/task")
    p.add_argument("id")
    p.add_argument("field")
    p.add_argument("value")
    p.add_argument("--outcome", help="with status done/abandoned: one-line outcome")
    p = sub.add_parser("log", help="append a session handoff to the workstream journal")
    p.add_argument("text")
    p.add_argument("--ws")
    p.add_argument("--label")
    p = sub.add_parser("link-run", help="attach a pulled run to its experiment")
    p.add_argument("run")
    p.add_argument("--experiment")

    a = ap.parse_args()
    try:
        ix = Index()
        if a.cmd == "status":
            changed = write_now(ix)
            if a.print:
                print(NOW_PATH.read_text(encoding="utf-8"))
                return
            ready, blocked, running = ready_and_blocked(ix, None)
            out({"now": rel(NOW_PATH), "changed": changed, "running": [r["id"] for r in running],
                 "ready": [r["id"] for r in ready], "blocked": [r["id"] for r in blocked]})
        elif a.cmd == "next":
            ready, blocked, running = ready_and_blocked(ix, a.ws)
            out({"running": running, "ready": ready, "blocked": blocked})
        elif a.cmd == "list":
            where, params = ["kind != 'workstream'" if not a.kind else "kind = ?"], ([] if not a.kind else [a.kind])
            if a.status:
                where.append("status = ?")
                params.append(a.status)
            if a.ws:
                where.append("ws = ?")
                params.append(a.ws)
            if not a.all:
                where.append("superseded_by IS NULL")
            rows = ix.q("SELECT id, kind, status, priority AS p, coalesce(verdict, '') AS verdict, "
                        "CASE WHEN status IN ('done','abandoned') AND outcome IS NOT NULL THEN outcome ELSE summary END AS line "
                        f"FROM item WHERE {' AND '.join(where)} ORDER BY kind, id", *params)
            out(capped(rows, a.limit))
        elif a.cmd == "show":
            rec = ix.items.get(a.id) or (ix.workstreams.get(a.id) and {**ix.workstreams[a.id], "id": a.id,
                                                                        "kind": "workstream",
                                                                        "path": rel(ROOT / a.id / "workstream.md"),
                                                                        "body": ix.workstream_bodies[a.id]})
            if not rec:
                raise TrackerError(f"unknown id {a.id}")
            skip = {"body", "meta", "path", "milestones"} if rec["kind"] != "workstream" else {"body", "meta"}
            res = {k: v for k, v in rec.items() if k not in skip and v not in (None, "", [])}
            res["path"] = rec["path"]
            if rec["kind"] == "experiment":
                res["metric_rows"] = ix.q("SELECT count(*) AS n FROM metric WHERE experiment=?", a.id)[0]["n"]
            res["referenced_by"] = [r["src"] for r in ix.q("SELECT DISTINCT src FROM edge WHERE dst=?", a.id)]
            if a.section or a.body:
                body = rec.get("body", "")
                if a.section:
                    m = re.search(rf"^## {re.escape(a.section)}[^\n]*\n(.*?)(?=^## |\Z)", body, re.M | re.S | re.I)
                    res["section"] = m.group(1).strip() if m else None
                    if not m:
                        res["sections"] = re.findall(r"^## (.+)$", body, re.M)
                else:
                    res["body"] = body.strip()
            out(res)
        elif a.cmd == "find":
            tokens = [re.sub(r'"', "", w) for w in a.words if w.strip('"')]
            query = (" OR " if a.any else " ").join(f'"{t}"' for t in tokens)
            sql = ("SELECT fts.id, fts.kind, i.status, snippet(fts, 2, '[', ']', '…', 10) AS hit FROM fts "
                   "LEFT JOIN item i ON i.id = fts.id WHERE fts MATCH ?"
                   + (" AND fts.kind = ?" if a.kind else "") + " ORDER BY bm25(fts)")
            out(capped(ix.q(sql, query, *([a.kind] if a.kind else [])), a.limit))
        elif a.cmd == "refs":
            key = a.key.lower()
            rows = ix.q("""SELECT DISTINCT i.id, i.kind, i.status,
                                  CASE WHEN i.status IN ('done','abandoned') AND i.outcome IS NOT NULL
                                       THEN i.outcome ELSE i.summary END AS line FROM item i
                           WHERE i.id IN (SELECT src FROM edge WHERE lower(dst) = ? OR lower(dst) = ?)
                              OR i.id IN (SELECT experiment FROM metric WHERE cohort = ? OR model = ?)
                              OR i.id IN (SELECT id FROM fts WHERE fts MATCH ?)
                           ORDER BY i.kind, i.id""", key, f"run:{key}", key, key, f'"{a.key}"')
            res = capped(rows, a.limit)
            res["metric_rows"] = [dict(r) for r in ix.q(
                "SELECT experiment, count(*) AS n FROM metric WHERE cohort = ? OR model = ? OR run = ? "
                "GROUP BY experiment", key, key, a.key)]
            out(res)
        elif a.cmd == "results":
            where, params = [], []
            for col in ("metric", "split", "model", "cohort", "experiment", "run"):
                if getattr(a, col):
                    where.append(f"{col} = ?")
                    params.append(getattr(a, col))
            if a.min is not None:
                where.append("value >= ?")
                params.append(a.min)
            if a.max is not None:
                where.append("value <= ?")
                params.append(a.max)
            clause = (" WHERE " + " AND ".join(where)) if where else ""
            base = f"SELECT * FROM metric{clause}"
            if not a.all_runs:  # latest run per (experiment, model, cohort, split, metric)
                base = (f"SELECT * FROM ({base}) m WHERE run = (SELECT max(run) FROM metric x WHERE "
                        "x.experiment=m.experiment AND x.model=m.model AND x.cohort=m.cohort AND "
                        "x.split=m.split AND x.metric=m.metric)")
            rows = ix.q(f"SELECT experiment, model, cohort, split, metric, round(value, 4) AS value, ci_lo, ci_hi, "
                        f"baseline, run FROM ({base}) ORDER BY metric, value DESC", *params)
            data = [{k: v for k, v in dict(r).items() if v is not None} for r in rows]
            res = {"count": len(data), "rows": data[:a.limit]}
            if len(data) > a.limit:
                res["truncated"] = f"showing {a.limit} of {len(data)}"
            out(res)
        elif a.cmd == "verdict":
            out(ix.verdict(a.id))
        elif a.cmd == "sql":
            ix.db.execute("PRAGMA query_only = ON")
            out(capped(ix.q(a.query), a.limit))
        elif a.cmd == "check":
            res = check()
            out({"ok": not any(p["level"] == "error" for p in res["problems"]), "problems": res["problems"]})
        elif a.cmd == "new":
            res = cmd_new(ix, a)
            write_now(Index())
            out(res)
        elif a.cmd == "set":
            res = cmd_set(ix, a)
            write_now(Index())
            out(res)
        elif a.cmd == "log":
            res = cmd_log(ix, a)
            write_now(Index())
            out(res)
        elif a.cmd == "criterion":
            res = cmd_criterion(ix, a)
            write_now(Index())
            out(res)
        elif a.cmd == "link-run":
            res = link_run(a.run, a.experiment, ix)
            write_now(Index())
            out(res)
    except (TrackerError, sqlite3.Error, ValueError) as exc:
        out({"error": str(exc)})
        raise SystemExit(2)


if __name__ == "__main__":
    main()
