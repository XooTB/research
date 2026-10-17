# T010: Top 10 research sub-topics in blockchain x supply chain

**Method.** Source: `sc.json` (975 OpenAlex records, citation-biased: top-600 cited 2018-2026 plus top-400 cited 2024-2026). 19 off-topic records dropped (data/cloud/VANET/BIM/health-IT provenance and authentication, Monero traceability); 956 kept. Each paper assigned to one sub-topic by a priority keyword classifier on the title (pharma, finance, economic models, AI, provenance, food, logistics, resilience, sustainability, adoption, IoT/architecture; catch-all = adoption), so counts are approximate and the boundaries overlap. Key papers were chosen by hand from the top of each bin by FWCI, percentile and venue (venue h-index >= 40, mostly OR/IS/TEM journals), with recent papers judged by FWCI/venue rather than raw citations.

**Ranking.** Score = 0.4 x norm(n papers) + 0.35 x norm(n papers 2024+) + 0.25 x norm(share 2024+) (min-max normalised across the 11 bins). It rewards volume and absolute recent activity, with a smaller momentum bonus. Resilience scored lowest of 11 and is reported as runner-up (#11) rather than in the top 10; its picks are included anyway. Note: ADOPT is partly a catch-all (generic reviews/conceptual papers), so its volume is inflated; for topic choice prefer its specific sub-themes.

## Ranking table

| # | Sub-topic | n | n 2024+ | share 2024+ | total cites | score |
|---|---|---|---|---|---|---|
| 1 | Agri-food traceability and food safety | 201 | 76 | 38% | 28,419 | 0.79 |
| 2 | Adoption, barriers, performance impact and conceptual foundations (incl. reviews) | 156 | 52 | 33% | 29,238 | 0.52 |
| 3 | Sustainability, circular economy and ethical sourcing | 116 | 53 | 46% | 19,590 | 0.50 |
| 4 | AI, big data and digital twins combined with blockchain | 65 | 46 | 71% | 5,264 | 0.50 |
| 5 | Economic and game-theoretic models of blockchain value | 86 | 44 | 51% | 10,016 | 0.41 |
| 6 | Logistics, shipping, cross-border trade and e-commerce | 81 | 27 | 33% | 10,715 | 0.19 |
| 7 | Pharmaceutical, healthcare and vaccine supply chains | 56 | 25 | 45% | 6,049 | 0.19 |
| 8 | Supply chain finance, payments and tokenisation | 59 | 23 | 39% | 5,941 | 0.15 |
| 9 | IoT / Industry 4.0 integration architectures, smart-contract and security design | 55 | 18 | 33% | 6,013 | 0.07 |
| 10 | Provenance, authenticity and anti-counterfeiting (luxury, minerals, textiles) | 40 | 15 | 38% | 5,543 | 0.05 |
| 11 (runner-up) | Resilience, risk, visibility and disruption (runner-up) | 41 | 13 | 32% | 5,755 | 0.00 |

## 1. Agri-food traceability and food safety

**Definition.** Farm-to-fork traceability, food safety/recall, fresh produce, halal and agri e-commerce use of blockchain.

**Counts.** 201 papers; 76 from 2024+ (38%); 28,419 total citations.

**Key papers** (F = foundational):

- **F** The rise of blockchain technology in agriculture and food supply chains - Andreas Kamilaris et al., 2019, *Trends in Food Science & Technology* (h=341); cites 1262, FWCI 153.3; https://doi.org/10.1016/j.tifs.2019.07.034
- Modeling the blockchain enabled traceability in agriculture supply chain - Sachin Kamble et al., 2019, *International Journal of Information Management* (h=250); cites 960, FWCI 125.3; https://doi.org/10.1016/j.ijinfomgt.2019.05.023
- Applying blockchain technology to improve agri-food traceability: A review of development methods, benefits and challenges - Huanhuan Feng et al., 2020, *Journal of Cleaner Production* (h=454); cites 789, FWCI 62.4; https://doi.org/10.1016/j.jclepro.2020.121031
- Blockchain implementation for food safety in supply chain: A review - V. Sri Vigna Hema et al., 2024, *Comprehensive Reviews in Food Science and Food Safety* (h=238); cites 109, FWCI 21.3; https://doi.org/10.1111/1541-4337.70002
- Should live streaming be adopted for agricultural supply chain considering platform’s quality improvement and blockchain support? - Xiaoping Xu et al., 2025, *Transportation Research Part E Logistics and Transportation Review* (h=190); cites 58, FWCI 82.2; https://doi.org/10.1016/j.tre.2024.103950

**Open problems.** Most work is pilots and architectures; few quantify value across tiers or handle the oracle problem (garbage-in at the farm/sensor). Recent 2024+ work shifts to pricing/live-streaming agri e-commerce models and consumer willingness-to-pay; field evidence on cost recovery and smallholder inclusion is thin.

## 2. Adoption, barriers, performance impact and conceptual foundations (incl. reviews)

**Definition.** Why firms adopt (or not) blockchain: TOE/TAM/UTAUT, ISM-DEMATEL barrier studies, performance/trust effects, plus general reviews and conceptual frameworks. Partly a catch-all for generic papers.

**Counts.** 156 papers; 52 from 2024+ (33%); 29,238 total citations.

**Key papers** (F = foundational):

- **F** Understanding the Blockchain technology adoption in supply chains-Indian context - Sachin Kamble et al., 2018, *International Journal of Production Research* (h=257); cites 960, FWCI 87.7; https://doi.org/10.1080/00207543.2018.1518610
- Blockchain technology: implications for operations and supply chain management - Rosanna Cole et al., 2019, *Supply Chain Management An International Journal* (h=184); cites 958, FWCI 118.7; https://doi.org/10.1108/scm-09-2018-0309
- Blockchain technology in supply chain operations: Applications, challenges and research opportunities - Pankaj Dutta et al., 2020, *Transportation Research Part E Logistics and Transportation Review* (h=190); cites 1537, FWCI 154.7; https://doi.org/10.1016/j.tre.2020.102067
- Blockchain technology and supply chain performance: The role of trust and relational capabilities - Sirsha Pattanayak et al., 2024, *International Journal of Production Economics* (h=294); cites 102, FWCI 38.8; https://doi.org/10.1016/j.ijpe.2024.109198
- Impact of Consumers Traceability Awareness on Blockchain Adoption in Supply Chains - Xiaopo Zhuo et al., 2025, *IEEE Transactions on Engineering Management* (h=157); cites 22, FWCI 31.3; https://doi.org/10.1109/tem.2025.3552437

**Open problems.** Saturated with cross-sectional SEM/MCDM studies from India/China/Africa; gaps are longitudinal and post-adoption evidence, causal designs, actual (not intended) use, inter-organisational governance and why pilots stall ("unfulfilled promise" papers, 2025).

## 3. Sustainability, circular economy and ethical sourcing

**Definition.** Blockchain for sustainable/green supply chains, circular economy, closed-loop and reverse logistics, carbon accounting, ESG and labour/ethical sourcing.

**Counts.** 116 papers; 53 from 2024+ (46%); 19,590 total citations.

**Key papers** (F = foundational):

- **F** Blockchain technology and its relationships to sustainable supply chain management - Sara Saberi et al., 2018, *International Journal of Production Research* (h=257); cites 4085, FWCI 330.1; https://doi.org/10.1080/00207543.2018.1533261
- Blockchain technology and the sustainable supply chain: Theoretically exploring adoption barriers - Mahtab Kouhizadeh et al., 2020, *International Journal of Production Economics* (h=294); cites 1474, FWCI 141.7; https://doi.org/10.1016/j.ijpe.2020.107831
- Blockchain technology for bridging trust, traceability and transparency in circular supply chain - Piera Centobelli et al., 2021, *Information & Management* (h=251); cites 820, FWCI 95.8; https://doi.org/10.1016/j.im.2021.103508
- Blockchain adoption in supply chains: implications for sustainability - Tianyu Zhang et al., 2024, *Production Planning & Control* (h=139); cites 65, FWCI 24.7; https://doi.org/10.1080/09537287.2023.2296669
- Optimizing Blockchain-Enabled Sustainable Supply Chains - Jingwen Wu et al., 2025, *IEEE Transactions on Engineering Management* (h=157); cites 35, FWCI 31.5; https://doi.org/10.1109/tem.2024.3525105

**Open problems.** Claims that blockchain improves sustainability rest on conceptual or perception data; lacking are measured LCA/carbon outcomes, blockchain energy footprint trade-offs, ESG-regulation (CSDDD, digital product passports) alignment and verified Scope 3 accounting.

## 4. AI, big data and digital twins combined with blockchain

**Definition.** Blockchain combined with machine learning, big-data analytics, digital twins, reinforcement learning, LLMs and Industry 5.0 for supply chain decisions and security.

**Counts.** 65 papers; 46 from 2024+ (71%); 5,264 total citations.

**Key papers** (F = foundational):

- **F** Artificial intelligence and blockchain implementation in supply chains: a pathway to sustainability and data monetisation? - Naoum Tsolakis et al., 2022, *Annals of Operations Research* (h=186); cites 326, FWCI 59.5; https://doi.org/10.1007/s10479-022-04785-2
- A critical analysis of the integration of blockchain and artificial intelligence for supply chain - Vincent Charles et al., 2023, *Annals of Operations Research* (h=186); cites 262, FWCI 61.0; https://doi.org/10.1007/s10479-023-05169-w
- Integrating AI with detection methods, IoT, and blockchain to achieve food authenticity and traceability from farm-to-table - Zhaolong Liu et al., 2025, *Trends in Food Science & Technology* (h=341); cites 88, FWCI 38.1; https://doi.org/10.1016/j.tifs.2025.104925
- Risk Management and Macroeconomic Disruptions in Supply Chains: The Role of Blockchain, Digital Twins, Generative AI, and Quantum Computing - Jiho Yoon et al., 2025, *IEEE Transactions on Engineering Management* (h=157); cites 31, FWCI 27.9; https://doi.org/10.1109/tem.2025.3585433
- A Blockchain-based Digital Twin for IoT deployments in logistics and transportation - Salvador Cuñat et al., 2024, *Future Generation Computer Systems* (h=216); cites 57, FWCI 21.7; https://doi.org/10.1016/j.future.2024.04.011

**Open problems.** Fastest-growing stream (71% of papers 2024+) but dominated by reviews and conceptual frameworks; open: real datasets/benchmarks, LLM and agentic automation with on-chain audit, digital-twin synchronisation, privacy-preserving learning across firms, honest evaluation vs non-blockchain baselines.

## 5. Economic and game-theoretic models of blockchain value

**Definition.** Analytical models (game theory, Stackelberg, contracts, pricing, information asymmetry, who-invests, transaction-cost theory) of when blockchain creates economic value.

**Counts.** 86 papers; 44 from 2024+ (51%); 10,016 total citations.

**Key papers** (F = foundational):

- **F** Blockchain and supply chain relations: A transaction cost theory perspective - Christoph G. Schmidt et al., 2019, *Journal of Purchasing and Supply Management* (h=112); cites 706, FWCI 88.4; https://doi.org/10.1016/j.pursup.2019.100552
- Value and Design of Traceability-Driven Blockchains - Yao Cui et al., 2023, *Manufacturing & Service Operations Management* (h=153); cites 158, FWCI 44.0; https://doi.org/10.1287/msom.2022.1161
- Blockchain‐Enabled Data Sharing in Supply Chains: Model, Operationalization, and Tutorial - Zhiyuan Wang et al., 2021, *Production and Operations Management* (h=184); cites 215, FWCI 31.8; https://doi.org/10.1111/poms.13356
- Blockchain adoption and coordination strategies for green supply chains considering consumer privacy concern - Changhua Liao et al., 2024, *European Journal of Operational Research* (h=412); cites 75, FWCI 35.7; https://doi.org/10.1016/j.ejor.2024.12.022
- Eliminating information asymmetry in supply chains: Blockchain-driven or not - Shuai Liu et al., 2025, *Transportation Research Part E Logistics and Transportation Review* (h=190); cites 25, FWCI 35.4; https://doi.org/10.1016/j.tre.2025.104208

**Open problems.** Models are stylised dual-channel/two-echelon Stackelberg settings repeating the same cost-vs-information trade-off; open: multi-tier and network structures, empirically calibrated parameters, consumer behaviour and trust, interoperability/platform competition, regulatory and data-ownership effects.

## 6. Logistics, shipping, cross-border trade and e-commerce

**Definition.** Blockchain in freight, ports, maritime, air cargo, cross-border trade documents, cold chain, e-commerce and last-mile.

**Counts.** 81 papers; 27 from 2024+ (33%); 10,715 total citations.

**Key papers** (F = foundational):

- **F** Blockchain in global supply chains and cross border trade: a critical synthesis of the state-of-the-art, challenges and opportunities - Yanling Chang et al., 2019, *International Journal of Production Research* (h=257); cites 692, FWCI 86.2; https://doi.org/10.1080/00207543.2019.1651946
- Evaluating the factors that influence blockchain adoption in the freight logistics industry - Ifeyinwa Juliet Orji et al., 2020, *Transportation Research Part E Logistics and Transportation Review* (h=190); cites 360, FWCI 48.8; https://doi.org/10.1016/j.tre.2020.102025
- Blockchain in transport and logistics – paradigms and transitions - Lenny S. C. Koh et al., 2020, *International Journal of Production Research* (h=257); cites 261, FWCI 38.1; https://doi.org/10.1080/00207543.2020.1736428
- Blockchain adoption in cross-border cold supply chains: Cost, Efficiency and Trust - Abhinay Mishra et al., 2025, *Transportation Research Part E Logistics and Transportation Review* (h=190); cites 21, FWCI 29.8; https://doi.org/10.1016/j.tre.2025.104236
- Blockchain-based solution to enhance carbon footprint traceability, accounting, and offsetting in the passenger aviation industry - Pratyush Kumar Patro et al., 2025, *International Journal of Production Research* (h=257); cites 30, FWCI 32.7; https://doi.org/10.1080/00207543.2024.2441450

**Open problems.** Strong on frameworks and barrier studies; open: cross-border document digitisation with legal validity (eBL, MLETR), port-community interoperability, quantified cost/lead-time gains, cold-chain sensor integrity and carbon traceability.

## 7. Pharmaceutical, healthcare and vaccine supply chains

**Definition.** Drug traceability, anti-falsified medicines, healthcare/medical-supply and vaccine cold-chain and procurement with blockchain.

**Counts.** 56 papers; 25 from 2024+ (45%); 6,049 total citations.

**Key papers** (F = foundational):

- **F** A Novel Medical Blockchain Model for Drug Supply Chain Integrity Management in a Smart Hospital - Faisal Jamil et al., 2019, *Electronics* (h=157); cites 454, FWCI 62.4; https://doi.org/10.3390/electronics8050505
- Blockchain implementation in pharmaceutical supply chains: A review and conceptual framework - Abhijeet Ghadge et al., 2022, *International Journal of Production Research* (h=257); cites 177, FWCI 34.2; https://doi.org/10.1080/00207543.2022.2125595
- Vaccine supply chain management: An intelligent system utilizing blockchain, IoT and machine learning - Hui Hu et al., 2022, *Journal of Business Research* (h=405); cites 173, FWCI 36.9; https://doi.org/10.1016/j.jbusres.2022.113480
- Blockchain technology: A potential tool for the management of pharma supply chain - Wasim Akram et al., 2024, *Research in Social and Administrative Pharmacy* (h=94); cites 73, FWCI 27.7; https://doi.org/10.1016/j.sapharm.2024.02.014
- Blockchain Technology Applications in Healthcare Supply Chains—A Review - Sarthak Dhingra et al., 2024, *IEEE Access* (h=378); cites 60, FWCI 22.8; https://doi.org/10.1109/access.2023.3348813

**Open problems.** Drug traceability (DSCSA-style) prototypes are plentiful; gaps are interoperability with serialisation systems, scalability/privacy of patient-linked data, vaccine cold-chain evidence in low-resource settings and real deployments rather than simulations.

## 8. Supply chain finance, payments and tokenisation

**Definition.** Supply chain finance, credit sharing, accounts receivable, working capital, payments, tokens and insurance enabled by blockchain.

**Counts.** 59 papers; 23 from 2024+ (39%); 5,941 total citations.

**Key papers** (F = foundational):

- **F** On the Financing Benefits of Supply Chain Transparency and Blockchain Adoption - Jiri Chod et al., 2020, *Management Science* (h=489); cites 658, FWCI 86.8; https://doi.org/10.1287/mnsc.2019.3434
- Supply Chain Finance Innovation Using Blockchain - Mingxiao Du et al., 2020, *IEEE Transactions on Engineering Management* (h=157); cites 422, FWCI 50.6; https://doi.org/10.1109/tem.2020.2971858
- Blockchain-Enabled Deep-Tier Supply Chain Finance - Lingxiu Dong et al., 2022, *Manufacturing & Service Operations Management* (h=153); cites 144, FWCI 29.5; https://doi.org/10.1287/msom.2022.1123
- Integrating digital twin and blockchain for responsive working capital management in supply chains facing financial disruptions - Ehsan Badakhshan et al., 2025, *International Journal of Production Research* (h=257); cites 27, FWCI 73.4; https://doi.org/10.1080/00207543.2025.2507112
- Financing decisions in capital-constrained supply chains considering uncertain emission reduction outputs and blockchain technology applications - Juanjuan Qin et al., 2025, *International Journal of Production Research* (h=257); cites 19, FWCI 26.9; https://doi.org/10.1080/00207543.2025.2483432

**Open problems.** Operations models (Management Science, MSOM) show value of transparency for financing; open: multi-tier (deep-tier) financing at scale, credit scoring from on-chain data, tokenised receivables regulation, LLM/AI-enhanced risk assessment and empirical bank/SME pilots.

## 9. IoT / Industry 4.0 integration architectures, smart-contract and security design

**Definition.** System architectures integrating IoT/RFID/IIoT/BIM with blockchain, smart-contract design, privacy, access control, consensus and scalability for supply chains.

**Counts.** 55 papers; 18 from 2024+ (33%); 6,013 total citations.

**Key papers** (F = foundational):

- **F** Blockchain-oriented dynamic modelling of smart contract design and execution in the supply chain - Alexandre B. Dolgui et al., 2019, *International Journal of Production Research* (h=257); cites 545, FWCI 88.1; https://doi.org/10.1080/00207543.2019.1627439
- Blockchain-Enhanced Data Sharing With Traceable and Direct Revocation in IIoT - Keping Yu et al., 2021, *IEEE Transactions on Industrial Informatics* (h=258); cites 362, FWCI 65.8; https://doi.org/10.1109/tii.2021.3049141
- Real-time supply chain—A blockchain architecture for project deliveries - Petri Helo et al., 2019, *Robotics and Computer-Integrated Manufacturing* (h=160); cites 281, FWCI 36.6; https://doi.org/10.1016/j.rcim.2019.101909
- IoT-BIM and blockchain integration for enhanced data traceability in offsite manufacturing - Roberto Brandín et al., 2024, *Automation in Construction* (h=244); cites 124, FWCI 23.2; https://doi.org/10.1016/j.autcon.2024.105266
- Blockchain applications in the construction supply chain - Mohammadhossein Heydari et al., 2025, *Automation in Construction* (h=244); cites 24, FWCI 26.0; https://doi.org/10.1016/j.autcon.2025.105998

**Open problems.** Architecture papers are numerous but hard to compare; open: standard benchmarks for throughput/latency/cost, off-chain data integrity (oracles, trusted hardware), lightweight authentication, construction/BIM and digital-product-passport integration.

## 10. Provenance, authenticity and anti-counterfeiting (luxury, minerals, textiles)

**Definition.** Product provenance, authentication and anti-counterfeiting, high-value goods (diamonds, luxury, jewels, minerals) and compliance/responsible sourcing.

**Counts.** 40 papers; 15 from 2024+ (38%); 5,543 total citations.

**Key papers** (F = foundational):

- **F** Toward an ontology‐driven blockchain design for supply‐chain provenance - Henry Kim et al., 2018, *Intelligent systems in accounting, finance and management/Intelligent systems in accounting, finance & management* (h=56); cites 651, FWCI 132.7; https://doi.org/10.1002/isaf.1424
- Blockchain-technology-supported platforms for diamond authentication and certification in luxury supply chains - Tsan‐Ming Choi et al., 2019, *Transportation Research Part E Logistics and Transportation Review* (h=190); cites 610, FWCI 79.5; https://doi.org/10.1016/j.tre.2019.05.011
- Combating Copycats in the Supply Chain with Permissioned Blockchain Technology - Bin Shen et al., 2021, *Production and Operations Management* (h=184); cites 465, FWCI 70.5; https://doi.org/10.1111/poms.13456
- Blockchain technology for supply chain provenance: increasing supply chain efficiency and consumer trust - Elena Isabel Vazquez Melendez et al., 2024, *Supply Chain Management An International Journal* (h=184); cites 157, FWCI 60.0; https://doi.org/10.1108/scm-08-2023-0383
- Blockchain for compliance: an information processing case study of mandatory supply chain transparency in conflict minerals sourcing - Alisha Tuladhar et al., 2024, *Supply Chain Management An International Journal* (h=184); cites 46, FWCI 17.6; https://doi.org/10.1108/scm-11-2023-0585

**Open problems.** Small but high-impact stream; open: economics of counterfeit deterrence (encroachment, consumer verification), physical-digital binding (NFC/PUF, DNA tagging) beyond the token, compliance-driven traceability (forced labour, conflict minerals) with evidence of effect.

## 11. Resilience, risk, visibility and disruption (runner-up) (runner-up)

**Definition.** Blockchain for supply chain resilience, risk management, ripple effect, visibility, agility and COVID-era disruption.

**Counts.** 41 papers; 13 from 2024+ (32%); 5,755 total citations.

**Key papers** (F = foundational):

- **F** Blockchain technology for enhancing supply chain resilience - Hokey Min et al., 2018, *Business Horizons* (h=200); cites 888, FWCI 103.2; https://doi.org/10.1016/j.bushor.2018.08.012
- Blockchain technology for enhancing swift-trust, collaboration and resilience within a humanitarian supply chain setting - Rameshwar Dubey et al., 2020, *International Journal of Production Research* (h=257); cites 674, FWCI 92.6; https://doi.org/10.1080/00207543.2020.1722860
- Blockchain-supported business model design, supply chain resilience, and firm performance - Guo Li et al., 2022, *Transportation Research Part E Logistics and Transportation Review* (h=190); cites 234, FWCI 38.0; https://doi.org/10.1016/j.tre.2022.102773
- Blockchain technology adoption and supply chain resilience: exploring the role of transformational supply chain leadership - Yang Liu et al., 2024, *Supply Chain Management An International Journal* (h=184); cites 66, FWCI 22.7; https://doi.org/10.1108/scm-08-2023-0390
- Balancing stability and flexibility: The effects of blockchain adoption on supply chain resilience - Haidi Zhou et al., 2025, *International Journal of Production Economics* (h=294); cites 15, FWCI 13.4; https://doi.org/10.1016/j.ijpe.2025.109671

**Open problems.** Mostly survey/SEM evidence that blockchain aids resilience; gaps are causal/quasi-experimental evidence, dynamic-capability mechanisms, trade-off between transparency and flexibility (2025 findings), and recovery models for actual disruptions.
