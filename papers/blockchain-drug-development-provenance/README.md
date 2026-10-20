# Blockchain drug-development provenance (T014, T015)

Literature base for the proposed framework: a blockchain record of a medicine's
development history (initial formulation, preclinical tests, trial protocols and
amendments, results, formulation tweaks, manufacturing/batch data, approval,
post-market safety) that a **patient or prescribing doctor** can inspect.

Cutoff for this topic is **2014** (D014; other blockchain topics keep 2018, D011).
106 papers: 104 in this folder (blockchain ids 412-464, non-blockchain context
ids 465-515, section F) plus 2 already in the library under
`blockchain-pharma-supply-chain` (402, 407). PDFs: **87/104** here, filed
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

## F. Non-blockchain context (T017): who needs what, in which standard, after approval

What the framework must show, to whom, in what standard data formats, and how a drug keeps changing after
approval. Not about blockchain; it grounds requirements and the evaluation.

**F1. Patient and prescriber information needs; trial and regulatory transparency**

| id | year | first author | title | venue | PDF |
|---|---|---|---|---|---|
| 465 | 2014 | Jefferson | Oseltamivir: systematic review of clinical study reports and regulatory comments (the Tamiflu case) | BMJ | Y |
| 482 | 2015 | Pires | Readability of medicinal package leaflets: systematic review | Rev Saúde Pública | Y |
| 467 | 2015 | Sydes | Sharing data from clinical trials: rationale for controlled access | Trials | Y |
| 475 | 2016 | Balog-Way | Medicines transparency at the EMA in the new information age | J Risk Research | |
| 483 | 2016 | Hammar | Patients' views on electronic patient information leaflets | Pharmacy Practice | Y |
| 481 | 2016 | Wieseler | Secrecy or transparency? The future of regulatory trial data | CMAJ | Y |
| 466 | 2018 | Chan | Promoting public access to clinical trial protocols | Trials | Y |
| 471 | 2018 | Hopkins | Data sharing from industry-sponsored studies: audit of availability | BMC Medicine | Y |
| 476 | 2018 | Aldinger | Returning aggregate trial results: patient preferences | J Clin Transl Sci | Y |
| 468 | 2019 | Kanter | Industry payment disclosure and public trust in physicians | JAMA Netw Open | |
| 469 | 2019 | Barnes | Lay summaries of clinical study results: overview (EU CTR 536/2014) | Pharmaceutical Medicine | Y |
| 474 | 2020 | Chan | What information do patients want about their medicines? | BMC Health Serv Res | Y |
| 478 | 2020 | Ostropolets | Physicians' information needs where evidence is missing | JAMIA Open | Y |
| 473 | 2021 | Egilman | Transparency of regulatory data across EMA, Health Canada and FDA | J Law Med Ethics | Y |
| 472 | 2022 | Gudi | Regulatory frameworks for clinical trial data sharing: scoping review | JMIR | Y |
| 470 | 2022 | Mitra-Majumdar | Reporting bias in clinical trials: progress toward transparency | PLoS Medicine | Y |
| 485 | 2022 | Bamberger | Replacing vaccine paper package inserts with electronic ones (multi-country) | BMC Public Health | Y |
| 477 | 2022 | Møllebæk | Are drug safety advisories compatible with physicians' information behaviour? | Eur J Health Commun | Y |
| 479 | 2023 | Franzen | Institutional dashboards on clinical trial transparency | PLoS Medicine | Y |
| 480 | 2024 | Hopkins | Accessibility of clinical study reports supporting medicine approvals | J Clin Epidemiol | Y |
| 484 | 2024 | Loh | Patient acceptance of electronic labelling for medicinal products | JMIR | Y |
| 486 | 2025 | Singh | QR codes for patient information leaflet delivery | Explor Res Clin Soc Pharm | Y |
| 487 | 2026 | Choudhury | Guidance on sharing trial results with patients and the public: scoping review | J Clin Epidemiol | Y |

**F2. Data standards the framework should speak** (structured CMC/quality data, IDMP, eCTD, FHIR/ePI, CDISC, W3C PROV)

| id | year | first author | title | venue | PDF |
|---|---|---|---|---|---|
| 494 | 2018 | Hume | CDISC SHARE: machine-readable CDISC standards | (PMC) | Y |
| 505 | 2018 | Kock-Schoppenhauer | Practical extension of provenance to healthcare data based on W3C PROV | Stud Health Technol Inform | Y |
| 490 | 2019 | Yu | FDA KASA: knowledge-aided assessment and structured applications (lifecycle quality knowledge) | Int J Pharm X | Y |
| 492 | 2020 | Algorri | Transitioning CMC content to structured data management | J Pharm Sci | Y |
| 496 | 2020 | Koshechkin | Implementing IDMP standards for a unified drug information space | Procedia Comput Sci | |
| 491 | 2021 | Ahluwalia | The future of CMC regulatory submissions: structured content and data | J Pharm Sci | Y |
| 488 | 2022 | Vorisek | FHIR for interoperability in health research: systematic review | JMIR Med Inform | Y |
| 489 | 2022 | Facile | CDISC standards for real-world data | JMIR Med Inform | Y |
| 500 | 2022 | Moen | G-Lens: FHIR International Patient Summary to personalise medication leaflets (Gravitate-Health) | Stud Health Technol Inform | Y |
| 501 | 2022 | Stojchevska | Electronic product information (ePI) in the EU | Maced Pharm Bull | Y |
| 502 | 2022 | Chronaki | Agile development of electronic product information standards | Stud Health Technol Inform | Y |
| 506 | 2022 | Frexia | The Common Provenance Model for distributed life-science processes | Stud Health Technol Inform | Y |
| 493 | 2023 | Anderson | Real-time algorithmic exchange of pharmaceutical quality data | Int J Pharm | |
| 499 | 2023 | Baker | HL7 FHIR to CDISC mapping implementation guide | J Soc Clin Data Manag | Y |
| 495 | 2024 | Karanikas | UNICOM test lab: implementing ISO IDMP across the EU | Stud Health Technol Inform | Y |
| 497 | 2024 | Jones | Adoption of IDMP standards in Europe | European Studies | Y |
| 498 | 2025 | Nagar | Transition to eCTD 4.0 | Int J Drug Regul Aff | Y |
| 503 | 2025 | Kirchsteiger | Medication leaflets via FHIR and an LLM question-answer app | Research Square | Y |
| 504 | 2026 | Lee | Regulatory readiness for electronic labelling replacing paper | JMIR | Y |

**F3. Post-approval: pharmacovigilance, label changes, real-world evidence** (the drug keeps changing after launch)

| id | year | first author | title | venue | PDF |
|---|---|---|---|---|---|
| 509 | 2016 | Dweik | Factors affecting patient reporting of adverse drug reactions: systematic review | Br J Clin Pharmacol | Y |
| 510 | 2017 | Mostaghim | Safety-related label changes after approval via expedited pathways (382 drugs) | BMJ | Y |
| 508 | 2018 | Beninger | Pharmacovigilance: an overview | Clin Ther | Y |
| 511 | 2018 | Shepshelovich | Post-marketing modifications of cancer drug labels | J Clin Oncol | |
| 514 | 2018 | Dreyer | Framework for regulatory use of real-world evidence | Ther Innov Regul Sci | Y |
| 513 | 2019 | Beaulieu-Jones | Use of real-world evidence in the regulatory process | Clin Pharmacol Ther | Y |
| 507 | 2020 | Alomar | Post-marketing surveillance through spontaneous ADR reporting | Ther Adv Drug Saf | Y |
| 515 | 2021 | Sienkiewicz | Direct patient reporting of ADRs in safety monitoring | IJERPH | Y |
| 512 | 2022 | Croteau | Sources of evidence triggering safety-related labelling changes (10 years) | Drug Safety | |

## Missing PDFs (17)

Blockchain papers, paywalled with no access from this network: Elsevier 414, 431, 432, 436;
Springer 429, 433; IEEE 456, 461, 464; Taylor & Francis 463; AHA 459.
Context papers (F): paywalled T&F 475, Elsevier 493, ASCO 511, Springer 512; open access
but blocked for automated download: JAMA Netw Open 468, Procedia Comput Sci 496 (ScienceDirect).
(437, 439 and 438 were downloaded by hand on 2026-10-20.)

## Excluded

- "A permissioned blockchain-based clinical trial service platform…" (BioMed Res Int 2021): **retracted**.
- Irving & Holden 2016/2017, "How blockchain-timestamped protocols could improve the
  trustworthiness of medical science" (F1000Research): **retracted by the authors**
  (all three versions) over methodological concerns. The protocol-timestamping idea
  survives in Nugent 2016 (455) and Benchoufi & Ravaud 2017 (454).
