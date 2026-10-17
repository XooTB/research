# Decisions

## D011 · 2026-10-13 · Blockchain literature base: papers from 2018 onward only
refs: T007
tags: scope, literature
User's call (2026-10-13): the seed library covers only papers published in 2018 or later; pre-2018 classics (Bitcoin whitepaper, Zerocash, Oyente, early IoT surveys) are out. Within the window: most-cited 2018-2021 papers plus recent 2022-2026 high-impact work. Rejected: no date limit with foundational classics back to 2008 (too old for the user's purpose).

## D012 · 2026-10-17 · Prune blockchain library to the three chosen domains (FL, supply chain, carbon)
refs: T007, T010
User request: keep T007 field-survey papers only if relevant to blockchain x FL / supply chain / carbon trading. Kept 5: Kim 2019 on-device BFL + Jiang 2024 BFL-IoT survey -> blockchain-fl; Andoni 2018 energy-sector review + Wang 2019 P2P energy trading -> blockchain-carbon (background for P2P electricity-carbon sub-topic); Cole 2019 (duplicate of a T010 pick) PDF merged into the supply-chain record. Deleted 63 (consensus, ZK, DeFi/MEV, L2, interop, privacy, post-quantum, CBDC, SC security, misc) from disk and library DB; recoverable from git commit aa3f2f6. Rejected: keeping all T007 papers (user wants a focused library); archiving them to a side folder (user asked to remove). Library now 160 papers / 35 PDFs.
