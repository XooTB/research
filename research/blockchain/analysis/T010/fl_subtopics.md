# T010: Blockchain x Federated Learning, top 10 sub-topics

**Method.** Source: OpenAlex export fl.json (723 records, citation-biased: top-600 cited 2018-2026 + top-400 cited 2024-2026). Removed 29 off-topic records (blockchain-federation, federated identity/cloud/crowdsourcing, non-ML "federated") leaving 694. Each paper assigned to one sub-topic by title/keyword rules with priority order (verifiability > attack/robustness > incentives > intrusion detection > crypto privacy > efficiency > healthcare > vehicular > industrial/edge > general architecture/surveys), then spot-checked, with a few manual overrides. Assignments are heuristic; generic "privacy-preserving" papers fall in the domain/architecture buckets, so the privacy bucket only counts papers with explicit crypto/DP techniques. Counts reflect cited papers, not the full population.

**Ranking.** score = 0.4*volume (n, scaled to max) + 0.3*recent volume (n 2024+, scaled) + 0.3*momentum (share 2024+, scaled to max). Blends size of the literature with recency (current frontier).

| Rank | Sub-topic | n | n 2024+ | share 2024+ | total cites | score |
|---|---|---|---|---|---|---|
| 1 | Poisoning, Byzantine robustness & trust | 104 | 70 | 67% | 3460 | 0.96 |
| 2 | Intrusion detection & cybersecurity | 70 | 50 | 71% | 2864 | 0.76 |
| 3 | Efficiency, scalability & resource allocation | 89 | 47 | 53% | 3983 | 0.75 |
| 4 | Healthcare & medical | 78 | 48 | 62% | 4350 | 0.75 |
| 5 | Decentralized FL architectures & consensus | 93 | 42 | 45% | 5106 | 0.71 |
| 6 | Privacy-preserving FL on chain (DP/HE/ZK/SMPC) | 43 | 33 | 77% | 1191 | 0.61 |
| 7 | Industrial IoT, smart grid & edge intelligence | 74 | 32 | 43% | 5664 | 0.59 |
| 8 | Incentive mechanisms & contribution evaluation | 53 | 29 | 55% | 1678 | 0.54 |
| 9 | Vehicular, UAV & 6G networks | 49 | 22 | 45% | 3537 | 0.46 |
| 10 | Verifiable, auditable & unlearnable FL | 41 | 17 | 41% | 1599 | 0.39 |

## 1. Poisoning, Byzantine robustness & trust

Detecting/mitigating model poisoning, Byzantine, Sybil and free-rider behaviour in FL using blockchain as trust, reputation and audit layer.

**Counts:** n=104, 2024+=70 (67%), total citations=3460

**Key papers** (F = foundational)

- **[F]** Decentralized Privacy Using Blockchain-Enabled Federated Learning in Fog Computing - Youyang Qu et al., 2020, IEEE Internet of Things Journal, cites 450, fwci 66.6, https://doi.org/10.1109/jiot.2020.2977383
- Privacy-Preserving Byzantine-Robust Federated Learning via Blockchain Systems - Yinbin Miao et al., 2022, IEEE Transactions on Information Forensics and Security, cites 300, fwci 19.8, https://doi.org/10.1109/tifs.2022.3196274
- A Blockchain-Enabled Cold Start Aggregation Scheme for Federated Reinforcement Learning-Based Task Offloading in Zero Trust LEO Satellite Networks - Bomin Mao et al., 2025, IEEE Journal on Selected Areas in Communications, cites 83, fwci 32.4, https://doi.org/10.1109/jsac.2025.3560003
- Entropy-guided meta-learning defense against data poisoning attacks in blockchain-assisted federated learning - Waheeb Algethami et al., 2026, Information Sciences, cites 4, fwci 14.4, https://doi.org/10.1016/j.ins.2026.123389
- Blockchain-enabled defenses in federated learning: A comprehensive survey - Omar Dib et al., 2026, Computer Science Review, cites 4, fwci 14.4, https://doi.org/10.1016/j.cosrev.2026.100932

**Open problems:** Most defenses assume honest-majority validators and are tested on small CNNs; adaptive attacks against the ledger/consensus layer itself and LLM-scale models are barely studied. Evaluation lacks common benchmarks.

## 2. Intrusion detection & cybersecurity

Collaborative intrusion/anomaly/threat detection (IoT, IoV, IIoT, smart grid) trained with FL and coordinated by blockchain.

**Counts:** n=70, 2024+=50 (71%), total citations=2864

**Key papers** (F = foundational)

- **[F]** Blockchain and Federated Learning for Collaborative Intrusion Detection in Vehicular Edge Computing - Hong Liu et al., 2021, IEEE Transactions on Vehicular Technology, cites 288, fwci 20.9, https://doi.org/10.1109/tvt.2021.3076780
- Block Hunter: Federated Learning for Cyber Threat Hunting in Blockchain-Based IIoT Networks - Abbas Yazdinejad et al., 2022, IEEE Transactions on Industrial Informatics, cites 201, fwci 44.2, https://doi.org/10.1109/tii.2022.3168011
- Blockchain and federated learning-based intrusion detection approaches for edge-enabled industrial IoT networks: a survey - Saqib Ali et al., 2023, Ad Hoc Networks, cites 196, fwci 21.9, https://doi.org/10.1016/j.adhoc.2023.103320
- Blockchain-Enabled Federated Learning for Enhanced Collaborative Intrusion Detection in Vehicular Edge Computing - Zakaria Abou El Houda et al., 2024, IEEE Transactions on Intelligent Transportation Systems, cites 97, fwci 16.4, https://doi.org/10.1109/tits.2024.3351699
- Cybersecurity in smart microgrids using blockchain-federated learning and quantum-safe approaches: A comprehensive review - Jameel Ahmad et al., 2025, Applied Energy, cites 38, fwci 14.6, https://doi.org/10.1016/j.apenergy.2025.126118

**Open problems:** Heavy reliance on old datasets (NSL-KDD, CICIDS) and many near-duplicate frameworks; non-IID, concept drift, adversarial robustness and real deployment are open.

## 3. Efficiency, scalability & resource allocation

Reducing latency, communication and storage cost: sharding, DAG ledgers, asynchronous/hierarchical designs, resource and consensus optimisation.

**Counts:** n=89, 2024+=47 (53%), total citations=3983

**Key papers** (F = foundational)

- **[F]** Communication-Efficient Federated Learning and Permissioned Blockchain for Digital Twin Edge Networks - Yunlong Lu et al., 2020, IEEE Internet of Things Journal, cites 283, fwci 18.3, https://doi.org/10.1109/jiot.2020.3015772
- Blockchain Assisted Decentralized Federated Learning (BLADE-FL): Performance Analysis and Resource Allocation - Jun Li et al., 2021, IEEE Transactions on Parallel and Distributed Systems, cites 231, fwci 13.9, https://doi.org/10.1109/tpds.2021.3138848
- DRL-Based Adaptive Sharding for Blockchain-Based Federated Learning - Yijing Lin et al., 2023, IEEE Transactions on Communications, cites 101, fwci 23.6, https://doi.org/10.1109/tcomm.2023.3288591
- Secure and Efficient Federated Learning Through Layering and Sharding Blockchain - Shuo Yuan et al., 2024, IEEE Transactions on Network Science and Engineering, cites 62, fwci 21.7, https://doi.org/10.1109/tnse.2024.3361458
- Resource-Efficient Federated Learning and DAG Blockchain With Sharding in Digital-Twin-Driven Industrial IoT - Li Jiang et al., 2024, IEEE Internet of Things Journal, cites 51, fwci 19.4, https://doi.org/10.1109/jiot.2024.3357827

**Open problems:** Blockchain throughput remains the bottleneck; few real-testbed deployments, and adaptive sharding/DRL schemes are evaluated only in simulation. Energy cost is overlooked.

## 4. Healthcare & medical

Cross-hospital learning on EHR, medical imaging and IoMT with blockchain-secured sharing and compliance.

**Counts:** n=78, 2024+=48 (62%), total citations=4350

**Key papers** (F = foundational)

- **[F]** Blockchain-Federated-Learning and Deep Learning Models for COVID-19 Detection Using CT Imaging - Rajesh Kumar et al., 2020, arXiv (Cornell University), cites 482, fwci n/a, https://doi.org/10.1109/jsen.2021.3076767
- IoMT: A COVID-19 Healthcare System Driven by Federated Learning and Blockchain - Omaji Samuel et al., 2022, IEEE Journal of Biomedical and Health Informatics, cites 113, fwci 25.3, https://doi.org/10.1109/jbhi.2022.3143576
- A secure healthcare 5.0 system based on blockchain technology entangled with federated learning technique - Abdur Rehman et al., 2022, Computers in Biology and Medicine, cites 256, fwci 52.4, https://doi.org/10.1016/j.compbiomed.2022.106019
- Federated Learning Meets Blockchain in Decentralized Data Sharing: Healthcare Use Case - Saeed Hamood Alsamhi et al., 2024, IEEE Internet of Things Journal, cites 129, fwci 49.0, https://doi.org/10.1109/jiot.2024.3367249
- Blockchain-Enabled Federated Learning in Healthcare: Survey and State-of-the-Art - Nasim Nezhadsistani et al., 2025, IEEE Access, cites 31, fwci 33.6, https://doi.org/10.1109/access.2025.3587345

**Open problems:** Mostly simulation on public image datasets; regulatory compliance, real hospital deployments, multimodal/foundation-model FL and cost analyses are missing.

## 5. Decentralized FL architectures & consensus

Core system designs and surveys: serverless/decentralized FL on chain, consensus tailored to learning (e.g. proof of FL), committees, design-choice reviews (default bucket for generic blockchain-FL papers).

**Counts:** n=93, 2024+=42 (45%), total citations=5106

**Key papers** (F = foundational)

- **[F]** A Blockchain-Based Decentralized Federated Learning Framework with Committee Consensus - Yuzheng Li et al., 2020, IEEE Network, cites 644, fwci 25.6, https://doi.org/10.1109/mnet.011.2000263
- Biscotti: A Blockchain System for Private and Secure Federated Learning - Muhammad Shayan et al., 2020, IEEE Transactions on Parallel and Distributed Systems, cites 353, fwci 11.3, https://doi.org/10.1109/tpds.2020.3044223
- A Platform-Free Proof of Federated Learning Consensus Mechanism for Sustainable Blockchains - Yuntao Wang et al., 2022, IEEE Journal on Selected Areas in Communications, cites 98, fwci 19.4, https://doi.org/10.1109/jsac.2022.3213347
- Blockchain-enabled Federated Learning: A Survey - Youyang Qu et al., 2022, ACM Computing Surveys, cites 284, fwci 18.6, https://doi.org/10.1145/3524104
- A multi-center federated learning mechanism based on consortium blockchain for data secure sharing - Bin Wang et al., 2025, Knowledge-Based Systems, cites 39, fwci 16.1, https://doi.org/10.1016/j.knosys.2025.112962
- Privacy-preserving in Blockchain-based Federated Learning systems - K. M. Sameera et al., 2024, Computer Communications, cites 84, fwci 12.4, https://doi.org/10.1016/j.comcom.2024.04.024

**Open problems:** Many surveys but few reproducible open-source systems; unclear when a chain is justified versus a trusted server; consensus designs unifying training work and validation (proof-of-FL) and LLM-era decentralised FL are open.

## 6. Privacy-preserving FL on chain (DP/HE/ZK/SMPC)

Protecting training data and updates with differential privacy, homomorphic encryption, secret sharing/SMPC, TEEs and post-quantum crypto inside blockchain-FL.

**Counts:** n=43, 2024+=33 (77%), total citations=1191

**Key papers** (F = foundational)

- **[F]** Blockchain-Enabled Federated Learning Data Protection Aggregation Scheme With Differential Privacy and Homomorphic Encryption in IIoT - Bin Jia et al., 2021, IEEE Transactions on Industrial Informatics, cites 343, fwci 20.1, https://doi.org/10.1109/tii.2021.3085960
- Blockchain-Based Decentralized and Lightweight Anonymous Authentication for Federated Learning - Mochan Fan et al., 2023, IEEE Transactions on Vehicular Technology, cites 71, fwci 16.6, https://doi.org/10.1109/tvt.2023.3265366
- BFL-SA: Blockchain-based federated learning via enhanced secure aggregation - Yizhong Liu et al., 2024, Journal of Systems Architecture, cites 65, fwci 9.6, https://doi.org/10.1016/j.sysarc.2024.103163
- PBFL: A Privacy-Preserving Blockchain-Based Federated Learning Framework With Homomorphic Encryption and Single Masking - Baofu Han et al., 2025, IEEE Internet of Things Journal, cites 33, fwci 13.6, https://doi.org/10.1109/jiot.2024.3524632
- PQS-BFL: A post-quantum secure blockchain-based federated learning framework - Daniel Commey et al., 2026, Expert Systems with Applications, cites 10, fwci 81.1, https://doi.org/10.1016/j.eswa.2026.131449

**Open problems:** Cost of HE/ZK/TEE on-chain is rarely benchmarked against accuracy and latency; post-quantum and collusion-resistant schemes are emerging (2025-26) but lack standardised evaluation.

## 7. Industrial IoT, smart grid & edge intelligence

Blockchain-FL for industrial IoT, edge/fog computing, digital twins, smart grid/energy trading, manufacturing and smart cities.

**Counts:** n=74, 2024+=32 (43%), total citations=5664

**Key papers** (F = foundational)

- **[F]** Blockchain and Federated Learning for Privacy-Preserved Data Sharing in Industrial IoT - Yunlong Lu et al., 2019, IEEE Transactions on Industrial Informatics, cites 1239, fwci 154.2, https://doi.org/10.1109/tii.2019.2942190
- Privacy-Preserving Blockchain-Based Federated Learning for IoT Devices - Yang Zhao et al., 2020, IEEE Internet of Things Journal, cites 601, fwci 29.7, https://doi.org/10.1109/jiot.2020.3017377
- Federated Learning Meets Blockchain in Edge Computing: Opportunities and Challenges - Dinh C. Nguyen et al., 2021, IEEE Internet of Things Journal, cites 659, fwci 38.7, https://doi.org/10.1109/jiot.2021.3072611
- Blockchain and Federated Learning in P2P Energy Trading: Privacy Protection and Prosumer Incentives - Ziming Liu et al., 2025, IEEE Transactions on Industrial Informatics, cites 27, fwci 29.4, https://doi.org/10.1109/tii.2025.3598484
- Adapting security and decentralized knowledge enhancement in federated learning using blockchain technology: literature review - Menna Mamdouh Orabi et al., 2025, Journal Of Big Data, cites 75, fwci 30.9, https://doi.org/10.1186/s40537-025-01099-5

**Open problems:** Fragmented applications with repetitive designs; interoperability, digital-twin integration, and measured energy/latency overheads on real edge hardware are open.

## 8. Incentive mechanisms & contribution evaluation

Rewards, pricing, game-theoretic and contribution-based payment (tokens, Shapley, Stackelberg) to motivate honest, fair participation in blockchain-based FL.

**Counts:** n=53, 2024+=29 (55%), total citations=1678

**Key papers** (F = foundational)

- **[F]** Hybrid Blockchain-Based Resource Trading System for Federated Learning in Edge Computing - Sizheng Fan et al., 2020, IEEE Internet of Things Journal, cites 125, fwci 16.0, https://doi.org/10.1109/jiot.2020.3028101
- Incentive Mechanism Design for Joint Resource Allocation in Blockchain-Based Federated Learning - Zhilin Wang et al., 2023, IEEE Transactions on Parallel and Distributed Systems, cites 135, fwci 31.1, https://doi.org/10.1109/tpds.2023.3253604
- InFEDge: A Blockchain-Based Incentive Mechanism in Hierarchical Federated Learning for End-Edge-Cloud Communications - Xiaofei Wang et al., 2022, IEEE Journal on Selected Areas in Communications, cites 126, fwci 25.7, https://doi.org/10.1109/jsac.2022.3213323
- A Model Value Transfer Incentive Mechanism for Federated Learning With Smart Contracts in AIoT - Gang Xu et al., 2024, IEEE Internet of Things Journal, cites 70, fwci 10.4, https://doi.org/10.1109/jiot.2024.3468443
- Game-Theoretic Incentive Mechanism for Blockchain-Based Federated Learning - Wenzheng Tang et al., 2025, IEEE Transactions on Mobile Computing, cites 18, fwci 19.5, https://doi.org/10.1109/tmc.2025.3567355

**Open problems:** Incentives are mostly analytical games without real-participant data; combining contribution evaluation with privacy and poisoning resistance, and token economics for foundation-model FL, remain open.

## 9. Vehicular, UAV & 6G networks

Blockchain-FL for internet of vehicles, UAV/drone swarms, space-air-ground and 6G networks.

**Counts:** n=49, 2024+=22 (45%), total citations=3537

**Key papers** (F = foundational)

- **[F]** Blockchain Empowered Asynchronous Federated Learning for Secure Data Sharing in Internet of Vehicles - Yunlong Lu et al., 2020, IEEE Transactions on Vehicular Technology, cites 733, fwci 98.9, https://doi.org/10.1109/tvt.2020.2973651
- Federated Learning With Blockchain for Autonomous Vehicles: Analysis and Design Challenges - Shiva Raj Pokhrel et al., 2020, IEEE Transactions on Communications, cites 530, fwci 23.8, https://doi.org/10.1109/tcomm.2020.2990686
- Blockchain-Empowered Decentralized Horizontal Federated Learning for 5G-Enabled UAVs - Chaosheng Feng et al., 2021, IEEE Transactions on Industrial Informatics, cites 213, fwci 12.8, https://doi.org/10.1109/tii.2021.3116132
- Industrial blockchain threshold signatures in federated learning for unified space-air-ground-sea model training - Jingxue Chen et al., 2024, Journal of Industrial Information Integration, cites 55, fwci 20.9, https://doi.org/10.1016/j.jii.2024.100593
- Privacy-aware electric vehicle load forecasting via blockchain-based federated transfer learning - Ruochen Jin et al., 2025, Complex & Intelligent Systems, cites 11, fwci 12.0, https://doi.org/10.1007/s40747-025-02002-8

**Open problems:** Mobility, intermittent links and latency of consensus vs real-time vehicle needs; realistic V2X/UAV testbeds and cross-domain (space-air-ground) trust are scarce.

## 10. Verifiable, auditable & unlearnable FL

Verifiable aggregation, provenance, accountability/auditing, ZK proofs and machine unlearning enabled by an immutable ledger.

**Counts:** n=41, 2024+=17 (41%), total citations=1599

**Key papers** (F = foundational)

- **[F]** VFChain: Enabling Verifiable and Auditable Federated Learning via Blockchain Systems - Zhe Peng et al., 2021, IEEE Transactions on Network Science and Engineering, cites 217, fwci 12.5, https://doi.org/10.1109/tnse.2021.3050781
- Blockchain-Based Federated Learning With SMPC Model Verification Against Poisoning Attack for Healthcare Systems - Aditya Pribadi Kalapaaking et al., 2023, IEEE Transactions on Emerging Topics in Computing, cites 120, fwci 10.5, https://doi.org/10.1109/tetc.2023.3268186
- Federated Learning With Blockchain-Enhanced Machine Unlearning: A Trustworthy Approach - Xuhan Zuo et al., 2025, IEEE Transactions on Services Computing, cites 25, fwci 9.9, https://doi.org/10.1109/tsc.2025.3553709
- Federated TrustChain: Blockchain-Enhanced LLM Training and Unlearning - Xuhan Zuo et al., 2026, IEEE Transactions on Dependable and Secure Computing, cites 10, fwci 21.3, https://doi.org/10.1109/tdsc.2026.3665277
- Security and Verifiability in Federated Learning: A Zero-Knowledge Reputation-Based Blockchain Framework - Swetha Ghanta et al., 2026, IEEE Transactions on Network Science and Engineering, cites 4, fwci 14.4, https://doi.org/10.1109/tnse.2026.3676154

**Open problems:** Verifiable training (proof-of-learning with ZK) is still prohibitively expensive; unlearning plus audit trails for LLM/regulatory (GDPR) use is new and thin.
