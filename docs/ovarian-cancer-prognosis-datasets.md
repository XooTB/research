# Dataset leads from the paper library

Extracted from abstracts/PDFs in `papers/ovarian-cancer-prognosis-ml/` (17 papers with PDFs; 309 findings in `docs/extracted/ovarian-cancer-prognosis-ml-datasets.csv`).

**Status:** **23 datasets downloaded** under `datasets/ovarian-cancer-prognosis-ml/` (~2 GB), all verified.

## Most reused (priority)

| Dataset | Type | Survival / clinical? | Obtainable? | Link |
|---|---|---|---|---|
| **TCGA-OV** | RNA-seq + clinical | Yes (prefer PanCanAtlas CDR endpoints) | Yes (open expression/clinical) | [GDC project](https://portal.gdc.cancer.gov/projects/TCGA-OV) · [cBioPortal pan-cancer OV](https://www.cbioportal.org/study/summary?id=ov_tcga_pan_can_atlas_2018) · [CDR / PanCanAtlas](https://gdc.cancer.gov/about-data/publications/pancanatlas) |
| **curatedOvarianData** | Harmonized multi-cohort ExpressionSets | Yes (OS / relapse curated) | Yes (Bioconductor) | [Bioconductor package](https://bioconductor.org/packages/curatedOvarianData/) · [paper](https://doi.org/10.1093/database/bat013) |
| **GSE9891** (Tothill / AOCS) | Microarray | Yes | Yes | [GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE9891) |
| **GSE32062** | Microarray | Yes | Yes | [GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE32062) |
| **GSE30161** | Microarray | Yes | Yes | [GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE30161) |
| **GSE26712** | Microarray | Yes | Yes | [GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE26712) |

Also useful from CLOVAR / TCGA publications: [GDC ov_exp (CLOVAR resources)](https://gdc.cancer.gov/about-data/publications/ov_exp).

## Other cohorts cited but not downloaded

| Accession | Link | Notes |
|---|---|---|
| E-MTAB-386 | [ArrayExpress / BioStudies](https://www.ebi.ac.uk/biostudies/arrayexpress/studies/E-MTAB-386) | In curatedOvarianData — use via Bioconductor |
| EGAS00001004987 | [EGA](https://ega-archive.org/studies/EGAS00001004987) | Olbrecht scRNA raw reads — controlled access |

(All other GEO cohorts cited across the 17 PDFs are now downloaded locally — see table above.)

## Downloaded locally

| Local folder | Role | Approx. n |
|---|---|---|
| `tcga-ov-xena-rna-seq-hiseqv2` | Train expression | 308 × 20,530 genes |
| `tcga-ov-xena-clinical-matrix` | Train survival/clinical | 630 rows (join to expression) |
| `gse9891-…` | External validate | 285 |
| `gse26712-…` | External validate | 195 (filter normals) |
| `gse32062-gpl6480-…` | Validate (PFS) | 260 |
| `gse49997-…` | Validate | 204 |
| `gse17260-…` | Validate (PFS) | 110 |
| `gse26193-…` | Validate (OS+PFS) | 107 |
| `gse14764-…` | Validate (OS) | 80 |
| `gse18520-…` | Validate | 63 |
| `gse30161-…` | Small validate | 58 |
| `gse13876-…` | Validate (curatedOvarianData cohort) | 415 |
| `gse140082-…` | Validate — **large**, from pyroptosis-signature paper | 380 |
| `gse53963-…` | Validate (MLLT6 recurrence paper) | 174 |
| `gse51088-…` | Validate (curatedOvarianData cohort) | 172 |
| `gse63885-…` | Chemoresistance / prognosis (AGGF1 paper) | 101 |
| `gse8842-…` | Recurrence-signature cohort | 83 |
| `gse19161-…` | Bentink validation cohort | 61 |
| `gse51373-…` | Platinum-response cohort (small) | 28 |
| `gse131978-gpl570-…` + `gse131978-gpl96-…` | FXYD5 paper cohort (2 platforms) | 14 + 25 |
| `gse14407-…` | Classic early cohort (small) | 24 |
| `gse154600-…` | scRNA-seq immune cohort (matrix only; raw in GEO suppl) | 5 |

## Suggested analysis setup

1. **Train:** TCGA-OV Xena expression + clinical (`vital_status` / `days_to_*`)  
2. **External validate:** GSE9891 + GSE26712  
3. **Extra checks:** GSE32062, GSE26193, GSE17260  

## Paper → dataset map (high level)

| Paper (year) | Datasets mentioned | Have locally? |
|---|---|---|
| TCGA Nature (2011) | TCGA-OV | yes |
| Köbel PLoS Med (2008) | Tissue microarrays (not GEO) | n/a |
| Mankoo PLoS ONE (2011) | TCGA-OV + MSK cohort (not deposited) | TCGA only |
| Bentink PLoS ONE (2012) | E-MTAB-386, GSE26712, GSE17260, GSE18520, GSE14764, GSE19161, GSE13876 | yes (E-MTAB-386 via Bioconductor) |
| Verhaak CLOVAR (2012) | TCGA-OV (+ external validation set in paper) | yes |
| ESTIMATE Nat Commun (2013) | TCGA + normal-tissue references | TCGA only (rest out of scope) |
| curatedOvarianData (2013) | Multi-cohort package (GSE* + TCGA) | R package |
| Zhang network survival (2013) | TCGA-OV, GSE26712, GSE9899* | yes |
| Chen Notch 10-gene (2015) | curatedOvarianData, GSE9891, GSE30161, TCGA-OV | yes |
| Cox-nnet (2018) | 10 TCGA RNA-seq cohorts (incl. OV) | TCGA-OV yes |
| DeepSurv (2018) | METABRIC etc. (non-ovarian) | n/a |
| Zhao AGGF1/MFAP4 (2019) | TCGA-OV, GSE9891, GSE32062, GSE51373, GSE63885, cBioPortal | yes |
| Tassi FXYD5 (2019) | curatedOvarianData, GSE9891, GSE17260, GSE26193, GSE30161, GSE49997, GSE131978 | yes |
| Ye pyroptosis (2021) | TCGA-OV, GTEx, GSE140082 | yes (GTEx not needed) |
| Olbrecht Genome Med (2021) | EGA scRNA (EGAS00001004987), curatedOvarianData, E-MTAB-386, TCGA-OV, GSE9891, GSE26712, GSE30161 | bulk yes; scRNA gated |
| sc/bulk immune risk model (2021) | TCGA-OV, GSE154600 | yes |
| Tran DL review (2021) | Methods review | n/a |
| Lactylation signature (2024) | TCGA-OV | yes |
| MLLT6 recurrence (2025) | TCGA-OV, GSE32062, GSE14407, GSE8842, GSE53963 | yes |
| CSOARG ML model (2025) | TCGA-OV (+ single-cell sources in paper) | yes |
| ADAMTS2 HGSOC (2025) | TCGA-OV, GSE32062 | yes |

\*GSE9899 in PDFs is a typo for GSE9891 — no such series exists.

## Not freely downloadable / lower priority for now

- **EGAS00001004987** — Olbrecht 2021 scRNA-seq raw reads (EGA **controlled access**; processed data via their pipelines)
- Controlled-access TCGA raw sequencing BAM/CRAM (not needed for expression prognosis)
- Some CPTAC proteogenomic raw files (paper registered; expression subset may still be public via CPTAC/GDC portals)
- Paywalled paper PDFs (metadata kept; datasets above are still mostly public)
- `GSE9899` in two PDFs is likely a typo for **GSE9891** (already downloaded); no such GEO series
- ESTIMATE paper validation sets (GSE1133, GSE10797, …) are normal-tissue references, out of scope
- E-MTAB-386: already inside the curatedOvarianData Bioconductor package; skip raw download

## Next step

Pick the starter stack above, then download + verify with the datasets skill.
