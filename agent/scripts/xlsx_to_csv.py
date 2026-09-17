#!/usr/bin/env python3
"""Convert an .xlsx workbook to CSV(s), stdlib only.

Why this exists: `datasets_to_csv.py`'s Excel path needs pandas, which is
not installed in this workspace's Python 3.14 venv (deliberately minimal,
see `.cursor/rules/colab-compute.md`). An .xlsx is a zip of OOXML parts, so
we parse it directly with `zipfile` + `xml.etree.ElementTree`: read
`xl/sharedStrings.xml` for the shared-string table, `xl/workbook.xml` +
`xl/_rels/workbook.xml.rels` to map sheet names to worksheet parts, then
stream each worksheet's `<row>`/`<c>` cells into CSV rows (blank cells for
gaps, shared strings resolved, numbers/booleans/dates left as the literal
cell text found in the XML).

Usage:
    xlsx_to_csv.py --path FILE.xlsx --out-dir DIR [--sheet NAME ...]

Writes one CSV per sheet (or per `--sheet` if given) named `<slug(sheet)>.csv`
under `--out-dir`. Prints a JSON summary {sheet: {rows, cols, path}} to
stdout; progress goes to stderr.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import emit, eprint, slugify  # noqa: E402

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "pr": "http://schemas.openxmlformats.org/package/2006/relationships"}


def _col_to_index(ref: str) -> int:
    """'AH3' -> 0-based column index for 'AH' (33)."""
    letters = re.match(r"[A-Z]+", ref).group(0)
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


def _shared_strings(z: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    out = []
    for si in root.findall("m:si", NS):
        # Concatenate all <t> runs (plain <t> or inside <r><t>).
        texts = [t.text or "" for t in si.findall(".//m:t", NS)]
        out.append("".join(texts))
    return out


def _sheet_map(z: zipfile.ZipFile) -> dict[str, str]:
    """sheet name -> worksheet part path (e.g. 'xl/worksheets/sheet1.xml')."""
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid_to_target = {
        rel.get("Id"): rel.get("Target")
        for rel in rels.findall("pr:Relationship", NS)
    }
    out = {}
    for sheet in wb.findall(".//m:sheet", NS):
        name = sheet.get("name")
        rid = sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        target = rid_to_target.get(rid)
        if target:
            if not target.startswith("xl/"):
                target = "xl/" + target
            out[name] = target
    return out


def _cell_value(c: ET.Element, shared: list[str]) -> str:
    ctype = c.get("t")
    v = c.find("m:v", NS)
    if ctype == "s":
        if v is None or v.text is None:
            return ""
        idx = int(v.text)
        return shared[idx] if 0 <= idx < len(shared) else ""
    if ctype == "inlineStr":
        t = c.find("m:is/m:t", NS)
        return t.text or "" if t is not None else ""
    if ctype == "str":
        return v.text if v is not None and v.text is not None else ""
    if ctype == "b":
        return "TRUE" if (v is not None and v.text == "1") else "FALSE"
    # numeric (default) / date-serial — leave as the literal text in the XML.
    return v.text if v is not None and v.text is not None else ""


def convert_sheet(z: zipfile.ZipFile, part: str, shared: list[str]) -> list[list[str]]:
    root = ET.fromstring(z.read(part))
    sheet_data = root.find("m:sheetData", NS)
    rows_out: list[list[str]] = []
    max_cols = 0
    for row in sheet_data.findall("m:row", NS):
        cells = {}
        for c in row.findall("m:c", NS):
            ref = c.get("r")
            col_idx = _col_to_index(ref)
            cells[col_idx] = _cell_value(c, shared)
            max_cols = max(max_cols, col_idx + 1)
        rows_out.append(cells)
    # Materialize ragged dict-rows into a dense grid.
    grid = []
    for cells in rows_out:
        row_list = [cells.get(i, "") for i in range(max_cols)]
        grid.append(row_list)
    return grid


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", required=True, help="Path to the .xlsx file")
    ap.add_argument("--out-dir", required=True, help="Directory to write CSV(s) into")
    ap.add_argument("--sheet", action="append", default=None,
                     help="Sheet name to convert (repeatable); default: all sheets")
    args = ap.parse_args()

    path = Path(args.path)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    eprint(f"[xlsx_to_csv] opening {path}")
    summary = {}
    with zipfile.ZipFile(path) as z:
        shared = _shared_strings(z)
        sheets = _sheet_map(z)
        wanted = args.sheet if args.sheet else list(sheets.keys())
        for name in wanted:
            if name not in sheets:
                eprint(f"[xlsx_to_csv] WARNING sheet not found: {name}")
                continue
            eprint(f"[xlsx_to_csv] converting sheet '{name}' ({sheets[name]})")
            grid = convert_sheet(z, sheets[name], shared)
            out_path = out_dir / f"{slugify(name)}.csv"
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerows(grid)
            summary[name] = {
                "rows": len(grid),
                "cols": len(grid[0]) if grid else 0,
                "path": str(out_path),
            }
            eprint(f"[xlsx_to_csv] wrote {out_path} ({len(grid)} rows)")

    emit(summary)


if __name__ == "__main__":
    main()
