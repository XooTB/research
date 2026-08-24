#!/usr/bin/env python3
"""Extract dataset references (accessions, URLs, named resources) from paper PDFs.

Scans every papers/<collection>/*/paper.pdf, applies regex patterns for common
biomedical data repositories, captures the surrounding sentence as context, and
writes a per-collection CSV + JSON inventory that an LLM (or human) can then
use to fetch the actual datasets.

Usage:
    python extract_datasets.py [--collection ovarian-cancer-prognosis-ml]
                               [--papers-dir papers] [--out-dir docs/extracted]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

# --- Accession patterns: (kind, regex, canonical URL template or None) ---------

ACCESSION_PATTERNS: list[tuple[str, str, str | None]] = [
    ("GEO series",       r"\bGSE\d{2,7}\b",   "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={}"),
    ("GEO sample",       r"\bGSM\d{3,8}\b",   "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={}"),
    ("GEO platform",     r"\bGPL\d{1,5}\b",   "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={}"),
    ("GEO dataset",      r"\bGDS\d{1,5}\b",   "https://www.ncbi.nlm.nih.gov/sites/GDSbrowser?acc={}"),
    ("ArrayExpress",     r"\bE-(?:MTAB|GEOD|TABM|MEXP)-\d+\b",
                         "https://www.ebi.ac.uk/biostudies/arrayexpress/studies/{}"),
    ("SRA/BioProject",   r"\b(?:PRJNA|PRJEB|PRJDB|PRJNZ)\d+\b",
                         "https://www.ncbi.nlm.nih.gov/bioproject/{}"),
    ("SRA study",        r"\b[SED]RP\d{4,}\b", "https://www.ncbi.nlm.nih.gov/sra?term={}"),
    ("dbGaP",            r"\bphs\d{6}(?:\.v\d+\.p\d+)?\b",
                         "https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id={}"),
    ("EGA",              r"\bEGA[SD]\d{6,11}\b",
                         "https://ega-archive.org/search-results.php?query={}"),
    ("GenBank/RefSeq",   r"\b(?:NC|NM|NR|NP|XM|XR)_\d{5,9}(?:\.\d+)?\b", None),
    ("Synapse",          r"\bsyn\d{5,9}\b",  "https://www.synapse.org/#!Synapse:{}"),
    ("DOI",              r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+",
                         "https://doi.org/{}"),
    ("PDB",              r"\b[1-9][A-Za-z0-9]{3}\s*\(PDB\)", None),  # handled specially
]

# Named resources worth flagging even without an accession number.
NAMED_RESOURCES: list[tuple[str, str]] = [
    ("TCGA",        r"\bTCGA(?:[- ][A-Z]{2,4})?\b"),
    ("ICGC",        r"\bICGC\b"),
    ("GTEx",        r"\bGTEx\b"),
    ("cBioPortal",  r"\bcBioPortal\b"),
    ("UCSC Xena",   r"\b(?:UCSC\s+)?Xena\b"),
    ("GDC",         r"\bGenomic Data Commons\b|\bGDC portal\b"),
    ("Bioconductor", r"\bcuratedOvarianData\b|\bcurated[A-Z]\w*Data\b"),
    ("CPTAC",       r"\bCPTAC\b"),
    ("DepMap/CCLE", r"\b(?:CCLE|DepMap|Cancer Cell Line Encyclopedia)\b"),
    ("KMplotter",   r"\bKM[- ]?plot(?:ter)?\b"),
    ("Oncomine",    r"\bOncomine\b"),
    ("HPA",         r"\bHuman Protein Atlas\b"),
]

DATA_URL_DOMAINS = (
    "ncbi.nlm.nih.gov/geo", "ncbi.nlm.nih.gov/sra", "ncbi.nlm.nih.gov/bioproject",
    "ebi.ac.uk", "ega-archive.org", "portal.gdc.cancer.gov", "gdc.cancer.gov",
    "cbioportal.org", "xenabrowser.net", "xena.ucsc.edu", "bioconductor.org",
    "zenodo.org", "figshare.com", "osf.io", "kaggle.com", "synapse.org",
    "datadryad.org", "doi.org", "cancergenome.nih.gov", "portal.gdc",
    "tcga-data.nci.nih.gov", "dcc.icgc.org", "kmplot.com", "depmap.org",
    "gse/", "geo/query", "arrayexpress",
)

URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>()\[\]\"'’”>,;]+", re.IGNORECASE)

# PDF line-wrapping splits URLs across newlines; glue them back together.
WRAP_GLUE_RE = re.compile(r"((?:https?://|www\.)\S*)\s*\n\s*")


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_text(pdf_path: Path) -> str:
    doc = fitz.open(pdf_path)
    try:
        text = "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()
    for _ in range(3):  # URLs may wrap over several lines
        text = WRAP_GLUE_RE.sub(r"\1", text)
    return text


def context_window(text: str, start: int, end: int, pad: int = 160) -> str:
    lo = max(0, start - pad)
    hi = min(len(text), end + pad)
    snippet = normalize_ws(text[lo:hi])
    if lo > 0:
        snippet = "…" + snippet
    if hi < len(text):
        snippet += "…"
    return snippet


def clean_url(url: str) -> str:
    return url.rstrip(".)]}>,;'\"”’")


def scan(text: str) -> list[dict]:
    """Return deduplicated finding dicts for one paper's text."""
    findings: dict[str, dict] = {}

    def add(kind: str, value: str, url: str | None, ctx: str):
        key = value if url is None else url
        if key not in findings:
            findings[key] = {
                "kind": kind, "value": value, "url": url or "", "context": ctx,
            }

    for kind, pattern, url_tpl in ACCESSION_PATTERNS:
        for m in re.finditer(pattern, text):
            val = m.group(0).strip()
            if kind == "PDB":
                continue  # too noisy without explicit "PDB" adjacency
            if kind == "DOI":
                val = val.rstrip(".")
            url = url_tpl.format(val) if url_tpl else None
            add(kind, val, url, context_window(text, m.start(), m.end()))

    for kind, pattern in NAMED_RESOURCES:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            add(f"name:{kind}", m.group(0), None,
                context_window(text, m.start(), m.end()))

    for m in URL_RE.finditer(text):
        url = clean_url(m.group(0))
        if any(dom in url.lower() for dom in DATA_URL_DOMAINS):
            add("url", url, url, context_window(text, m.start(), m.end(), pad=80))

    return list(findings.values())


def process_collection(papers_root: Path, collection: str) -> list[dict]:
    rows: list[dict] = []
    collection_dir = papers_root / collection
    for paper_dir in sorted(collection_dir.iterdir()):
        if not paper_dir.is_dir():
            continue
        pdf = paper_dir / "paper.pdf"
        if not pdf.exists():
            continue
        try:
            text = extract_text(pdf)
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"  ! failed to read {pdf}: {exc}", file=sys.stderr)
            continue
        for f in scan(text):
            rows.append({"paper": paper_dir.name, **f})
        print(f"  {paper_dir.name}: {sum(1 for f in rows if f['paper'] == paper_dir.name)} findings")
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--collection", default=None,
                    help="Subfolder under --papers-dir to scan (default: all)")
    ap.add_argument("--papers-dir", default="papers", type=Path)
    ap.add_argument("--out-dir", default=Path("docs/extracted"), type=Path)
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    collections = ([args.collection] if args.collection
                   else sorted(d.name for d in args.papers_dir.iterdir() if d.is_dir()))

    for collection in collections:
        print(f"Scanning {collection}/")
        rows = process_collection(args.papers_dir, collection)
        if not rows:
            print("  (no findings)")
            continue

        base = args.out_dir / f"{collection}-datasets"
        with base.with_suffix(".csv").open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=["paper", "kind", "value", "url", "context"])
            writer.writeheader()
            writer.writerows(rows)
        base.with_suffix(".json").write_text(json.dumps(rows, indent=2, ensure_ascii=False))

        n_papers = len({r["paper"] for r in rows})
        n_acc = sum(1 for r in rows if not r["kind"].startswith(("name:", "url")))
        print(f"  -> {base.with_suffix('.csv')} ({len(rows)} findings, "
              f"{n_acc} accessions/DOIs across {n_papers} papers)")

        # Keep DB paper<->dataset links in step with the fresh extraction.
        # Failure-safe: linking must never break extraction.
        try:
            import db
            import paper_dataset_links
            conn = db.connect()
            try:
                report = paper_dataset_links.sync_links(
                    conn, base.with_suffix(".csv"), collection)
            finally:
                conn.close()
            print(f"  -> paper_datasets: +{report['links_created']} links "
                  f"({report['paper_datasets_total']} total)", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"  ! link sync failed for {collection}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
