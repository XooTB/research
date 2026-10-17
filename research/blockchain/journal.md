# Journal (append-only session handoffs)

## 2026-10-13 12:38 · blockchain kickoff
Did: started workstream blockchain; T007 done: 11-field map, 68 popular 2018+ papers downloaded to papers/blockchain-topics/ (D011: 2018+ only; F-tooling finding on eprint/Wayback). papers_search.py now returns citation counts (OpenAlex/S2).
State: library DB + references.bib updated, PDFs verified (title on page 1). Nothing committed for this work yet. No research question chosen.
Next: user picks a field (or two) to go deep on; then plan a lit-review task / first experiment in that field.
Watch: papers_add.py --topic X writes to papers/X, not papers/blockchain-topics/X: new blockchain papers need moving (or a small nested-topic change). Citation counts for 2024-26 papers are naturally low; recency, not unpopularity. Pre-existing os-hgsoc workspace_check errors (unpacked GSE32062/GSE9891 matrices missing) untouched.

## 2026-10-17 15:43
Did: T008 done: OpenAlex per-year share of blockchain papers across 24 application domains (2018-2025) + top-cited 2023-25 papers per domain; F016 records the ranking. State: script+json in research/blockchain/analysis/; no new PDFs downloaded; nothing committed. Next: user picks application field(s) to go deep on (candidates: blockchain x AI agents/LLMs, carbon/sustainability, supply-chain traceability, digital twins); then a lit-review task. Watch: keyword counts are noisy (sustainability/energy), measure academic volume not industry adoption; RWA/DePIN underrepresented in literature.

## 2026-10-17 15:51
Did: T009 validated F016 (query semantics, precision sampling, title-only shares, Semantic Scholar cross-check, external bibliometrics); F017 supersedes F016 with corrections. State: scripts in research/blockchain/analysis/T009_*; nothing committed. Next: user picks field(s); recommended blockchain x AI (LLM/agents, federated learning), supply-chain traceability, digital twins, carbon markets. Watch: use title-only shares for trend claims; abstract matching has 15-70% precision; OpenAlex 2025 indexing jump.

## 2026-10-17 18:40
Did: T010 done: OpenAlex pull (citation-biased top 600 + top 400 2024+) per domain; sonnet agents built top-10 sub-topic maps with key papers and open problems (research/blockchain/analysis/T010/*_subtopics.md, *_picks.json); haiku agent recorded 156 papers in papers/blockchain-topics/blockchain-{fl,supply-chain,carbon}, 28 PDFs verified; F018 on OA coverage. State: nothing committed; download agent truncated/lost 2 FL PDFs (ids 241, 283) during a killed rerun. Next: user picks a sub-topic; T011 (PDF gap) if wanted, user previously declined an arXiv-search attempt. Watch: carbon sub-topics 7/8/10 are adjacent lines (green finance, crypto energy use, adoption econometrics), not blockchain-for-carbon-markets; OpenAlex anon budget.

## 2026-10-17 19:04
Did: T011 arXiv pass: title-keyword search over 128 T010 papers lacking PDFs (strict 7-word + loose 4-word passes, fuzzy title match, manual review). Only 2 genuine preprints (Rehman 2022 healthcare 5.0; Kamilaris 2019 agri-food); 2 loose candidates rejected as different papers. Added + verified; blockchain-topics now 98 PDFs (T010 set 30/156). Removed empty leftover folders. State: script research/blockchain/analysis/T010/arxiv_find.py; nothing committed. Next: T011 stays open for OpenAlex-key/Unpaywall lookups or manual library downloads. Watch: journal titles rarely match arXiv titles in these applied venues; arXiv is not a viable bulk source here.

## 2026-10-17 19:11
Did: pruned blockchain library per user (D012): 5 T007 papers kept and moved into blockchain-fl/carbon/supply-chain (Cole 2019 PDF filled a T010 pick), 63 deleted from disk+DB (in git aa3f2f6), BibTeX re-exported; F019 re-files F015 (its evidence folder was deleted). State: papers/blockchain-topics now only blockchain-{fl,supply-chain,carbon}: 160 papers, 35 PDFs (fl 21, sc 10, carbon 4); nothing committed. Next: user picks sub-topic; T011 PDF gap (125 missing) needs OpenAlex key or library access. Watch: deletions show as git removals until committed.
