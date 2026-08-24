# Ovarian Cancer Prognosis from Gene Expression (ML)

## Topic

**Predicting patient prognosis in ovarian cancer from tumor gene-expression profiles using machine learning.**

In plain terms: given how genes are turned on/off in a tumor sample, can we estimate how aggressive the disease is — e.g. risk of death or relapse — better than clinical factors alone?

---

## What this entails

### Problem
Ovarian cancer (especially high-grade serous) is often diagnosed late and has heterogeneous outcomes. Two patients with similar stage/grade can diverge sharply in survival. Gene expression captures molecular programs (proliferation, immune response, stromal signaling, etc.) that help explain that variability.

### Input
- **Features:** gene-expression values from microarray or RNA-seq (thousands of genes per patient)
- **Optional clinical covariates:** age, stage, grade, residual disease after surgery, BRCA status

### Output (prediction target)
One of:
1. **Risk group** — high vs low risk (classification; beginner-friendly)
2. **Survival time / hazard** — overall survival (OS), progression-free survival (PFS/PFI), with censoring (Cox / survival models; more rigorous)

### Typical workflow
1. Collect public cohorts with expression **and** follow-up (TCGA-OV, GEO series, curatedOvarianData)
2. Preprocess (normalize, filter genes, handle batch effects across platforms)
3. Split: train on one cohort, **externally validate** on others
4. Fit models (LASSO-Cox, random survival forest, XGBoost, simple neural nets)
5. Evaluate with C-index, Kaplan–Meier stratification, AUC for binary risk
6. Interpret: small gene signature + pathway context

### Scope for this project
- Disease focus: **ovarian cancer** (primarily high-grade serous)
- Method focus: supervised **prognosis / survival prediction** from expression
- Start simple (risk classification or LASSO-Cox signature), validate externally

### Out of scope (for now)
- Wet-lab validation
- Single-cell foundation models as the first deliverable
- Claiming clinical deployment readiness from retrospective public data alone

---

## Papers in the library — prestige ranking (most → least)

Prestige = **journal standing + lasting influence for ovarian expression/prognosis**, not “best methods to copy.” Foundational TCGA / Tothill / CLOVAR / JNCI meta-analyses outrank recent Frontiers-style signature papers even when the latter look more “ML-like.”

Library size: **37 papers** (metadata for all; **PDF on disk for 17**, missing for **20** — usually paywalled or bot-blocked, not “paper doesn’t exist”).

| Rank | PDF | Year | Venue | Paper | Why this rank |
|---:|:---:|---:|---|---|---|
| 1 | yes | 2011 | **Nature** | Integrated genomic analyses of ovarian carcinoma (TCGA) | Absolute top journal; defines TCGA-OV expression + survival resource almost every later paper uses |
| 2 | no | 2023 | **Cell** | Proteogenomic analysis of chemo-refractory HGSOC | Same top-journal tier; major multi-omics cancer paper (broader than expression-only prognosis) |
| 3 | no | 2009 | **Cancer Cell** | Gene signature predictive for outcome… (Mok / Bonome; MFAP2) | Top cancer journal *and* classic expression→survival signature study |
| 4 | no | 2012 | **JCI** | Prognostically relevant gene signatures… (CLOVAR / Verhaak) | Elite translational journal; canonical HGSOC subtype/prognosis signatures |
| 5 | yes | 2005 | **JCI** | Death-from-cancer signature… | Same elite venue; early expression/prognosis landmark (multi-cancer, not ovarian-only) |
| 6 | no | 2004 | **JCO** | Gene expression signature with independent prognostic significance (Spentzos) | ASCO flagship; early independent ovarian expression-prognosis landmark |
| 7 | no | 2010 | **JCO** | BRCAness gene-expression profile… chemo response & outcome (Konstantinopoulos) | ASCO flagship; highly cited expression profile linking HR repair phenotype to outcome |
| 8 | yes | 2008 | **PLoS Medicine** | Ovarian carcinoma subtypes are different diseases (Köbel / Huntsman) | Elite OA medical journal; landmark histotype paper that reframed all ovarian biomarker studies |
| 9 | no | 2014 | **JNCI** | Comparative meta-analysis of prognostic gene signatures (Waldron) | Top cancer journal; field’s “which signatures actually replicate?” paper |
| 10 | no | 2014 | **JNCI** | Risk prediction meta-analysis of 1525 patients (Riester) | Companion large-*n* JNCI meta-analysis; strong community recognition |
| 11 | no | 2014 | **JNCI** | Prognostic & therapeutic relevance of molecular subtypes (Konecny) | Mayo/UCLA validation of TCGA + Tothill subtypes with survival and chemo response; canonical companion to CLOVAR |
| 12 | no | 2020 | **Annals of Oncology** | Prognostic gene expression signature for HGSOC (Millstein) | ESMO flagship; large multi-cohort modern HGSOC signature |
| 13 | yes | 2013 | **Nature Communications** | ESTIMATE — tumour purity & stromal/immune scores (Yoshihara) | One of the most-cited expression-deconvolution methods; directly usable as features here |
| 14 | no | 2008 | **Cancer Research** | Survival signature in suboptimally debulked patients (Bonome / GSE26712) | AACR flagship; foundational survival cohort still used for external validation |
| 15 | no | 2008 | **Clinical Cancer Research** | Novel molecular subtypes… clinical outcome (Tothill / GSE9891) | Top AACR clinical journal; foundational subtypes + outcome cohort |
| 16 | no | 2012 | **Clinical Cancer Research** | 126-gene high-risk signature… antigen presentation (Yoshihara) | Same strong venue; influential high-risk / immune-presentation signature |
| 17 | no | 2013 | **Clinical Cancer Research** | Collagen-remodeling / TGF-β survival signature (Cheon) | Same venue; stroma/ECM biology often reused in later work |
| 18 | yes | 2021 | **Genome Medicine** | scRNA-seq refines HGSOC subtypes; cell subtypes influence survival (Olbrecht) | Strong OA genomics journal; modern single-cell follow-up to the Tothill/TCGA subtypes |
| 19 | yes | 2021 | **Genome Medicine** | Deep learning in cancer diagnosis, prognosis and treatment selection (Tran) | Same venue; well-regarded DL-for-prognosis methods review |
| 20 | yes | 2019 | **British Journal of Cancer** | FXYD5 upregulation… platinum resistance | Strong Nature Portfolio cancer journal; prognosis + resistance angle |
| 21 | yes | 2013 | **PLoS Computational Biology** | Network-based survival… subnetwork signatures (Net-Cox) | Respected computational-biology venue; methods value for survival ML |
| 22 | yes | 2018 | **PLoS Computational Biology** | Cox-nnet — ANN prognosis for high-throughput omics (Ching) | Same venue; the reference neural-net Cox model for omics data |
| 23 | yes | 2018 | **BMC Medical Research Methodology** | DeepSurv — deep Cox proportional hazards network (Katzman) | Standard methods journal; the canonical deep-learning survival baseline |
| 24 | no | 2017 | **Pacific Symposium on Biocomputing** | VAE latent space of cancer transcriptomes (Way & Greene) | Respected comp-bio venue; key representation-learning method for TCGA-scale expression data |
| 25 | no | 2013 | **Database (Oxford)** | curatedOvarianData | Lower “glamour,” but **high community value** — harmonized multi-cohort resource for this project |
| 26 | no | 2016 | **Oncotarget** | BRCA1/2 status, neoantigen load, TILs, PD-1/PD-L1 in HGSOC (Strickland) | Mid-tier OA; influential immune-prognosis link (Howitt/Rodig group) |
| 27 | yes | 2012 | **PLoS ONE** | Angiogenic mRNA/miRNA subtype of serous ovarian cancer (Bentink / Haibe-Kains) | Solid OA; the “angiogenic subtype” signature from the meta-analysis group |
| 28 | yes | 2011 | **PLoS ONE** | Survival from integrated genomic profiles (Mankoo, MSK) | Same tier; early integrative survival modeling worth mining for method ideas |
| 29 | yes | 2021 | **Cell Death Discovery** | Pyroptosis-related gene signature… | Nature Portfolio mid-tier; competent signature study, less field-defining |
| 30 | yes | 2025 | **BMC Cancer** | ADAMTS2… HGSOC | Established OA cancer journal; solid specialty paper |
| 31 | yes | 2025 | **Journal of Ovarian Research** | MLLT6 recurrence-related signature | Specialty OA; useful methods, modest prestige |
| 32 | yes | 2019 | **Journal of Cancer** | AGGF1 / MFAP4 chemoresistance | Mid/lower-tier OA |
| 33 | no | 2024 | **Translational Cancer Research** | Lactylation-related signature | Niche OA; lower standing |
| 34 | no | 2021 | **Frontiers in Oncology** | scRNA-seq + bulk immune risk model | Frontiers: high volume, generally lower perceived prestige |
| 35 | no | 2023 | **Frontiers in Genetics** | Ferroptosis review (ovarian) | Review + Frontiers |
| 36 | no | 2025 | **Frontiers in Oncology** | CSOARG ML model… | Same Frontiers tier; methods ideas only |
| 37 | yes | 2015 | **Oncology Letters** | Notch 10-gene recurrence signature | Lower-tier Spandidos journal |

### Rough “read first” order for *this* project
1. TCGA **Nature** (2011) — what the data is  
2. Tothill **CCR** (2008) — subtypes + GSE9891  
3. Bonome **Cancer Research** (2008) — GSE26712 survival setup  
4. CLOVAR **JCI** (2012) + Konecny **JNCI** (2014) — prognosis signatures done well, and validated  
5. Waldron / Riester **JNCI** (2014) — what replicates across cohorts  
6. Köbel **PLoS Medicine** (2008) — why histotype matters before any signature  
7. curatedOvarianData **Database** (2013) — how cohorts were harmonized  
8. Spentzos **JCO** / Mok **Cancer Cell** / Millstein **Annals** — signature design patterns  
9. ESTIMATE **Nat Commun** (2013) / Cox-nnet / DeepSurv / Way & Greene — method toolbox  
10. Then mid/lower ranks for modeling tricks only  

Full dataset mapping: `docs/ovarian-cancer-prognosis-datasets.md`  
PDFs/metadata: `papers/ovarian-cancer-prognosis-ml/`

## Workspace artifacts

| Item | Path |
|---|---|
| This brief | `docs/ovarian-cancer-prognosis-ml.md` |
| Dataset links (from papers) | `docs/ovarian-cancer-prognosis-datasets.md` |
| Paper PDFs / metadata | `papers/ovarian-cancer-prognosis-ml/` |
| BibTeX | `.research/references.bib` |

## Next steps

1. ~~Topic brief~~  
2. ~~Paper library (37 papers; 17 PDFs on disk; many Tier-A/B metadata-only)~~  
3. ~~Dataset link inventory~~  
4. ~~Download starter cohorts~~ → `datasets/ovarian-cancer-prognosis-ml/`  
5. Preprocess + build first survival / risk model (TCGA train → GSE9891/GSE26712 validate)
