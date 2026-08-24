# Top 3 Most Prestigious Papers — Ovarian Cancer Prognosis

Ranked by journal standing + lasting influence (see ranking in `ovarian-cancer-prognosis-ml.md`).

---

## 1. Integrated Genomic Analyses of Ovarian Carcinoma (TCGA, Nature 2011)

- **Paper:** https://doi.org/10.1038/nature10166
- **Datasets used:** TCGA-OV — ~489 high-grade serous tumors with mRNA expression, miRNA, DNA copy number, methylation, exome sequencing + clinical/survival follow-up
- **Dataset links:**
  - [GDC project TCGA-OV](https://portal.gdc.cancer.gov/projects/TCGA-OV)
  - [cBioPortal pan-cancer OV](https://www.cbioportal.org/study/summary?id=ov_tcga_pan_can_atlas_2018)
  - [PanCanAtlas CDR endpoints](https://gdc.cancer.gov/about-data/publications/pancanatlas)
  - Local copy: `datasets/ovarian-cancer-prognosis-ml/tcga-ov-xena-*`
- **Summary:** The foundational multi-omics characterization of HGSOC. Identified 4 expression subtypes (immunoreactive, differentiated, proliferative, mesenchymal), near-universal TP53 mutation, ~50% homologous-recombination defects (BRCA1/2 in ~20%), and NF1/RB1/CDK12 alterations. It defines the TCGA-OV expression + survival resource that virtually every later prognosis study trains on.

---

## 2. Proteogenomic Analysis of Chemo-Refractory HGSOC (Zhang et al., Cell 2023)

- **Paper:** https://doi.org/10.1016/j.cell.2023.07.004
- **Datasets used:** CPTAC-OV3 — proteogenomic profiling (whole-exome, RNA-seq, global proteome/phosphoproteome) of 242 chemo-refractory vs chemo-sensitive HGSOC tumors; raw sequencing controlled via dbGaP
- **Dataset links:**
  - [CPTAC Data Portal](https://cptac-data-portal.georgetown.edu/study-summary/S056)
  - [Proteomic Data Commons (PDC)](https://pdc.cancer.gov/pdc/)
- **Summary:** Major CPTAC multi-omics study linking protein/phospho-level pathways (chromosome instability signatures, glycolysis, immune microenvironment) to platinum refractoriness and survival. Goes beyond expression-only prognosis, but its proteogenomic predictors of chemo response are the current state of the art.

---

## 3. A Gene Signature Predictive for Outcome in Advanced Ovarian Cancer… MAGP2 (Mok/Bonome, Cancer Cell 2009)

- **Paper:** https://doi.org/10.1016/j.ccr.2008.10.018
- **Datasets used:** Discovery microarray cohort of microdissected advanced serous tumors, validated on independent public cohorts (incl. Tothill/AOCS GSE9891); primary discovery set not freely deposited
- **Dataset links:**
  - [GSE9891 (validation cohort)](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE9891)
- **Summary:** Classic expression→survival signature study. Derived and externally validated a prognostic signature for advanced serous tumors, then singled out MAGP2 as a survival factor: it promotes tumor-cell and endothelial survival via αvβ3 integrin, and its expression correlates with microvessel density — tying prognosis to angiogenesis. Canonical early proof that ovarian expression signatures carry outcome information.

---

**Note:** Only paper #1's dataset is fully mirrored locally (`datasets/ovarian-cancer-prognosis-ml/tcga-ov-xena-*`). Papers #2 and #3 have no PDF on disk (paywalled); metadata is in `.research/library.db`.
