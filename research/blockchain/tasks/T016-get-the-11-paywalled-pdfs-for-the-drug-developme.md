+++
id = "T016"
title = "Get the 11 paywalled PDFs for the drug-development provenance topic"
status = "planned"
priority = 2
depends_on = []
summary = "Manual/campus download: IEEE 456,461,464 (SEU IP); Elsevier 414,431,432,436; Springer 429,433; T&F 463; AHA 459. Omidian 431/432 first. Links + filenames: topic README."
tags = []
created = "2026-10-20"
updated = "2026-10-20"
+++
## Plan
Papers lack pdf_path in the DB (topic blockchain-drug-development-provenance); list with library.py --papers --topic blockchain-drug-development-provenance. Automated routes are exhausted (F024): ScienceDirect Cloudflare, paywalls elsewhere. User downloads to ~/Downloads; agent checks title+first author, moves to papers/blockchain-drug-development-provenance/<year>-<author>-<title>.pdf, sets pdf_path, re-runs paper_datasets_extract.py --collection, updates README Missing PDFs section.

## Notes
