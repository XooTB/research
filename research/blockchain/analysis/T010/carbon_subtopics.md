# T010: Blockchain x carbon trading / carbon markets / emissions: top-10 sub-topics

## Method

- Source: `carbon.json` (689 OpenAlex records, 2018-2026; citation-biased: 600 most cited + 400 most cited 2024-26, deduped). Title/abstract match is noisy, so each record was classified by hand-assisted reading of title, keywords and venue (no API calls).
- Classes: **core** = blockchain/DLT applied to carbon or emissions markets, accounting, offsets, certificates or carbon-aware energy trading; **adjacent** = legitimate neighbouring lines (energy/carbon footprint of blockchains, blockchain adoption vs emissions econometrics, green finance/ESG/fintech, P2P energy trading without a carbon element); **off-topic** = only passing mention (generic IoT/AI/supply-chain/construction reviews, battery/EV tech, health, etc.), dropped.
- Sub-topic assignment: one sub-topic per kept paper (first-best fit by title/keywords). Momentum = share of papers dated 2024+. Citations are raw OpenAlex counts.
- Caveat: the sample is citation-biased, so older sub-topics look larger than their share of new output; 2025-26 papers have few citations by construction, so for them fwci/percentile and venue were used.

## Counts

| Class | n |
|---|---|
| core | 268 |
| adjacent | 139 |
| off-topic (dropped) | 282 |
| total | 689 |

## Ranking

Rank score = (0.4 x n/max n + 0.4 x n2024+/max n2024+ + 0.2 x share 2024+) x (0.8 + 0.2 x core share): volume and absolute recent output weigh equally, a small bonus for high 2024+ share, and a mild penalty for purely adjacent sub-topics. Total citations are shown but not scored (they are dominated by a few Bitcoin-footprint papers).

| Rank | Sub-topic | n | n 2024+ | Share 2024+ | Total cites | Core / adjacent | Picks |
|---|---|---|---|---|---|---|---|
| 1 | Game-theoretic/operations models of blockchain adoption under carbon policy | 57 | 40 | 70% | 1163 | 57 / 0 | 5 |
| 2 | P2P and integrated electricity-carbon trading (microgrids, EVs, power systems) | 61 | 30 | 49% | 2573 | 24 / 37 | 5 |
| 3 | Compliance carbon/emission-allowance trading platforms (ETS) on blockchain | 56 | 23 | 41% | 2152 | 56 / 0 | 5 |
| 4 | Carbon accounting, MRV and footprint verification (buildings, construction, corporate) | 41 | 26 | 63% | 1054 | 41 / 0 | 5 |
| 5 | Voluntary carbon markets, offsets and tokenized/nature-based credits | 41 | 25 | 61% | 723 | 41 / 0 | 5 |
| 6 | Supply-chain carbon footprint tracing and traceability | 23 | 15 | 65% | 915 | 23 / 0 | 5 |
| 7 | Green finance, ESG and fintech with blockchain | 25 | 20 | 80% | 956 | 0 / 25 | 5 |
| 8 | Energy use and carbon footprint of blockchains/crypto-mining | 46 | 13 | 28% | 3173 | 0 / 46 | 6 |
| 9 | Renewable energy certificates and green certificates | 26 | 8 | 31% | 701 | 26 / 0 | 5 |
| 10 | Blockchain adoption and sustainability/emission impact (econometrics, reviews, circular economy) | 31 | 10 | 32% | 2304 | 0 / 31 | 5 |

Note: sub-topic S2 mixes 24 core papers (explicit carbon/green-certificate coupling) with 37 adjacent P2P energy-trading papers; its core part alone would rank lower.

## Sub-topics and key papers

### 1. Game-theoretic/operations models of blockchain adoption under carbon policy

- Counts: n=57, 2024+=40 (70%), total cites=1163, type=core (57 core / 0 adjacent).
- Key papers (F = foundational):

| | Title | First author | Year | Venue | Cites | fwci | DOI |
|---|---|---|---|---|---|---|---|
| F | The influence of carbon emission reduction instruments on blockchain technology adoption in recycling batteries of the new energy vehicles | Zhangwei Feng | 2023 | International Journal of Production Research | 102 | 22.2 | https://doi.org/10.1080/00207543.2023.2175173 |
|  | Implications of information sharing on blockchain adoption in reducing carbon emissions: A mean–variance analysis | Zhiwen Li | 2023 | Transportation Research Part E Logistics and Transportation Review | 67 | 19.4 | https://doi.org/10.1016/j.tre.2023.103254 |
|  | Using blockchain or not? A focal firm's blockchain strategy in the context of carbon emission reduction technology innovation | Jianhua Zhu | 2024 | Business Strategy and the Environment | 76 | 26.1 | https://doi.org/10.1002/bse.3664 |
|  | Should blockchain be used to eliminate greenwashing for green and live-streaming platform operations under carbon trading systems? | Xiaoping Xu | 2025 | European Journal of Operational Research | 49 | 43.8 | https://doi.org/10.1016/j.ejor.2025.02.017 |
|  | Differential game theoretic analysis of the blockchain technology investment and carbon reduction strategy in digital supply chain with government intervention | Yuwei Kang | 2024 | Computers & Industrial Engineering | 62 | 21.3 | https://doi.org/10.1016/j.cie.2024.109953 |

- Open problems: Largest and most 2024+-heavy line (70%); mostly Stackelberg/differential/evolutionary games on a blockchain-adoption decision under cap-and-trade, tax or subsidy. Gaps: models are stylised and similar (saturation risk), rarely calibrate blockchain cost/benefit with real data, and ignore carbon-market price dynamics, border adjustment (CBAM) and verification failure modes beyond a few 2025 papers.

### 2. P2P and integrated electricity-carbon trading (microgrids, EVs, power systems)

- Counts: n=61, 2024+=30 (49%), total cites=2573, type=mixed (core+adjacent) (24 core / 37 adjacent).
- Key papers (F = foundational):

| | Title | First author | Year | Venue | Cites | fwci | DOI |
|---|---|---|---|---|---|---|---|
| F | A blockchain based peer-to-peer trading framework integrating energy and carbon markets | Weiqi Hua | 2020 | Applied Energy | 211 | 26.1 | https://doi.org/10.1016/j.apenergy.2020.115539 |
|  | A blockchain-centric P2P trading framework incorporating carbon and energy trades | Ameni Boumaiza | 2024 | Energy Strategy Reviews | 36 | 13.8 | https://doi.org/10.1016/j.esr.2024.101466 |
|  | Blockchain-Enabled Carbon and Energy Trading for Network-Constrained Coal Mines With Uncertainties | Hongxu Huang | 2023 | IEEE Transactions on Sustainable Energy | 84 | 6.1 | https://doi.org/10.1109/tste.2023.3240203 |
|  | Electricity–carbon coupling markets: mechanisms, models and digital enablers for low-carbon power system | Pengcheng Du | 2026 | Renewable and Sustainable Energy Reviews | 4 | 6.8 | https://doi.org/10.1016/j.rser.2025.116691 |
|  | P2P trading mode for real-time coupled electricity and carbon markets based on a new indicator green energy | Longze Wang | 2023 | Energy | 42 | 3.1 | https://doi.org/10.1016/j.energy.2023.129179 |

- Open problems: Many P2P energy-trading papers are adjacent (no carbon term); the core niche is joint electricity-carbon-green-certificate markets (coupled clearing, cross-chain settlement, CCS/P2G). Gaps: realistic carbon-intensity signals (marginal vs average emissions), scalable consensus for high-frequency trading, privacy, and validation against real grid/market data rather than simulations.

### 3. Compliance carbon/emission-allowance trading platforms (ETS) on blockchain

- Counts: n=56, 2024+=23 (41%), total cites=2152, type=core (56 core / 0 adjacent).
- Key papers (F = foundational):

| | Title | First author | Year | Venue | Cites | fwci | DOI |
|---|---|---|---|---|---|---|---|
| F | Blockchain Enhanced Emission Trading Framework in Fashion Apparel Manufacturing Industry | Bailu Fu | 2018 | Sustainability | 191 | 33.2 | https://doi.org/10.3390/su10041105 |
|  | A comprehensive hierarchical blockchain system for carbon emission trading utilizing blockchain of things and smart contract | Alia Al Sadawi | 2021 | Technological Forecasting and Social Change | 196 | 27.1 | https://doi.org/10.1016/j.techfore.2021.121124 |
|  | Smart contract design and process optimization of carbon trading based on blockchain: The case of China's electric power sector | Tian-yuan Zhang | 2023 | Journal of Cleaner Production | 84 | 19.6 | https://doi.org/10.1016/j.jclepro.2023.136509 |
|  | Leveraging blockchain technology to enhance transparency and efficiency in carbon trading markets | Ameni Boumaiza | 2024 | International Journal of Electrical Power & Energy Systems | 92 | 35.0 | https://doi.org/10.1016/j.ijepes.2024.110225 |
|  | Blockchain-embedded carbon emission allowance pledge financing: Resolving maturity mismatch with machine trust and collateral flexibility | Ting Yang | 2026 | International Journal of Production Economics | 3 | 27.0 | https://doi.org/10.1016/j.ijpe.2026.109947 |

- Open problems: Most papers are architecture/prototype designs (Hyperledger, smart contracts) with simulations; few evaluate real ETS data, throughput/cost versus incumbent registries, or cross-jurisdiction interoperability (EU ETS, China ETS, K-ETS, Article 6). Recent work moves to data-quality regulation, allowance-pledge finance and AI/ML-assisted trading, but empirical field validation and regulator-acceptable governance are missing.

### 4. Carbon accounting, MRV and footprint verification (buildings, construction, corporate)

- Counts: n=41, 2024+=26 (63%), total cites=1054, type=core (41 core / 0 adjacent).
- Key papers (F = foundational):

| | Title | First author | Year | Venue | Cites | fwci | DOI |
|---|---|---|---|---|---|---|---|
| F | Applying blockchain technology for building energy performance measurement, reporting, and verification (MRV) and the carbon credit market: A review of the literature | Junghoon Woo | 2021 | Building and Environment | 210 | 23.0 | https://doi.org/10.1016/j.buildenv.2021.108199 |
|  | Greening inventories: Blockchain to improve the GHG Protocol Program in scope 2 | Eduardo Henrique Diniz | 2021 | Journal of Cleaner Production | 78 | 12.9 | https://doi.org/10.1016/j.jclepro.2021.125900 |
|  | Supporting building life cycle carbon monitoring, reporting and verification: A traceable and immutable blockchain-empowered information management system and application in Hong Kong | Ye Luo | 2024 | Resources Conservation and Recycling | 44 | 16.7 | https://doi.org/10.1016/j.resconrec.2024.107736 |
|  | Artificial intelligence- and blockchain-enabled carbon emissions ledger system (AB-CELS) for sustainable construction processes | Istiqlal Aurangzeb | 2025 | Automation in Construction | 23 | 24.9 | https://doi.org/10.1016/j.autcon.2025.106286 |
|  | Blockchain-based solution to enhance carbon footprint traceability, accounting, and offsetting in the passenger aviation industry | Pratyush Kumar Patro | 2025 | International Journal of Production Research | 30 | 32.7 | https://doi.org/10.1080/00207543.2024.2441450 |

- Open problems: Strong 2024+ growth (63%) in construction/built-environment MRV and corporate scope 2/3 accounting. Gaps: oracle/sensor trust (garbage-in on chain), standardisation with GHG Protocol/ISO 14064, privacy-preserving verification (ZK, federated), and field pilots measuring accounting error reduction.

### 5. Voluntary carbon markets, offsets and tokenized/nature-based credits

- Counts: n=41, 2024+=25 (61%), total cites=723, type=core (41 core / 0 adjacent).
- Key papers (F = foundational):

| | Title | First author | Year | Venue | Cites | fwci | DOI |
|---|---|---|---|---|---|---|---|
| F | Blockchain solutions for carbon markets are nearing maturity | Adam Sipthorpe | 2022 | One Earth | 84 | 15.8 | https://doi.org/10.1016/j.oneear.2022.06.004 |
|  | Trading carbon credit tokens on the blockchain | Laurens A. P. Swinkels | 2024 | International Review of Economics & Finance | 35 | 13.3 | https://doi.org/10.1016/j.iref.2024.01.012 |
|  | Unlocking the transformative potential of blockchain to enhance transparency and efficiency in voluntary carbon markets for a sustainable energy transition | Caleb Kan | 2025 | Energy Research & Social Science | 9 | 9.7 | https://doi.org/10.1016/j.erss.2025.104177 |
|  | The nexus between ReFi, carbon, fossil energy, and clean energy assets: Quantile time–frequency connectedness and portfolio implications | Heng Lei | 2024 | Energy Economics | 27 | 9.6 | https://doi.org/10.1016/j.eneco.2024.107456 |
|  | Blockchain and double auction for credible and efficient voluntary carbon market | Xiaojing Liu | 2026 | Applied Energy | 3 | 27.2 | https://doi.org/10.1016/j.apenergy.2026.127719 |

- Open problems: Fast-growing (61% 2024+) but mostly reviews and prototypes. Gaps: empirical evidence on tokenized credits (KlimaDAO/Toucan, additionality and double-counting, price/liquidity dynamics), link between on-chain token and off-chain registry retirement, MRV for nature-based and CDR credits, and regulation of integrity (greenwashing, fraud detection).

### 6. Supply-chain carbon footprint tracing and traceability

- Counts: n=23, 2024+=15 (65%), total cites=915, type=core (23 core / 0 adjacent).
- Key papers (F = foundational):

| | Title | First author | Year | Venue | Cites | fwci | DOI |
|---|---|---|---|---|---|---|---|
| F | A blockchain-based approach for a multi-echelon sustainable supply chain | Vijaya Kumar Manupati | 2019 | International Journal of Production Research | 341 | 54.7 | https://doi.org/10.1080/00207543.2019.1683248 |
|  | Integrating smart Green Product Platforming for carbon footprint reduction: The role of blockchain technology and stakeholders influence within the agri-food supply chain | Afaf Camel | 2024 | International Journal of Production Economics | 91 | 31.3 | https://doi.org/10.1016/j.ijpe.2024.109251 |
|  | Achieving sustainable carbon-neutral supply chain: A perspective of integrating blockchain technology | Aditi S. Saha | 2025 | Technological Forecasting and Social Change | 11 | 9.8 | https://doi.org/10.1016/j.techfore.2025.124262 |
|  | Blockchain technology adoption for secured and carbon neutral logistics operations: barrier intensity index framework | Anchal Gupta | 2024 | Annals of Operations Research | 40 | 13.7 | https://doi.org/10.1007/s10479-024-05824-w |
|  | Blockchain-Driven Carbon Accountability in Supply Chains | Eid Mohammed Alotaibi | 2024 | Sustainability | 56 | 21.3 | https://doi.org/10.3390/su162410872 |

- Open problems: Mostly conceptual/IoT frameworks and case studies in food, logistics and manufacturing. Gaps: product-level (Scope 3) emission-factor data quality, interoperability across tiers, incentives for supplier participation, and quantified audit/cost benefits versus centralised databases.

### 7. Green finance, ESG and fintech with blockchain

- Counts: n=25, 2024+=20 (80%), total cites=956, type=adjacent (0 core / 25 adjacent).
- Key papers (F = foundational):

| | Title | First author | Year | Venue | Cites | fwci | DOI |
|---|---|---|---|---|---|---|---|
| F | Do FinTech trigger renewable energy use? Evidence from OECD countries | Alexandre Croutzet | 2021 | Renewable Energy | 226 | 28.0 | https://doi.org/10.1016/j.renene.2021.07.144 |
|  | Sustainable finance research: Review and agenda | Monica Singhania | 2023 | International Journal of Finance & Economics | 88 | 18.5 | https://doi.org/10.1002/ijfe.2854 |
|  | Can Fintech Promote Sustainable Finance? Policy Lessons from the Case of Turkey | Orkun Bayram | 2022 | Sustainability | 125 | 24.0 | https://doi.org/10.3390/su141912414 |
|  | Blockchain-enabled green Loans: Mitigating greenwashing through inventory and emission signaling | Xia Bing | 2026 | International Journal of Production Economics | 5 | 31.8 | https://doi.org/10.1016/j.ijpe.2026.109983 |
|  | A Detailed Comprehensive Role of Digital Technologies in Green Finance Initiative for Net‐Zero Energy Transition | Furkan Ahmad | 2025 | Advanced Energy and Sustainability Research | 38 | 35.9 | https://doi.org/10.1002/aesr.202500066 |

- Open problems: Adjacent: fintech/green-finance reviews and econometrics with blockchain as one technology; 80% 2024+ but the blockchain-specific content is thin. Gaps: tokenized green bonds/loans with verifiable use-of-proceeds, emission-linked contract automation, and causal evidence beyond bibliometric reviews.

### 8. Energy use and carbon footprint of blockchains/crypto-mining

- Counts: n=46, 2024+=13 (28%), total cites=3173, type=adjacent (0 core / 46 adjacent).
- Key papers (F = foundational):

| | Title | First author | Year | Venue | Cites | fwci | DOI |
|---|---|---|---|---|---|---|---|
| F | The Carbon Footprint of Bitcoin | Christian Stoll | 2019 | Joule | 539 | 65.1 | https://doi.org/10.1016/j.joule.2019.05.012 |
|  | Quantification of energy and carbon costs for mining cryptocurrencies | Max J. Krause | 2018 | Nature Sustainability | 447 | 43.4 | https://doi.org/10.1038/s41893-018-0152-7 |
|  | Policy assessments for the carbon emission flows and sustainability of Bitcoin blockchain operation in China | Shangrong Jiang | 2021 | Nature Communications | 283 | 48.8 | https://doi.org/10.1038/s41467-021-22256-3 |
|  | Revisiting Bitcoin’s carbon footprint | Alex de Vries | 2022 | Joule | 149 | 28.6 | https://doi.org/10.1016/j.joule.2022.02.005 |
|  | Toward a greener future: A survey on sustainable blockchain applications and impact | Pritam Rani | 2024 | Journal of Environmental Management | 81 | 30.8 | https://doi.org/10.1016/j.jenvman.2024.120273 |
|  | Cryptocurrency blockchain and its carbon footprint: Anticipating future challenges | Ujkan Q. Bajra | 2024 | Technology in Society | 53 | 20.1 | https://doi.org/10.1016/j.techsoc.2024.102571 |

- Open problems: Adjacent and mature (28% 2024+): high-citation estimates of Bitcoin's footprint (Joule, Nature Commun.) are contested on methodology. Gaps: post-Merge PoS/L2 footprints, marginal vs average grid emissions, mining as flexible grid load / flare-gas monetisation, and standardised footprint accounting for non-Bitcoin chains.

### 9. Renewable energy certificates and green certificates

- Counts: n=26, 2024+=8 (31%), total cites=701, type=core (26 core / 0 adjacent).
- Key papers (F = foundational):

| | Title | First author | Year | Venue | Cites | fwci | DOI |
|---|---|---|---|---|---|---|---|
| F | Establishing a Secure, Transparent, and Autonomous Blockchain of Custody for Renewable Energy Credits and Carbon Credits | Michael J. Ashley | 2018 | IEEE Engineering Management Review | 99 | 12.5 | https://doi.org/10.1109/emr.2018.2874967 |
|  | Blockchain-enabled renewable energy certificate trading: A secure and privacy-preserving approach | Wei-Jen Liu | 2023 | Energy | 67 | 15.7 | https://doi.org/10.1016/j.energy.2023.130110 |
|  | Blockchain-based smart trading mechanism for renewable energy power consumption vouchers and green certificates: Platform design and simulation | Shi-man Guo | 2024 | Applied Energy | 36 | 13.7 | https://doi.org/10.1016/j.apenergy.2024.123351 |
|  | Blockchain and Green Certificates Based Market Structure and Transaction Mechanism of Direct Power-Purchase for Industrial Users | Xinxin Ge | 2023 | IEEE Transactions on Industry Applications | 26 | 6.1 | https://doi.org/10.1109/tia.2023.3246966 |
|  | Blockchain for Energy Credits and Certificates: A Comprehensive Review | Syed Muhammad Danish | 2024 | IEEE Transactions on Sustainable Computing | 27 | 10.3 | https://doi.org/10.1109/tsusc.2024.3366502 |

- Open problems: Technically mature designs for REC/green-certificate issuance and trading (tokenization, SSI, privacy-preserving). Gaps: certificate-electricity temporal/geographic matching (24/7 CFE), interoperability between national schemes (I-REC, GO, TIGR), double-counting prevention, and empirical market-efficiency or cost evidence.

### 10. Blockchain adoption and sustainability/emission impact (econometrics, reviews, circular economy)

- Counts: n=31, 2024+=10 (32%), total cites=2304, type=adjacent (0 core / 31 adjacent).
- Key papers (F = foundational):

| | Title | First author | Year | Venue | Cites | fwci | DOI |
|---|---|---|---|---|---|---|---|
| F | Tackling climate change with blockchain | Peter Howson | 2019 | Nature Climate Change | 132 | 20.5 | https://doi.org/10.1038/s41558-019-0567-9 |
|  | Blockchain technology and the circular economy: Implications for sustainability and social responsibility | Arvind Upadhyay | 2021 | Journal of Cleaner Production | 665 | 101.1 | https://doi.org/10.1016/j.jclepro.2021.126130 |
|  | Blockchain market and green finance: The enablers of carbon neutrality in China | Meng Qin | 2023 | Energy Economics | 179 | 37.3 | https://doi.org/10.1016/j.eneco.2022.106501 |
|  | The blockchain-enabled technology and carbon performance: Insights from early adopters | Yudi Fernando | 2021 | Technology in Society | 163 | 27.1 | https://doi.org/10.1016/j.techsoc.2020.101507 |
|  | Promoting blockchain technology in low-carbon management to achieve firm performance from a socio-economic perspective: Empirical evidence from China | Nianqi Deng | 2024 | Journal of Cleaner Production | 37 | 14.1 | https://doi.org/10.1016/j.jclepro.2024.141686 |

- Open problems: Adjacent: reviews and firm/country econometrics on blockchain adoption and carbon performance (circular economy, green transformation). Gaps: identification (self-selected adopters, endogeneity), measurement of 'blockchain adoption' from text/patents, and mechanisms linking adoption to verified emission reductions.
