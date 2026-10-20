+++
id = "T016"
title = "Get the 17 missing PDFs for the drug-development provenance topic"
status = "planned"
priority = 2
depends_on = []
summary = "Manual/campus download of 17 PDFs: IEEE 456,461,464; Elsevier 414,431,432,436,493; Springer 429,433,512; T&F 463,475; AHA 459; ASCO 511; OA-blocked 468,496. README lists all."
tags = []
created = "2026-10-20"
updated = "2026-10-20"
+++
## Plan
Papers lack pdf_path in the DB (topic blockchain-drug-development-provenance); list with library.py --papers --topic blockchain-drug-development-provenance. Automated routes are exhausted (F024): ScienceDirect Cloudflare, paywalls elsewhere. User downloads to ~/Downloads; agent checks title+first author, moves to papers/blockchain-drug-development-provenance/<year>-<author>-<title>.pdf, sets pdf_path, re-runs paper_datasets_extract.py --collection, updates README Missing PDFs section.

## Notes
