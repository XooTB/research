"""Shared helpers: workspace paths, config loading, slugs, HTTP, output.

Kept dependency-light on purpose. The only third-party import is `requests`,
and even that is wrapped so a missing install produces a clear message rather
than a traceback.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# scripts/ -> agent/ -> workspace root
WORKSPACE = Path(__file__).resolve().parents[2]
CONFIG_PATH = WORKSPACE / ".research" / "config.yaml"


# ---------------------------------------------------------------------------
# Minimal config loader (a constrained YAML subset; no external dependency)
# Supports: comments, `key: value`, two levels of nesting by indentation,
# inline lists `[a, b, c]`, quoted/unquoted scalars, bool/int coercion.
# ---------------------------------------------------------------------------
def _coerce(value: str):
    v = value.strip()
    if v == "" or v == "[]":
        return [] if v == "[]" else ""
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [_coerce(x) for x in inner.split(",")]
    if (v[0] == v[-1]) and v[0] in ("'", '"'):
        return v[1:-1]
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
    return v


def load_config() -> dict:
    cfg: dict = {}
    if not CONFIG_PATH.exists():
        return cfg
    stack = [(-1, cfg)]  # (indent, container)
    for raw in CONFIG_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, _, rest = line.strip().partition(":")
        key = key.strip()
        rest = rest.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if rest == "":
            child: dict = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _coerce(rest)
    return cfg


_CONFIG = load_config()


def cfg(path: str, default=None):
    """Dotted lookup into config, e.g. cfg('papers.default_limit', 15)."""
    node = _CONFIG
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return default
    return node


def ws_path(config_key: str, fallback: str) -> Path:
    p = Path(cfg(config_key, fallback))
    return p if p.is_absolute() else (WORKSPACE / p)


def ws_rel(path: str | Path | None) -> str | None:
    """Workspace-relative POSIX string for a path inside the workspace.

    The library DB stores paths this way so it stays valid in any clone and on
    the Colab runtime. Paths outside the workspace are returned unchanged.
    """
    if path is None or str(path) == "":
        return None
    p = Path(path)
    if not p.is_absolute():
        return p.as_posix()
    try:
        return p.resolve().relative_to(WORKSPACE).as_posix()
    except ValueError:
        return p.as_posix()


def ws_abs(path: str | Path | None) -> Path | None:
    """Absolute path for a stored (usually workspace-relative) path."""
    if path is None or str(path) == "":
        return None
    p = Path(path)
    return p if p.is_absolute() else WORKSPACE / p


# ---------------------------------------------------------------------------
# Slugs / filesystem-safe names
# ---------------------------------------------------------------------------
def slugify(text: str, max_len: int = 60) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:max_len].strip("-") or "untitled"


def short_title(title: str, words: int = 5) -> str:
    return slugify(" ".join((title or "").split()[:words]))


# ---------------------------------------------------------------------------
# HTTP (requests wrapper)
# ---------------------------------------------------------------------------
def get_requests():
    try:
        import requests  # noqa: WPS433
        return requests
    except ImportError:
        eprint("ERROR: the 'requests' package is required. "
               "Install it into the project venv: .venv/bin/pip install requests")
        sys.exit(2)


def http_get(url: str, *, params=None, headers=None, timeout: int = 30, stream: bool = False):
    requests = get_requests()
    default_headers = {"User-Agent": "research-agent/0.1 (+local)"}
    if headers:
        default_headers.update(headers)
    return requests.get(url, params=params, headers=default_headers,
                        timeout=timeout, stream=stream)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def emit(payload) -> None:
    """Print a JSON payload to stdout for the agent (me) to read."""
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
