---
description: Zip files over 100 MB for GitHub; keep unpacked copies on disk
alwaysApply: true
---

# GitHub 100 MB file packing

GitHub rejects any file over **100 MB**. Working copies stay unzipped on disk
and are gitignored. Git tracks the zip (or zip parts).

Use `agent/scripts/github_pack.py` — do not invent a different naming scheme.

## After creating or downloading a large file

```bash
.venv/bin/python agent/scripts/github_pack.py pack
# or:  ... github_pack.py pack --path datasets/<topic>/<slug>
```

The script zips any file **> 100 MB**. If the zip is still **≥ 100 MB**, it
splits into `*.zip.part01`, `*.zip.part02`, … (90 MB chunks). The unpacked
original is left on disk. `.gitignore` is updated automatically.

## Before working with packed data

Unpacked files must exist on disk (analysis, CSV conversion, verification,
notebooks). After a clone/pull, or if an original is missing:

```bash
.venv/bin/python agent/scripts/github_pack.py unpack
```

Never delete an unpacked original to "clean up" — only the zip/parts are
committed; the unzipped file is the working copy.

## Do not commit unpacked originals

They are listed in `.gitignore` between `# BEGIN github-pack` and
`# END github-pack`. Do not `git add -f` those paths. Do not hand-edit that
block; the pack script owns it.
