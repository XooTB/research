# Findings

## F015 · 2026-10-13 · Blockchain PDF sources: eprint.iacr.org blocks scripted downloads; Wayback id_ URLs work
refs: T007, papers/blockchain-topics/blockchain-zk-proofs
tags: tooling, downloads
eprint.iacr.org returns a Cloudflare 403 HTML page to scripted requests (any UA), so most crypto papers (ZK, sharding, PoS) can't be fetched directly. Working fallback: https://web.archive.org/web/2023id_/https://eprint.iacr.org/<yr>/<n>.pdf (the id_ modifier returns the raw PDF; without it Wayback serves an HTML wrapper). Wayback refuses connections after ~10 rapid requests: space requests ~45 s apart. Also: eprints.lancs.ac.uk returns 404 when the request sends 'Accept: application/pdf' (papers_add.py does), 200 without it. Publisher hosts (IEEE/ACM/Elsevier/MDPI/Springer/SSRN) block scripted PDF fetches; arXiv, usenix, ndss, bis.org, nber.org work.
