# Blockchain drug-development provenance (T014, T015)

Literature base for the proposed framework: a blockchain record of a medicine's
development history (initial formulation, preclinical tests, trial protocols and
amendments, results, formulation tweaks, manufacturing/batch data, approval,
post-market safety) that a **patient or prescribing doctor** can inspect.

Cutoff for this topic is **2014** (D014; other blockchain topics keep 2018, D011).
55 papers: 53 in this folder (library ids 412-464) plus 2 already in the library
under `blockchain-pharma-supply-chain` (402, 407). PDFs: **42/53** here, filed
flat as `<year>-<author>-<title>.pdf`; every one was checked against its title.
"Y" means PDF on disk; "Y*" means a preprint or accepted manuscript, not the
publisher version.

**Gap (F022):** no paper found builds a patient- or prescriber-facing view of a
drug's development history. Work splits into (a) trial-data integrity for
sponsors/regulators, (b) lifecycle position papers, (c) post-approval supply
chain. The closest pieces: BlockTrial's patient-facing interface (416), consent
bound to protocol revisions (421), discovery-to-disposal lifecycle chains
(431, 432), and the digital product passport concept (453).

## 0. Foundations, 2016-2017 (added with the 2014 cutoff, T015)

| id | year | first author | title | venue | PDF |
|---|---|---|---|---|---|
| 455 | 2016 | Nugent | Improving data transparency in clinical trials using blockchain smart contracts | F1000Research | Y |
| 461 | 2016 | Azaria | MedRec: using blockchain for medical data access and permission management | IEEE OBD | |
| 464 | 2016 | Mettler | Blockchain technology in healthcare: the revolution starts here | IEEE Healthcom | |
| 454 | 2017 | Benchoufi | Blockchain technology for improving clinical research quality | Trials | Y |
| 456 | 2017 | Shae | On the design of a blockchain platform for clinical trial and precision medicine | IEEE ICDCS | |
| 457 | 2017 | Ichikawa | Tamper-resistant mobile health using blockchain technology | JMIR mHealth uHealth | Y |
| 458 | 2017 | Kuo | Blockchain distributed ledger technologies for biomedical and health care applications | JAMIA | Y |
| 459 | 2017 | Angraal | Blockchain technology: applications in health care | Circ Cardiovasc Qual Outcomes | |
| 460 | 2017 | Mamoshina | Converging blockchain and next-generation AI to decentralize biomedical research | Oncotarget | Y |
| 462 | 2017 | Ramachandran | Using blockchain and smart contracts for secure data provenance management | arXiv | Y |
| 463 | 2017 | Mackey | Existing and emerging digital technologies to combat the global trade in fake medicines | Expert Opin Drug Saf | |

## A. Clinical-trial provenance and integrity (core evidence layer)

| id | year | first author | title | venue | PDF |
|---|---|---|---|---|---|
| 421 | 2018 | Benchoufi | Blockchain protocols in clinical trials: transparency and traceability of consent | F1000Research | Y |
| 416 | 2018 | Maslove | Using blockchain technology to manage clinical trials data: proof-of-concept (BlockTrial, patient-facing) | JMIR Med Inform | Y |
| 428 | 2018 | Choudhury | Enforcing human subject regulations using blockchain and smart contracts | Blockchain Healthc Today | Y |
| 402 | 2019 | Wong | Prototype of running clinical trials in an untrustworthy environment using blockchain | Nature Communications | in `blockchain-pharma-supply-chain` (no PDF) |
| 420 | 2019 | Choudhury | A blockchain framework for managing and monitoring data in multi-site clinical trials | arXiv | Y |
| 423 | 2019 | Benchoufi | From clinical trials to highly trustable clinical trials | Frontiers in Blockchain | Y |
| 425 | 2019 | Osipenko | Blockchain's potential to improve clinical trials (essay) | BMJ | Y |
| 426 | 2019 | Charles | Blockchain compliance by design: regulatory considerations in clinical research | Frontiers in Blockchain | Y |
| 415 | 2020 | Omar | Ensuring protocol compliance and data transparency in clinical trials using smart contracts | BMC Med Res Methodol | Y |
| 422 | 2020 | Omar | Applications of blockchain technology in clinical trials: review and open challenges | Arab J Sci Eng | Y* (TechRxiv) |
| 418 | 2020 | Zhuang | Development of a blockchain framework for virtual clinical trials | AMIA | Y |
| 419 | 2021 | Mak | Blockchain for informed consent and patient engagement in a clinical trial pilot | Blockchain Healthc Today | Y |
| 417 | 2022 | Zhuang | Re-engineering a clinical trial management system using blockchain | JMIR | Y |
| 424 | 2022 | Hang | Blockchain for clinical trials: taxonomy, challenges, future directions | IET Communications | Y |
| 414 | 2024 | Kushwaha | Enhancing clinical drug trial monitoring with blockchain | Contemp Clin Trials | |
| 427 | 2024 | Arjun | Blockchain-based CTMS: scoping review and conceptual framework | medRxiv | Y |
| 413 | 2025 | Barenji | Blockchain-enabled quality-by-design system for clinical trials | Frontiers in Medicine | Y |
| 412 | 2026 | Sheikh | Blockchain smart contracts for automating clinical trials: systematic review + architecture | JMIR Med Inform | Y |

## B. Whole drug lifecycle and R&D (discovery → formulation → approval)

| id | year | first author | title | venue | PDF |
|---|---|---|---|---|---|
| 433 | 2020 | Yu | Leveraging research failures to accelerate drug discovery and development | Ther Innov Regul Sci | |
| 434 | 2021 | Macdonald | Digital innovation in medicinal product regulatory submission, review and approval | Frontiers in Medicine | Y |
| 438 | 2021 | Olsson | A permissioned blockchain-based system for collaborative drug discovery | SciTePress conf. | Y (manual) |
| 432 | 2022 | Omidian | Blockchain in pharmaceutical life cycle management | Drug Discovery Today | |
| 431 | 2023 | Omidian | Tracing drugs from discovery to disposal | Drug Discovery Today | |
| 436 | 2023 | Sharma | Hyperledger dApp for drug discovery chain management | Comput Ind Eng | |
| 430 | 2024 | Gaynor | Blockchain applications in the pharmaceutical industry | Blockchain Healthc Today | Y |
| 435 | 2025 | Alsalamah | FairChain: transparent blockchain ecosystem for drug development | Electronics | Y |
| 437 | 2025 | Murala | BlockDrugChain: blockchain + ML framework for drug discovery management | Franklin Open | Y (manual) |
| 429 | 2026 | Faiyazuddin | Blockchain across pharma operations incl. formulation development (review) | Pharmaceutical Research | |

## C. Manufacturing, batch records and data originality (formulation tweaks → batches)

| id | year | first author | title | venue | PDF |
|---|---|---|---|---|---|
| 439 | 2019 | Wu | Blockchain recall management in pharmaceutical industry | Procedia CIRP | Y (manual) |
| 451 | 2020 | Eryılmaz | Traceability blockchain prototype for regulated manufacturing industries | ACM IECC | Y |
| 440 | 2021 | Leal | Smart pharmaceutical manufacturing: end-to-end traceability and data integrity | Big Data Research | Y |
| 407 | 2021 | Agrawal | A robust drug recall supply chain management system using Hyperledger | Comput Biol Med | in `blockchain-pharma-supply-chain` |
| 441 | 2023 | Durá | Blockchain for data originality in pharma manufacturing | J Pharm Innov | Y |

## D. Patient-facing access, consent and transparency (the consumer/doctor view)

| id | year | first author | title | venue | PDF |
|---|---|---|---|---|---|
| 443 | 2020 | Porsdam Mann | Blockchain, consent and prosent for medical research | J Med Ethics | Y |
| 446 | 2020 | Peral | Using visualization to build transparency in a healthcare blockchain application | Sustainability | Y |
| 444 | 2022 | Huh | METORY: blockchain dynamic consent platform for clinical trials | Frontiers in Medicine | Y |
| 447 | 2022 | Marbouh | Blockchain for patient safety: use cases and open challenges | Data | Y |
| 442 | 2024 | Charles | Blockchain-based dynamic consent for patient-centric research (protocol) | JMIR Res Protoc | Y |
| 445 | 2024 | Pham | Distributed management of patient data-sharing informed consents | Comput Biol Med | Y |

## E. Provenance and confidentiality building blocks (what to disclose, and to whom)

| id | year | first author | title | venue | PDF |
|---|---|---|---|---|---|
| 450 | 2021 | Malik | PrivChain: provenance and privacy preservation in blockchain supply chains | arXiv | Y |
| 449 | 2022 | Coelho | Blockchain architecture for trust in collaborative scientific experimentation | J Grid Computing | Y |
| 448 | 2024 | Akbarfam | SoK: blockchain for provenance | arXiv | Y |
| 452 | 2024 | Zhang | Blockchain data governance for privacy-preserved sharing of confidential data | PeerJ Comput Sci | Y |
| 453 | 2025 | Xia | Integrating blockchain with digital product passports | Transp Res Part E | Y* (Cardiff repository) |

## Missing PDFs (11)

Paywalled with no access from this network: Elsevier 414, 431, 432, 436;
Springer 429, 433; IEEE 456, 461, 464; Taylor & Francis 463; AHA 459.
(437, 439 and 438 were downloaded by hand on 2026-10-20.)

## Excluded

- "A permissioned blockchain-based clinical trial service platform…" (BioMed Res Int 2021): **retracted**.
- Irving & Holden 2016/2017, "How blockchain-timestamped protocols could improve the
  trustworthiness of medical science" (F1000Research): **retracted by the authors**
  (all three versions) over methodological concerns. The protocol-timestamping idea
  survives in Nugent 2016 (455) and Benchoufi & Ravaud 2017 (454).
