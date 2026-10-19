# Findings

## F015 · 2026-10-13 · Blockchain PDF sources: eprint.iacr.org blocks scripted downloads; Wayback id_ URLs work
refs: T007, papers/blockchain-topics/blockchain-zk-proofs
tags: tooling, downloads
eprint.iacr.org returns a Cloudflare 403 HTML page to scripted requests (any UA), so most crypto papers (ZK, sharding, PoS) can't be fetched directly. Working fallback: https://web.archive.org/web/2023id_/https://eprint.iacr.org/<yr>/<n>.pdf (the id_ modifier returns the raw PDF; without it Wayback serves an HTML wrapper). Wayback refuses connections after ~10 rapid requests: space requests ~45 s apart. Also: eprints.lancs.ac.uk returns 404 when the request sends 'Accept: application/pdf' (papers_add.py does), 200 without it. Publisher hosts (IEEE/ACM/Elsevier/MDPI/Springer/SSRN) block scripted PDF fetches; arXiv, usenix, ndss, bis.org, nber.org work.

## F016 · 2026-10-17 · Trending blockchain application domains 2018-2025 (OpenAlex share of blockchain papers)
refs: T008, research/blockchain/analysis/T008_openalex_trends.json
Share of all blockchain papers (title/abstract), 2022 -> 2025 (all blockchain: 18.6k -> 39.4k/yr): AI/ML integration 13% -> 30% (LLM/AI-agents 12 -> 527 papers, 2022-25; federated learning 364 -> 1791); supply chain/traceability 17% -> 21%; IoT 18% -> 20% (mature, flat); healthcare 11% -> 12%; sustainability/ESG/circular economy ~7% -> 20% (carbon-credit/trading specifically 115 -> 617 papers 2022-25); energy/P2P trading 8% -> 10%; digital twin 1.0% -> 3.0%; agri-food 3.5% -> 4.5%; DeFi 1.3% -> 2.6%; SSI/decentralized identity 1.1% -> 2.2%; CBDC/stablecoin small but x4 since 2022 (109 -> 452). NFT/metaverse peaked 2023 (6.3%) and is falling (4.0%). Flat or declining share: e-voting, smart cities, vehicles/UAV, construction, IP/copyright. RWA tokenization and DePIN are hot in industry but still tiny in academic literature (205 and 25 papers in 2025). Caveats: keyword matching (sustainability/energy terms are noisy), academic volume not industry adoption, 2025 indexing growth inflates raw counts so compare shares.

## F017 · 2026-10-17 · Validated blockchain application trends: AI, supply chain, digital twin, carbon rise; energy and e-voting claims were wrong
refs: T009, F016, research/blockchain/analysis/T009_v3.py, research/blockchain/analysis/T009_v4.py
supersedes: F016
Validation of F016 (T009). Query semantics OK (AND/OR counts consistent). OpenAlex indexed +34% more works overall in 2025 vs 2024, so raw 2025 growth is mostly indexing; only shares are comparable. Precision of title+abstract matches (15 random 2025 papers/domain, judged): healthcare ~70%, supply chain ~60-65%, LLM ~45%, AI/ML ~40%, NFT ~40%, digital twin ~30%, energy ~25%, sustainability/ESG ~15-20%. Title-only share 2022->2025 (stricter): AI/ML 6.0->14.7 (confirmed, magnitude ~half of abstract-based 13->30); LLM/agents 0.3->0.9; federated learning 1.6->2.9; supply chain 8.8->10.5 (confirmed); healthcare 8.0->8.7 (flat, confirmed); IoT 9.8->8.5 (slightly declining, not rising); sustainability/ESG 2.2->4.0 (rising but F016's 7->20 overstated by noise); carbon 0.4->1.2 (confirmed x3); digital twin 0.4->1.0 (confirmed); NFT/metaverse peak 2023 2.1->1.6 (confirmed); DeFi 0.1->0.4 and SSI 0.5->0.8 (confirmed, small); energy trading/grid 1.9->1.5 (REFUTED: falling, F016's rise came from generic 'energy'); CBDC/stablecoin flat 0.1 (x4 was volume only); tokenization ~1% flat (not 'tiny'; F016 RWA query too narrow); e-voting 1.5->2.1 (REFUTED 'fading': stable/slightly up); smart city flat ~1. Semantic Scholar (independent index, title+abstract) reproduces OpenAlex abstract shares within ~2pp (AI 13.0->29.9, supply chain 15.4->18.6, energy trading 2.7->2.3, NFT 4.0->3.4), so results are not an OpenAlex artifact but share the abstract-mention noise. External bibliometric studies mostly end 2023; they agree supply chain, healthcare, finance are core and AI-blockchain convergence is an established theme; one WoS study reports a 2023 dip in total blockchain output, so total-volume growth is index-dependent.

## F018 · 2026-10-17 · OA PDF coverage is low for blockchain application papers in IEEE/Elsevier/T&F venues
refs: T010, research/blockchain/analysis/T010/resolve_pdfs.py
tags: tooling, downloads
T010: of 156 key papers (venue-filtered, mostly IEEE Trans/IJPR/IJPE/TRE/Applied Energy), Semantic Scholar openAccessPdf gave URLs for 71 but most were landing pages/paywalls rejected by papers_add's PDF sniff; 28 PDFs verified (FL 18/51 thanks to arXiv preprints, supply chain 8/54, carbon 2/51). OpenAlex anonymous budget (~100 calls/day, shared per IP) runs out mid-pull; an API key would be needed for full-population pulls and best_oa_location lookups.

## F019 · 2026-10-17 · Blockchain PDF sources: eprint.iacr.org blocks scripted downloads; Wayback id_ URLs work
refs: T007, T011
tags: tooling, downloads
supersedes: F015
Same content as F015; re-filed because F015's evidence folder (papers/blockchain-topics/blockchain-zk-proofs) was deleted when the library was pruned (D012). eprint.iacr.org returns a Cloudflare 403 HTML page to scripted requests (any UA). Working fallback: https://web.archive.org/web/2023id_/https://eprint.iacr.org/<yr>/<n>.pdf (id_ returns the raw PDF). Wayback refuses connections after ~10 rapid requests: space ~45 s apart. eprints.lancs.ac.uk returns 404 when the request sends 'Accept: application/pdf' (papers_add.py does), 200 without it. Publisher hosts (IEEE/ACM/Elsevier/MDPI/Springer/SSRN) block scripted PDF fetches; arXiv, usenix, ndss, bis.org, nber.org work.

## F020 · 2026-10-18 · IEEE Xplore full text is accessible via Southeast University IP access
refs: T011, papers/blockchain-topics/blockchain-fl
On the university network, IEEE Xplore serves licensed full-text PDFs with no login: resolve the DOI to /document/<arnumber>, GET stamp.jsp?arnumber=N (sets cookies), then stampPDF/getPDF.jsp?tp=&arnumber=N returns application/pdf. Each PDF is stamped 'Authorized licensed use limited to: Southeast University'. On 2026-10-18, 81/81 library papers with 10.1109 DOIs that had no PDF downloaded, all title-verified on page 1 (33 blockchain, 48 kmmu-uddin). This works only from the campus network.

## F021 · 2026-10-19 · Pharma blockchain PDFs: IEEE/arXiv/repository copies download; MDPI, Nature, Europe PMC, PMC block scripted fetches
refs: T013, F018, F020
Of 15 new pharma-blockchain picks, PDFs came from IEEE (3, incl. stampPDF via campus IP), arXiv and a university repository. MDPI, Europe PMC render, PMC and Nature return 403 or an HTML interstitial to scripted requests even for OA papers; these stay metadata-only unless fetched manually.

## F022 · 2026-10-19 · No prior work gives patients or prescribers a blockchain view of a drug's development history
refs: T014, papers/blockchain-drug-development-provenance/README.md
tags: drug-development, provenance, gap
Across 19 searches (OpenAlex, arXiv, PubMed; 2018+), blockchain work on drug R&D splits into (a) clinical-trial data integrity and consent for sponsors/regulators (Benchoufi 2018, Maslove 2018, Wong 2019, Omar 2020), (b) lifecycle position papers without a system (Omidian 2022, 2023), and (c) post-approval supply-chain traceability. None exposes formulation history, protocol amendments, trial results and formulation changes to the end consumer or prescriber. Closest building blocks: BlockTrial's patient-facing interface, consent bound to protocol revisions, the digital product passport concept, and PrivChain/ZKP-style selective disclosure for confidential formulation data. Blockchain papers on pharmacovigilance and electronic product information are few and from low-tier venues.

## F023 · 2026-10-19 · Paper tooling bugs: PubMed DOIs leaked from reference lists; empty downloads were kept as PDFs
refs: agent/scripts/sources/pubmed.py, agent/scripts/papers_add.py, T014
tags: tooling
pubmed.py matched .//ArticleIdList, which includes ReferenceList entries, so a PubMed result carried the DOI of the last paper it cites (e.g. a JMIR paper tagged 10.1371/journal.pbio.1002106). Fixed to read PubmedData/ArticleIdList with an ELocationID fallback. The 6 older PubMed records in the library (ovarian, ids 148-156) were checked and have correct DOIs. papers_add.py kept a 0-byte paper.pdf and reported pdf_ok when a response body was empty; it now requires %PDF magic bytes. 4 pre-existing 0-byte files remain in papers/kmmu-uddin/ (untouched).

## F024 · 2026-10-20 · Publisher PDFs need a real browser; ScienceDirect blocks even that, and no subscription access from current network
refs: T015, F019, F020, F021, papers/blockchain-drug-development-provenance/README.md
tags: pdf, access, tooling
supersedes: F021
Scripted requests (requests/curl, browser UA) get 403 or a bot challenge from JMIR, MDPI, Wiley, ACM, T&F, OUP, medRxiv, Oncotarget, PMC, Europe PMC, Cardiff/Copenhagen repositories and ScienceDirect. A Playwright browser passes the checks for JMIR (/PDF via the browser's request context), MDPI (/pdf), Wiley (pdfdirect), ACM, BMC/Springer OA, OUP, Oncotarget, medRxiv, TechRxiv (/doi/pdf/), Europe PMC (in-page fetch of ?pdf=render; PMC itself shows a reCAPTCHA) and institutional repositories: 20 of 33 recovered. ScienceDirect stays on Cloudflare 'Just a moment' even in the browser, including OA journals. Springer subscription, IEEE, T&F and AHA return paywall pages, so IEEE IP access (F020) was not active from this network on 2026-10-20. OpenAlex OA locations can be mislinked (one gave another journal's article) and loose .pdf links on landing pages are often references (Bitcoin whitepaper, a US statute), so every PDF must be checked against its title (plus first author for short titles).

## F025 · 2026-10-20 · Papers are now filed flat: papers/<topic>/<year>-<author>-<title>.pdf
refs: agent/scripts/papers_add.py, agent/scripts/paper_datasets_extract.py, T015
tags: tooling, layout
User request 2026-10-20: papers_add.py saves PDFs directly as papers/<topic>/<year>-<author>-<short-title>.pdf instead of a folder holding paper.pdf, and stores workspace-relative paths. paper_datasets_extract.py reads both layouts (slug = file stem or folder name, so DB linking via pdf_path LIKE still matches). Topic blockchain-drug-development-provenance was migrated (39 PDFs); older topics still use <slug>/paper.pdf. Skill docs and agent/README.md updated.
