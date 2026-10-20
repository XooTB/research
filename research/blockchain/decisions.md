# Decisions

## D011 · 2026-10-13 · Blockchain literature base: papers from 2018 onward only
refs: T007
tags: scope, literature
User's call (2026-10-13): the seed library covers only papers published in 2018 or later; pre-2018 classics (Bitcoin whitepaper, Zerocash, Oyente, early IoT surveys) are out. Within the window: most-cited 2018-2021 papers plus recent 2022-2026 high-impact work. Rejected: no date limit with foundational classics back to 2008 (too old for the user's purpose).

## D012 · 2026-10-17 · Prune blockchain library to the three chosen domains (FL, supply chain, carbon)
refs: T007, T010
User request: keep T007 field-survey papers only if relevant to blockchain x FL / supply chain / carbon trading. Kept 5: Kim 2019 on-device BFL + Jiang 2024 BFL-IoT survey -> blockchain-fl; Andoni 2018 energy-sector review + Wang 2019 P2P energy trading -> blockchain-carbon (background for P2P electricity-carbon sub-topic); Cole 2019 (duplicate of a T010 pick) PDF merged into the supply-chain record. Deleted 63 (consensus, ZK, DeFi/MEV, L2, interop, privacy, post-quantum, CBDC, SC security, misc) from disk and library DB; recoverable from git commit aa3f2f6. Rejected: keeping all T007 papers (user wants a focused library); archiving them to a side folder (user asked to remove). Library now 160 papers / 35 PDFs.

## D013 · 2026-10-19 · Narrow blockchain research to two topics: medicine/vaccine supply-chain trust, and federated learning for a medical model
refs: D012, T010
supersedes: D012
The team chose two research topics, narrowing D012's three domains:
1. Trust in the medicine/vaccine development-lifecycle supply chain using blockchain (traceability and provenance from development through manufacturing, cold chain and distribution to administration).
2. Federated learning combined with a medical model (blockchain-coordinated or blockchain-audited FL on medical data; the specific clinical model is still open).

Rejected alternatives: keeping carbon/sustainability as a third domain (dropped); a generic supply-chain scope that is not specific to medicine or vaccines; generic federated learning not tied to a medical model. Existing sc/fl library papers stay, and later work should focus on their pharma/vaccine and medical subsets.

## D014 · 2026-10-19 · Drug-development provenance topic (T014) uses a 2014 cutoff; other blockchain topics keep 2018
refs: D011, T014, F022
tags: scope, literature
User request (2026-10-19). Blockchain clinical-trial transparency starts 2016 (Irving & Holden protocol timestamping, Nugent smart contracts, Benchoufi & Ravaud 2017), so the 2018 cutoff dropped the founding work of exactly this topic. Applies only to topic blockchain-drug-development-provenance. Rejected: moving the cutoff for all blockchain topics (not asked; the field-survey topics care about recent trends); keeping 2018 and citing precursors without collecting them.

## D015 · 2026-10-20 · Main topic is the blockchain drug-development provenance framework; pharma supply chain is supporting context
refs: D013, T013, T014, T017, F022, F026
tags: scope, focus
User statement (2026-10-20). The research centres on the drug-development provenance framework (formulation → trials → post-approval changes, visible to patients and prescribers; topic blockchain-drug-development-provenance). The pharma/vaccine supply-chain papers (T013, topic blockchain-pharma-supply-chain) are background and related work for it, not a separate research line. Refines D013, whose topic 1 was framed as supply-chain trust; the federated-learning topic of D013 is not changed by this. Rejected: treating supply chain and provenance as two equal threads (user corrected that framing).
