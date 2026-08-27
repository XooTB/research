# Ovarian cancer molecular prognosis: data audit and opportunity map

**Date:** 25 August 2026  
**Scope:** every dataset under `datasets/ovarian-cancer-prognosis-ml/`, the two existing Colab models, and the original product idea (tumor genome → future risk).  
**Rule used here:** an endpoint exists only if a column (or a reconstructable pair of columns) is on disk. Paper claims without a local field are listed as *not in hand*.

This document re-evaluates *what kind of prognosis is actually worth building*, given the files we have, not given a wishlist.

---

## 1. Verdict

The original plan was a model that “looks at the gene sequence of the tumor and accurately predicts future risk of death and complications.”

Three facts from the library contradict that plan as stated:

1. **We do not have gene sequence.** We have **bulk gene-expression** (microarray or RNA-seq): abundance of RNA, not DNA letters. Sequence-like information (somatic mutations, copy-number, HRD) exists at GDC/TCGA for some of the same patients, but those files were never downloaded.
2. **Individual, accurate death prediction from expression is not a realistic target.** On the only RNA-seq training set we have (TCGA-OV HiSeqV2, 303 patients with usable overall survival), a LASSO-Cox model of 20,530 genes did **not** beat age + stage + residual disease (C-index 0.605 vs 0.615). On two external microarray cohorts it fell to 0.56 and 0.53. That is the same range the 2014 JNCI meta-analyses reported for this field. A product that promises “accurate” death risk from a tumor transcriptome would be overselling what this modality contains.
3. **Complication endpoints are absent.** There are no labels for bowel obstruction, VTE, fistula, ascites requiring procedures, neuropathy, nephrotoxicity, ICU stay, or any other non-cancer-specific morbidity.

What the library *does* support is narrower and more honest:

- **Relative risk stratification** on overall survival and (better) progression-free survival, always compared against clinical covariates.
- **Platinum-response / platinum-free interval**, which is closer to tumor biology than death, is clinically used, and is present in several cohorts.
- **One genuine predictive (treatment-benefit) experiment:** bevacizumab vs standard therapy in GSE140082.
- **A few intermediate phenotypes** that are not prognosis themselves but are usable as tasks or covariates: residual disease, TCGA expression subtype, BRCA1 mutation (one cohort), histotype.

The rest of this document is the evidence for that re-evaluation, then an endpoint-by-endpoint plan that says *what data each task needs* and *whether we have it*.

---



## 2. Sequence vs expression (this is not a wording issue)


| What someone might mean                               | What we have locally                                                                                                                                                                                                                          | Consequence                                                                               |
| ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| DNA sequence of the tumor (WGS/WES/gene panel)        | **No** FASTQ, BAM, VCF, or MAF                                                                                                                                                                                                                | Cannot take “a tumor’s gene sequence” as input                                            |
| Somatic mutations (TP53, BRCA1/2, CDK12, NF1, RB1, …) | Clinical matrix has **IDs** pointing at TCGA mutation tracks for 316/630 samples (186 of the 304 HiSeq primaries). The mutation tables themselves are **not** on disk                                                                         | Doable after a GDC MAF download; not doable now                                           |
| Copy-number / CCNE1 amplification / HRD genomic scar  | GISTIC IDs for 579/630 samples; no GISTIC matrix downloaded                                                                                                                                                                                   | Same: pointer, not data                                                                   |
| Germline BRCA                                         | Only **GSE63885** (`brca1 mutation`, 98/101 samples; 28 mutation carriers, mostly 5382insC). TCGA clinical matrix has **no** BRCA field. `_PANCAN_CNA_PANCAN_K8 = BRCA-LUAD+` is a pan-cancer copy-number *cluster name*, not a BRCA mutation | Expression-BRCAness is possible on one small cohort unless we fetch TCGA BRCA annotations |
| Transcriptome (which genes are on, and how much)      | **Yes:** TCGA HiSeqV2 (20,530 genes × 308 samples) plus 20 GEO microarray series                                                                                                                                                              | This is the actual feature modality                                                       |
| Proteome / phospho                                    | RPPA IDs for 436/630 TCGA samples; no RPPA table. CPTAC HGSOC (Cell 2023) not downloaded                                                                                                                                                      | Not available                                                                             |
| Single-cell                                           | GSE154600 is 5 omental tumors (matrix only). Olbrecht scRNA is EGA-controlled                                                                                                                                                                 | Not a modelling resource                                                                  |


A transcriptome model answers: *given how this tumor is behaving now (proliferation, stroma, interferon, angiogenesis), how will the patient do?*  
A sequence model answers: *given which DNA lesions this tumor carries, how will it respond to DNA-damaging or homologous-recombination-targeted therapy?*

Those are different products. The files on disk only support the first. The second is a real opportunity **after** downloading public TCGA MAF + GISTIC (see §8). It is not what we can train this week.

RNA-seq and microarray also do **not** give a future clinical “risk factor” as a single number a clinician can treat as a probability of death. At best they give a **rank** (higher vs lower hazard than similar patients), and historically that rank is only modestly better than stage and residual disease — sometimes not better at all.

---



## 3. What “prognosis” can mean in ovarian cancer

Clinically, “prognosis” is not one variable. The endpoints below are the ones the field actually uses. Later sections map each to our files.

**Time-to-event (need time + censoring indicator)**


| Endpoint                        | Meaning                                         | Why it matters                                                                                              |
| ------------------------------- | ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Overall survival (OS)           | Time from diagnosis/surgery to death, any cause | Regulatory / literature default. Diluted by post-progression therapy, non-cancer death, and short follow-up |
| Disease-specific survival (DSS) | Death from ovarian cancer only                  | Cleaner than OS; almost never in GEO                                                                        |
| Progression-free survival (PFS) | Time to recurrence, progression, or death       | More events, closer to the tumor’s biology, still standard                                                  |
| Platinum-free interval (PFI)    | Time from last platinum to progression          | Defines “platinum resistant” (<6 months) vs sensitive. Actionable                                           |
| Disease-free survival (DFS)     | Time to relapse after complete resection        | Relevant after optimal debulking / early stage                                                              |


**Binary / ordinal (need a label; time optional)**


| Endpoint                                         | Meaning                                                                                         |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| Horizon mortality                                | Dead vs alive at 1 / 3 / 5 / 10 years. Patients censored before the horizon **must be dropped** |
| Long- vs short-term survivor                     | e.g. OS <2 years vs >8–10 years, excluding the middle                                           |
| Primary therapy outcome                          | RECIST-style CR / PR / SD / PD after first-line chemo                                           |
| Platinum sensitivity class                       | Resistant / partially sensitive / sensitive (GCIG, usually by PFI)                              |
| Residual disease                                 | Optimal vs suboptimal debulking (or R0 / 1–10 mm / >20 mm)                                      |
| Relapse (yes/no)                                 | Especially in early-stage disease, where OS events are rare                                     |
| Treatment *benefit* (predictive, not prognostic) | Does this patient gain from adding drug X? Needs a treated and a control arm                    |


**Not prognosis, but often confused with it**

- Histotype (serous vs clear-cell vs endometrioid vs mucinous) — diagnostic, and a confounder if mixed into a survival model.
- TCGA/Tothill expression subtype — intermediate phenotype; prognostic only insofar as mesenchymal/proliferative groups do worse.
- Tumor vs normal — classification, not outcome.

**Complications and other product-like endpoints** (bowel obstruction, VTE, fistula, toxicities, CA125 kinetics, secondary cytoreduction, PARP-inhibitor response, HIPEC benefit): **none of these exist in the local files.** They remain listed in §7 so they are not forgotten.

---



## 4. Library at a glance

**23 dataset folders** under `datasets/ovarian-cancer-prognosis-ml/` (~2 GB). One empty shell (`gse131978-ovarian-expression-series-matrix`). One expression-only matrix (`tcga-ov-xena-rna-seq-hiseqv2`). One clinical-only matrix (`tcga-ov-xena-clinical-matrix`). Twenty GEO series with expression + sample metadata.

**What has already been modelled**


| Run                                          | Task                             | Train                                                               | Internal                                                                                                                                                  | External                                                                                                                      |
| -------------------------------------------- | -------------------------------- | ------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `20260824T195053Z-tcga-ov-lasso-cox`         | OS, LASSO-Cox                    | TCGA HiSeq 303 pts, 182 deaths, median follow-up 951 days           | Expression C-index **0.605**; clinical-only **0.615**; 3-year OS AUC 0.629; KM log-rank p = 1.2×10⁻⁵ (optimistic: same cohort used to pick the signature) | GSE26712 185 pts: C-index **0.560**, log-rank p = 0.68 (no separation). GSE14764 80 pts: C-index **0.530**, log-rank p = 0.88 |
| `20260825T034757Z-tcga-ov-3yr-mortality-clf` | Dead within 3 years, elastic-net | Same 303; 80 censored-before-3y dropped → 223 evaluable, 42.6% dead | Best = expression + clinical ENET, OOF AUC **0.695** (clinical LR 0.646; expression-only 0.681)                                                           | GSE26712 169 evaluable: AUC **0.615**. GSE14764 48 evaluable: AUC **0.505**                                                   |


Interpretation, which should drive the rest of the project:

- On TCGA, **clinical covariates already carry most of the OS signal**.
- Expression adds a little internally (especially at a 3-year horizon) and **does not travel** to GSE14764. GSE26712 keeps a weak rank (AUC 0.61) but the Cox signature does not stratify KM curves.
- GSE14764 is a bad OS validator (21 deaths / 80 patients, mixed histotypes). Treating a coin-flip there as “the model failed” would be over-reading; treating 0.56 on GSE26712 (129 deaths) as “it worked” would also be over-reading.
- The next OS attempt should not be “a bigger neural net on the same 303 patients.” It should be **better labels, more patients, HGSOC-only subsets, and validators with enough events** (GSE32062, GSE140082, GSE53963, GSE9891 once survival is attached). Even then, the literature ceiling for expression-only OS is roughly C-index 0.60–0.65.

**Structural limits that apply to every task below**

- **p ≫ n.** Thousands of genes, hundreds of patients. Without penalization and **external** validation, anything will look good.
- **Platforms do not share a numeric scale.** RNA-seq, Affymetrix U133A, U133 Plus 2.0, Agilent 4×44k, ABI, Illumina, and two-color custom arrays cannot be concatenated as if they were one matrix. Models must be trained on gene symbols, then applied after per-cohort normalization, or trained as ranks/signatures.
- **Histotype mixing silently invents a prognostic gene.** Clear-cell, mucinous, endometrioid, and serous are different diseases (Köbel, *PLoS Medicine* 2008). Several GEO series mix them. HGSOC-only subsets are the scientifically defensible analysis.
- **Batch = cohort.** “Independent validation” on another GEO series is the real test; k-fold CV on TCGA is not.

---



## 5. Cohort catalog

Counts below are from the series matrices / phenotype CSVs / Xena clinical matrix on disk (August 2026). “Usable n” means samples that have the stated endpoint **and** are tumors (normals excluded). Histotype-restricted numbers are given when the column exists.

### 5.1 Training-scale resources



#### TCGA-OV (Xena HiSeqV2 + clinical matrix)


| Item                                                   | Value                                                                                                                                                                                                                                        |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Expression                                             | 20,530 genes × **308** samples (`HiSeqV2`)                                                                                                                                                                                                   |
| Clinical                                               | **630** samples × 102 fields (`OV_clinicalMatrix`)                                                                                                                                                                                           |
| Overlap                                                | all 308 expression samples match clinical IDs                                                                                                                                                                                                |
| Barcode primary (`-01`)                                | 304                                                                                                                                                                                                                                          |
| `sample_type = Primary Tumor`                          | 303 (plus 5 recurrent; 12 normals live in the clinical file only)                                                                                                                                                                            |
| Usable OS (time ≥ 1 day, vital status LIVING/DECEASED) | **303** primaries (182 deaths, 121 censored). Median time 951 days (range 8–5481). Dropped primary: `TCGA-04-1357-01` (LIVING, both day fields empty). Including the 4 recurrent `-02` samples, 307/308 HiSeq barcodes have constructible OS |
| Histology                                              | ovarian serous cystadenocarcinoma (HGSOC by construction)                                                                                                                                                                                    |
| Stage (HiSeq primary)                                  | IIIC 221, IV 38, IIIA–B 21, II 21, IC 1, missing 2                                                                                                                                                                                           |
| Grade                                                  | G3 261, G2 33, other/missing 10                                                                                                                                                                                                              |
| Residual disease (`tumor_residual_disease`)            | 267/304: 1–10 mm 134, no macroscopic 58, >20 mm 52, 11–20 mm 23                                                                                                                                                                              |
| Primary therapy outcome                                | 223/304: CR 150, PR 33, SD 18, PD 22, missing 81                                                                                                                                                                                             |
| Days to new tumor event                                | 175/304 have a time; the binary `new_tumor_event_after_initial_treatment` is filled for only 32/304 (YES 23, NO 9). A strict YES/NO+time proxy is ~183 samples with almost no true censoring — **not** a proper PFI                          |
| 3-year mortality evaluable                             | 223 (95 dead by 3 years; 80 dropped because censored earlier) — matches the classifier notebook                                                                                                                                              |
| Age                                                    | 304/304                                                                                                                                                                                                                                      |
| BRCA / HRD / mutations **as data**                     | not in this file; mutation *IDs* for 186/304                                                                                                                                                                                                 |
| Other omics **as data**                                | not downloaded. IDs exist: Affy U133A 593/630, GISTIC 579, methyl27 616, miRNA 485, RPPA 436                                                                                                                                                 |


**Missing relative to a modern TCGA survival analysis:** the PanCanAtlas CDR table (Liu et al., standardized OS / DSS / DFI / PFI) was not downloaded. PFI constructed from `days_to_new_tumor_event_after_initial_treatment` will under-count early progressors (only 7 of 175 new-tumor times are <180 days — that is not biologically plausible as a complete platinum-resistance rate).

**Also not downloaded, but larger:** TCGA-OV Affymetrix U133A expression (~565–593 tumors). Using only HiSeq throws away almost half the TCGA OS events.

#### GSE140082 (Kommoss / ICON7 gene-expression, Illumina GPL14951)

Largest GEO cohort, and the only one with a **randomized treatment arm**.


| Field                                                 | n                                                                       |
| ----------------------------------------------------- | ----------------------------------------------------------------------- |
| Samples                                               | 380 FFPE ovarian cancers                                                |
| OS time + event (`final_ostm`, `final_osid`)          | 380 (96 deaths). Time range 1–1326, median 770 — **days**, immature OS  |
| PFS time + event (`final_pfstm`, `final_pfsid`)       | 380 (235 progressions). Median 552 days                                 |
| Treatment                                             | bevacizumab 199, standard 181                                           |
| Debulking                                             | optimal 290, sub-optimal 88, inoperable 2                               |
| FIGO                                                  | I 20, II 31, III 266, IV 63                                             |
| Histology                                             | serous 277, other 103                                                   |
| Grade                                                 | high 281, low 74, NA 25                                                 |
| Serous + high-grade subset                            | **212** (56 OS events, 138 PFS events; bev 109 / standard 103)          |
| TCGA-style subtype (`t1_cluster_name`)                | immunoreactive 124, proliferative 97, differentiated 86, mesenchymal 73 |
| Age                                                   | 380/380                                                                 |
| Manuscript analysis subset (`manuscript_analysis359`) | 359 of 380                                                              |


PFS<180 days with event: only **11/380**. This cohort is excellent for PFS and for **bevacizumab interaction**. It is a poor platinum-resistance set. FFPE Illumina DASL (GPL14951) — another platform family, not Affy/Agilent.

#### GSE32062-GPL6480 (Yoshihara / Japanese HGSOC, Agilent)

Cleanest dedicated HGSOC survival series after TCGA.


| Field                                           | n                                        |
| ----------------------------------------------- | ---------------------------------------- |
| Samples                                         | **260**, all labelled high-grade serous  |
| OS months + death                               | 260 (121 deaths). Time 1–128 months      |
| PFS months + recurrence                         | 260 (193 recurrences). Time 1–119 months |
| Surgery                                         | suboptimal 157, optimal 103              |
| All received platinum **and** taxane            | 260/260                                  |
| Grade                                           | 2: 131, 3: 129                           |
| Stage                                           | IIIa 4, IIIb 20, IIIc 180, IV 56         |
| PFS<6 months (platinum-resistant proxy)         | **24**                                   |
| PFS≥12 months and no recurrence (sensitive-ish) | **66**                                   |




#### GSE9891 (Tothill / AOCS, Affymetrix GPL570)

The cohort every ovarian signature paper wants as a validator. **Expression is here; survival is not.**


| Field                     | n                                                     |
| ------------------------- | ----------------------------------------------------- |
| Samples                   | 285                                                   |
| Primary site              | ovary 243, peritoneum 34, fallopian tube 8            |
| Type                      | malignant 267, LMP 18 (exclude LMP from HGSOC models) |
| Subtype                   | serous/papillary serous 264, endometrioid 20, adeno 1 |
| Stage / grade             | present (IIIC 187, grade 3: 161)                      |
| OS / PFS / residual / age | **absent from the GEO series matrix**                 |


The existing OS notebook already recorded this gap. Survival for these patients lives in the Tothill paper supplements and in Bioconductor **curatedOvarianData**. Until that is attached, GSE9891 is a histotype/stage/grade expression set, not a prognosis set.

### 5.2 Solid OS + PFS GEO cohorts


| Cohort                  | Platform          | Tumors                                                        | OS                                                                                                         | PFS / DFS                                       | Residual                               | Notes                                                                                                        |
| ----------------------- | ----------------- | ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ----------------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **GSE26712** Bonome     | GPL96 U133A       | 185 tumors (+10 HOSE normals)                                 | 185 times in years; status DOD 129 / AWD 24 / NED 32                                                       | no                                              | optimal 90, suboptimal 95              | Late-stage high-grade by description. Already used as OS validator. Treat DOD as event, AWD+NED as censored  |
| **GSE17260** Yoshihara  | GPL6480 Agilent   | 110 serous                                                    | 110 months, 46 deaths                                                                                      | 110 months, 76 recurrences                      | optimal 57, not optimal 53             | Same platform family as GSE32062 — natural paired validator                                                  |
| **GSE26193** Mateescu   | GPL570            | 107 mixed histotype; **79 serous**                            | 107 (76 deaths); serous 60 deaths                                                                          | 107 (80 events); serous 63                      | no                                     | Times in years (up to 20). Restrict to serous for HGSOC models                                               |
| **GSE49997** Pils       | GPL2986 ABI       | 204 (10 marked `excluded=yes`); **194 usable**, 171 serous    | 194 months, 57 deaths (48 in serous)                                                                       | 194, 124 events (108 in serous)                 | residual tumor Yes 57 / No 137         | Also: age, peritoneal carcinomatosis, molecular subclass 1/2. Short OS follow-up (max 49 months)             |
| **GSE14764** Denkert    | GPL96             | 80 mixed; **68 serous**                                       | 80 months (7–73), **21 deaths** (19 serous)                                                                | no                                              | 0: 50, 1: 26 (4 missing)               | Underpowered OS validator — our 3-year AUC 0.50 is expected                                                  |
| **GSE30161** Ferriss    | GPL570 FFPE       | 58 mixed; **47 serous**                                       | 58 days, 36 deaths                                                                                         | PFI days 58; relapse 48 yes / 6 no / 4 unknown  | optimal 26, sub-optimal 30 (2 missing) | **Best small chemo-annotated set:** agent, CR/PR/SD/PD, PFI, OS. FFPE                                        |
| **GSE63885** Lisowska   | GPL570            | 101 mixed; **73 serous**                                      | 75 with OS days (70 serous); last status DOD 66 / AWD 4 / NED 5 / NA 26                                    | DFS days for 75                                 | R0 15, R1 38, R2 22 (26 NA)            | **Best platinum-class labels** (see §5.3). Also BRCA1 + TP53                                                 |
| **GSE19161**            | GPL9717           | 61                                                            | 61 months, 32 events / 29 censored                                                                         | no                                              | no                                     | **Only 658 probes** — skip as a gene-signature validator                                                     |
| **GSE18520** Mok/Bonome | GPL570            | 53 late high-grade serous (+10 OSE)                           | `surv data` 5–150, 12 marked `(A)` = alive, 41 unmarked                                                    | no                                              | no                                     | Usable only after adopting the paper’s coding (unmarked = dead, units almost certainly months). Messy        |
| **GSE53963**            | GPL6480 two-color | 174 serous                                                    | `time_fu_months` + `vital_status` on **channel 2**: 153 dead, 21 alive                                     | no                                              | optimal 123, sub-optimal 48, unknown 3 | Phenotype is on ch2 (easy to miss). 14 samples carry a TCGA barcode — drop those if used beside TCGA         |
| **GSE51088**            | GPL7264 two-color | 172 mixed (15 normal, 5 benign, 12 borderline, 140 malignant) | ch2 `follow up months` + `patient status`. Serous **primary malignant 100** (80 dead, 19 alive, 1 unknown) | disease status Free/Not Free (not a proper PFS) | no                                     | Must subset malignant primary. Mixed histotype. Two-color. **23 samples carry a TCGA id** — drop beside TCGA |




#### GSE13876 (Crijns, custom two-color GPL7759)

415 arrays from **157 unique patients** (dye-swaps / replicates; arrays-per-patient 2–6; phenotype consistent within patient). Advanced-stage serous by source name. Fields: `status` 0/1 (113 events / 44 censored at patient level), `fumnd` 1–234 (months from surgery), `age`.

GEO’s own description: **status 1 = death due to ovarian cancer**; **status 0 = end of follow-up or death unrelated to OC**. That is closer to **disease-specific survival** than all-cause OS. Do not mix it with TCGA `vital_status` without saying so.

This is a real survival cohort, but GPL7759 is a custom array. Gene mapping will be painful and cross-platform overlap will be thin. Treat as optional, not as a default validator.

### 5.3 Chemo / platinum-labelled cohorts


| Cohort                       | Label                                                                                                                                                                             | n (all / serous where known)           | Survival too?    |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- | ---------------- |
| **GSE63885**                 | Platinum: resistant / moderately sensitive / highly sensitive (PFI cut at 180 and 732 days). Serous: 32 / 26 / 12 (3 NA). First-line RECIST: CR 47, PR 13, SD 3, P 7 among serous | 101 / 73                               | Yes              |
| **GSE51373**                 | chemotherapy sensitive 16, resistant 12                                                                                                                                           | 28 HGSOC                               | No               |
| **GSE131978** GPL96 + GPL570 | platinum sensitive / partially sensitive / resistant. Combined non-missing: 12 / 6 / 19. Also long- vs short-term survivor in the sample titles                                   | 25 + 14 = 39 HGSOC, **two Affy chips** | No time-to-event |
| **GSE30161**                 | CR 32, PR 22, PD 1, unknown 3 (serous CR 26 / PR 18 / PD 1)                                                                                                                       | 58 / 47                                | Yes              |
| **TCGA HiSeq**               | primary_therapy_outcome_success: CR 150, PR 33, SD 18, PD 22                                                                                                                      | 223 labelled of 304                    | Yes              |
| **GSE154600**                | chemo response resistant 2 / sensitive 2 / refractory 1                                                                                                                           | **5** scRNA                            | No               |


GSE32062 / GSE17260 / GSE140082 can supply a **PFS-based proxy** (progression by 6 months) but the resistant class is small (24, 15, and 11 respectively). Do not pretend those are equivalent to GSE63885’s curated platinum classes.

### 5.4 Special-purpose / weak-for-prognosis


| Cohort                     | n                        | What it is                                                                                                                                          | Prognosis use                                                                    |
| -------------------------- | ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **GSE8842**                | 83, **all FIGO stage I** | OS days, PFS days, relapsed 21/83, cancer death 13. Histotype mixed; 15 borderline. Invasive 68 (18 relapsed, 13 cancer deaths). Serous invasive 24 | Early-stage **relapse**, not late-stage OS. Underpowered if restricted to serous |
| **GSE14407**               | 24                       | 12 OSE vs 12 LCM serous tumor                                                                                                                       | Diagnostic, zero follow-up                                                       |
| **GSE154600**              | 5                        | scRNA omental HGSOC                                                                                                                                 | Ignore for supervised prognosis                                                  |
| empty `gse131978-…` folder | 0                        | leftover slug                                                                                                                                       | Ignore                                                                           |




### 5.5 Platform map (why pooling is hard)


| Platform                          | Cohorts                                                                                           | Approx. tumor n with some outcome                          |
| --------------------------------- | ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| RNA-seq HiSeqV2                   | TCGA-OV                                                                                           | 303 OS                                                     |
| Affymetrix U133A (GPL96)          | GSE26712, GSE14764, GSE131978-gpl96                                                               | ~185+80+25                                                 |
| Affymetrix U133 Plus 2.0 (GPL570) | GSE9891 (no OS yet), GSE18520, GSE26193, GSE30161, GSE63885, GSE14407, GSE51373, GSE131978-gpl570 | largest Affy family                                        |
| Agilent GPL6480                   | GSE32062, GSE17260, GSE53963                                                                      | 260+110+174                                                |
| Illumina GPL14951                 | GSE140082                                                                                         | 380                                                        |
| ABI GPL2986                       | GSE49997                                                                                          | 194                                                        |
| Two-color / custom                | GSE13876, GSE51088, GSE8842, GSE19161                                                             | GSE19161 is 658 probes — skip; others need careful mapping |


A model trained on TCGA RNA-seq and tested on GPL96 (GSE26712) is already a cross-platform test. That is partly why external C-index collapsed. It is also why **within-platform** validation (e.g. train GSE32062, test GSE17260, both Agilent) is a cleaner scientific experiment than another TCGA→Affy leap.

---



## 6. Cross-cohort endpoint matrix

Legend: **Y** = usable time+event or a clean label on disk; **p** = partial / reconstructable / messy; **—** = not present; **n** = too small to be a training set.


| Cohort     | n tumors           | OS           | PFS/PFI      | Chemo/platinum                        | Residual | Stage                 | Grade                 | Age | Histotype     | Other distinctive labels                     |
| ---------- | ------------------ | ------------ | ------------ | ------------------------------------- | -------- | --------------------- | --------------------- | --- | ------------- | -------------------------------------------- |
| TCGA HiSeq | 303–304            | Y            | p            | Y (RECIST-like, PD n=22)              | Y        | Y                     | Y                     | Y   | serous        | new-tumor time 175; omics IDs only           |
| GSE140082  | 380                | Y (immature) | Y            | — (trial therapy, not platinum class) | Y        | Y                     | Y                     | Y   | mixed         | **bevacizumab vs standard**; TCGA subtypes   |
| GSE32062   | 260                | Y            | Y            | proxy via PFS                         | Y        | Y                     | Y                     | —   | HGSOC         | all platinum+taxane                          |
| GSE9891    | 285                | —            | —            | —                                     | —        | Y                     | Y                     | —   | mostly serous | **need curated survival**; 18 LMP            |
| GSE26712   | 185                | Y            | —            | —                                     | Y        | — (late-stage stated) | — (high-grade stated) | —   | HGSOC stated  | DOD/AWD/NED                                  |
| GSE17260   | 110                | Y            | Y            | proxy                                 | Y        | Y                     | Y                     | —   | serous        |                                              |
| GSE26193   | 107                | Y            | Y            | —                                     | —        | Y                     | Y                     | —   | mixed         | fibrosis/stress signature tag                |
| GSE49997   | 194                | Y            | Y            | —                                     | Y        | Y                     | Y                     | Y   | mostly serous | peritoneal carcinomatosis; subclass          |
| GSE14764   | 80                 | Y            | —            | —                                     | Y        | Y                     | Y                     | —   | mixed         | few deaths                                   |
| GSE30161   | 58                 | Y            | Y (PFI days) | Y                                     | Y        | Y                     | Y                     | Y   | mixed         | chemo agent; FFPE                            |
| GSE63885   | 75 labelled        | Y            | Y (DFS)      | **Y (best)**                          | Y        | Y                     | Y                     | —   | mixed         | **BRCA1, TP53**                              |
| GSE53963   | 174                | Y            | —            | —                                     | Y        | Y                     | Y                     | Y   | serous        | 14 TCGA IDs                                  |
| GSE51088   | 100 serous primary | Y            | p            | —                                     | —        | Y                     | Y                     | Y   | mixed         | two-color; drop normals                      |
| GSE13876   | 157 patients       | Y            | —            | —                                     | —        | —                     | —                     | Y   | serous stated | custom array; technical replicates           |
| GSE19161   | 61                 | Y            | —            | —                                     | —        | —                     | —                     | —   | —             | 658-probe custom array — skip                |
| GSE18520   | 53                 | p            | —            | —                                     | —        | late                  | high                  | —   | serous        | messy `surv data`                            |
| GSE8842    | 83                 | Y            | Y            | —                                     | —        | **all I**             | Y                     | Y   | mixed         | **early-stage relapse**                      |
| GSE51373   | 28                 | —            | —            | Y                                     | —        | Y                     | —                     | —   | HGSOC         |                                              |
| GSE131978  | 39                 | —            | —            | Y                                     | —        | Y                     | —                     | —   | HGSOC         | two platforms; long/short survivor in titles |
| GSE14407   | 12 tumors          | —            | —            | —                                     | —        | —                     | —                     | —   | serous vs OSE | diagnostic                                   |
| GSE154600  | 5                  | —            | —            | n                                     | —        | Y                     | Y                     | —   | HGSOC         | scRNA                                        |


Rough ceiling if one naively sums tumor samples that have **some** OS label (ignoring overlap and platform): on the order of **2,000**. After HGSOC-only filters, dropping two-color custom arrays, and removing the 14 GSE53963–TCGA duplicates, a realistic *multi-cohort OS* analysis is about **1,200–1,600** patients across 5–6 incompatible platforms. That is the same scale Riester/Waldron used, and they still found weak, poorly replicating signatures.

---



## 7. Opportunity analyses

Each subsection is a distinct prediction product. “Have the data?” is about **this workspace**, not about what exists somewhere on the internet.

Performance language: “ceiling” is an informed prior from this library plus the 2014 JNCI meta-analyses, not a guarantee.

### 7.1 Overall survival (time-to-death) — already started

**Clinical question.** At diagnosis, given the primary tumor’s expression (and age/stage/residual disease), what is the patient’s hazard of death?

**Required data.** Expression + OS time + death/censoring. Preferably HGSOC-only, known residual disease, and at least one external cohort on a **related** platform.

**Have it?** Yes, in volume. TCGA 303, GSE26712 185, GSE32062 260, GSE140082 380 (immature), GSE17260 110, GSE26193 79 serous, GSE49997 171 serous, GSE53963 174, GSE63885 70 serous, GSE30161 47 serous, GSE14764 68 serous, plus smaller sets. **Do not have it** for GSE9891 (the most cited validator).

**Design.** Cox / random survival forest / DeepSurv-style, always with a clinical-only baseline. Train on one platform family, validate on another. Report C-index **and** KM separation on the validator, not just internal CV.

**Expected ceiling.** C-index ~0.58–0.65 expression-only; clinical-only often ~0.60–0.65. Beating residual disease + stage by a *replicated* ΔC-index of 0.03 would already be a real result in this field.

**Recommendation.** Keep as a **secondary, literature-comparable** endpoint. Do not make it the product. Before another OS model: attach GSE9891 survival, add GSE32062 and GSE53963 as validators, subset HGSOC, and consider fetching TCGA U133A so n is ~550 rather than 303.

**Status:** **Active workstream** — tracked in `docs/current-focus-overall-survival.md` (since 27 Aug 2026). Data in hand (except GSE9891). First attempt already run; external performance is weak.

---



### 7.2 Horizon mortality (dead within 1 / 3 / 5 years)

**Clinical question.** Binary: will this patient die within X years? Easier to explain than a hazard, worse statistically (throws away censoring).

**Required data.** Same as OS, plus follow-up long enough to observe the horizon. Anyone censored before X years is **undefined** and must be dropped.

**Have it?** 3-year: TCGA 223 evaluable (already modelled, OOF AUC 0.70 with clinical, 0.62 on GSE26712). GSE32062 (times up to 128 months) and GSE26712 (up to 13.6 years) can support 3- and 5-year labels. GSE140082 max OS time is 1326 days (~3.6 years) and only 96 deaths — 5-year is impossible, 3-year is marginal. GSE49997 max 49 months — 5-year no. GSE14764 max 73 months but only 21 deaths.

**Expected ceiling.** Internal AUC 0.65–0.75; external 0.55–0.65 unless the validator is large and same-platform.

**Recommendation.** A 5-year classifier on GSE32062 (train) → GSE17260 (test), both Agilent, is a cleaner experiment than repeating 3-year on TCGA. Still a secondary endpoint.

**Status:** data in hand for 3-year; 5-year only on longer-follow-up microarray sets.

---



### 7.3 Progression-free survival / platinum-free interval — **highest-value survival task we can do now**

**Clinical question.** When will this disease come back? For HGSOC this is more proximal to the resected tumor’s biology than death (which is years of subsequent lines of therapy later). PFI also defines platinum resistance.

**Required data.** Expression + PFS/PFI time + event. Ideally all patients received platinum.

**Have it?**


| Source    | PFS/PFI                                | Notes                                                                                              |
| --------- | -------------------------------------- | -------------------------------------------------------------------------------------------------- |
| GSE32062  | 260, 193 events, all platinum+taxane   | Best dedicated set                                                                                 |
| GSE140082 | 380, 235 events                        | Trial therapy (half on bevacizumab) — model must include treatment or subset to standard arm (181) |
| GSE17260  | 110, 76 events                         | Same Agilent platform as GSE32062                                                                  |
| GSE26193  | 107 (79 serous), 80 events             | Mixed histotype                                                                                    |
| GSE49997  | 194, 124 events                        | ABI platform                                                                                       |
| GSE30161  | 58 PFI days                            | Plus relapse flag                                                                                  |
| GSE63885  | 75 DFS days                            | Plus explicit platinum class                                                                       |
| GSE8842   | 83 PFS days                            | Stage I only                                                                                       |
| TCGA      | 175 times-to-new-tumor; PFI incomplete | **Need PanCanAtlas CDR** before treating this as PFI                                               |
| GSE9891   | missing                                | Need curatedOvarianData                                                                            |


**Design.** Train a Cox model for PFS on GSE32062 (HGSOC, uniform treatment), validate on GSE17260 (same platform) and GSE26193 serous (Affy). Separately, try TCGA only after CDR PFI is attached. Always include residual disease: it is the dominant clinical predictor of PFS.

**Expected ceiling.** Slightly higher than OS (more events, less dilution). Still likely C-index <0.70. A replicated gain over residual disease is the bar.

**Recommendation.** **Do this next** as the main survival endpoint. It uses data we already have, matches how ovarian cancer is actually managed (when will she progress?), and is a better home for expression biology (stroma, immune, EMT) than OS.

**Status:** data in hand for a serious PFS study. TCGA PFI not trustworthy until CDR is fetched. GSE9891 PFS not in hand.

---



### 7.4 Platinum resistance (actionable binary / three-class)

**Clinical question.** Will this tumor progress within 6 months of platinum (resistant), between 6–12 months (partially sensitive), or later (sensitive)? This is the decision that changes next-line therapy. It is the closest thing in this library to “risk of a clinically defined complication of the disease.”

**Required data.** Either (a) a curated platinum-sensitivity class, or (b) PFI with a known last-platinum date. PFS-from-surgery <6 months is a **proxy**, not the GCIG definition.

**Have it?**


| Quality                          | Source          | n (usable)                                       |
| -------------------------------- | --------------- | ------------------------------------------------ |
| Curated 3-class                  | GSE63885 serous | 32 resistant / 26 moderate / 12 highly sensitive |
| Curated binary                   | GSE51373        | 16 sensitive / 12 resistant                      |
| Curated 3-class, tiny, two chips | GSE131978       | 37 with a class, split 25+14 across GPL96/GPL570 |
| RECIST after first line          | GSE30161        | 54 with CR/PR/PD (PD n=1 — cannot model PD)      |
| RECIST after first line          | TCGA HiSeq      | 223; **PD only 22**                              |
| Proxy PFS<6 mo                   | GSE32062        | 24 events                                        |
| Proxy PFS<6 mo                   | GSE17260        | 15                                               |
| Proxy PFS<6 mo                   | GSE140082       | 11                                               |
| Proxy PFS<6 mo                   | GSE49997        | 7                                                |
| scRNA                            | GSE154600       | 5 — ignore                                       |


**Have it in a form that can train a generalizable classifier?** Only if we **pool** GSE63885 + GSE51373 + GSE131978 + PFS proxies, accept noisy labels, and test leave-one-cohort-out. A model trained on GSE63885 alone (70 serous with a class) will overfit.

**Missing.** Last-platinum date in TCGA; GCIG class in most GEO series; any PARP-inhibitor label.

**Expected ceiling.** Internal AUC 0.70–0.80 is easy and meaningless on n=70. External AUC 0.60–0.70 on GSE51373 would be a genuine result. This is one of the few tasks where a moderately accurate model would change a decision.

**Recommendation.** Treat as **priority #2**, in parallel with PFS. Plan: (1) convert remaining GEO phenotypes to CSV, (2) define a single label dictionary (resistant = PFI/PFS <6 months or explicit “resistant”), (3) leave-one-cohort-out across GSE63885, GSE51373, GSE32062-proxy, GSE30161 CR vs not-CR, (4) do not claim GCIG platinum resistance unless the label was curated that way.

**Status:** labels in hand, sample size for a *single* training set is too small; sample size for a **multi-cohort** classifier is borderline but real (~150–200 labelled tumors if proxies are included).

---



### 7.5 Primary therapy outcome (CR vs not)

**Clinical question.** After surgery + first-line chemo, will imaging/CA125 show complete remission?

**Required data.** Expression from **pre-treatment** tumor + RECIST-like outcome. Post-treatment samples would leak.

**Have it?** TCGA 223 (CR 150 vs not-CR 73). GSE30161 54. GSE63885 serous CR 47 vs not 23. Whether every GEO sample is truly pre-chemo is not always documented; GSE30161 `surgtype: Primary Surgery` and `chemtype: Adjuvant` is the cleanest.

**Problem.** CR is common in optimally debulked HGSOC; the label is entangled with residual disease. A model that “predicts CR” by rediscovering residual disease is not a molecular test.

**Recommendation.** Only as a sensitivity analysis of §7.4, always with residual disease in the baseline. Not a standalone product.

**Status:** data in hand; scientifically slippery.

---



### 7.6 Residual disease / unresectability

**Clinical question.** From a pre-operative (or diagnostic) biopsy’s expression, will surgery achieve R0 / optimal debulking? This is **not** survival, but it is a major prognostic factor and a surgical decision.

**Required data.** Expression + residual-disease class. Ideally the profile is from a biopsy taken *before* the cytoreductive attempt. Most public series are **surgical specimens from the operation whose result they are labelling** — i.e. the sample is taken at the same time as the outcome. That is a serious leakage / circularity problem: a suboptimal case may be a different anatomic site or a more stromal sample.

**Have it?** Many cohorts: TCGA 267, GSE140082 378, GSE32062 260, GSE26712 185, GSE17260 110, GSE49997 194, GSE30161 56, GSE63885 75, GSE53963 171, GSE14764 76.

**Recommendation.** Publishable as an association study (mesenchymal/stromal programs ↔ suboptimal debulking — this is already known). Weak as a *prediction product* unless we can show the sample is a true pre-op biopsy. **Do not** sell this as “will the surgeon get it all?”

**Status:** labels in hand; causal/clinical interpretation is the blocker, not data volume.

---



### 7.7 Long-term vs short-term survivor

**Clinical question.** Extreme phenotypes: death within 2 years vs alive at 8–10 years. Used in GSE131978 titles (“Long-term survivor” / “Short-term Survivor”) and in several classic papers.

**Required data.** Long follow-up and a willingness to throw away the middle of the distribution.

**Have it?** TCGA has times to 15 years but HiSeq n=303 and 121 censored; a 10-year alive group will be small after dropping short-censored patients. GSE26712 goes to 13.6 years. GSE32062 to 10+ years. GSE131978 has the binary in the title (n=39, two platforms) without times. GSE140082 cannot do 10-year.

**Recommendation.** Optional exploratory analysis once OS/PFS pipelines work. Not a primary product (tiny n at the extremes, selection bias).

**Status:** possible on TCGA + GSE26712 + GSE32062; GSE131978 is too small to train.

---



### 7.8 Early-stage (FIGO I) relapse — GSE8842

**Clinical question.** Stage I disease is often cured; the clinical need is “who still relapses and needs adjuvant chemo?”

**Required data.** Stage I (or I–II) tumors + relapse / PFS.

**Have it?** **Only GSE8842** (n=83, all stage I; 21 relapsed; 13 cancer deaths). After dropping 15 borderline tumors: 68 invasive, 18 relapsed. Serous invasive: 24. TCGA HiSeq is almost all stage III–IV (one IC). GSE140082 has 20 stage I — not enough.

**Missing.** Any second early-stage cohort for validation.

**Recommendation.** Keep on the list as a clinically important question we **cannot** answer well with current files. Would need more stage I–II series (they exist in the literature; they are not in this download).

**Status:** one small mixed-histotype cohort. Not trainable as a general model.

---



### 7.9 Bevacizumab benefit (predictive, not prognostic) — unique in this library

**Clinical question.** ICON7-style: does *this* patient’s tumor imply she will gain PFS from adding bevacizumab? That is a **treatment interaction**, not a main-effect prognosis.

**Required data.** Randomized (or at least assigned) treated vs control, expression, PFS. Subtype labels help (the Kommoss paper’s claim is that proliferative/mesenchymal tumors benefit more).

**Have it?** **Only GSE140082.** 380 patients, 199 bev / 181 standard, PFS 235 events, precomputed subtypes. Serous high-grade 212 with balanced arms (109/103).

**Missing.** Any second bevacizumab-annotated expression cohort. GOG-218 / ICON7 clinical data beyond this series. OS in this file is immature (96 deaths).

**Expected ceiling.** A single-cohort interaction test can be done properly (pre-specify subtype × treatment, or train on a subset and test the rest). It **cannot** be externally validated with current files. That is still worth doing because almost nobody in this workspace’s paper list has a predictive design.

**Recommendation.** **High scientific value, low product value** until a second cohort exists. Run it as a focused notebook after PFS plumbing works. Do not advertise a “bevacizumab companion diagnostic.”

**Status:** one complete experiment in hand; no validator.

---



### 7.10 Expression subtype as an intermediate phenotype

**Clinical question.** Can we assign TCGA/Tothill subtypes (immunoreactive, differentiated, proliferative, mesenchymal; or Tothill C1–C6) from expression, and use that as a risk stratum?

**Required data.** Either published subtype labels, or a classifier trained where labels exist and applied elsewhere.

**Have it?** GSE140082 already has `t1_cluster_name` for 380 samples. TCGA subtypes are **not** a column in our clinical matrix (they live in the 2011 Nature paper supplements / CLOVAR resources, not downloaded). GSE9891 is the Tothill discovery set but **does not include C1–C6 in the GEO phenotype**. GSE49997 has `subclass` 1/2 (100/104) — a different dichotomy.

**Recommendation.** Useful as a **covariate and as a sanity check** (mesenchymal should look stromal; immunoreactive should look IFN-γ / HLA). Not a new product. Recomputing TCGA subtypes on HiSeq with the published CLOVAR genes would take a day and would help interpret every other model.

**Status:** labels in hand only for GSE140082; reproducible elsewhere if we implement the published classifiers.

---



### 7.11 BRCAness / HRD phenotype from expression

**Clinical question.** Does this tumor look like a homologous-recombination-deficient tumor (PARP-inhibitor / platinum sensitive biology) even if we do not have a BRCA test?

**Required data.** Expression + BRCA/HRD label on the same patients, then validation on an independent labelled set.

**Have it?** GSE63885: BRCA1 mutation status for 98/101 (28 carriers, 70 wild-type; among serous 21 vs 52). TCGA: **no BRCA column**; mutation MAF not downloaded (186 HiSeq samples have a mutation-track ID). No HRD score, no germline file, no PARP-inhibitor outcome anywhere.

**Missing.** TCGA BRCA1/2 annotations (publicly available via cBioPortal/GDC), CHORD/HRDetect-style scores, a second BRCA-labelled expression set.

**Recommendation.** Keep as a **future** task once MAF + cBioPortal clinical are fetched. With only GSE63885, a BRCA classifier is a 70-vs-28 overfit waiting to happen. Konstantinopoulos JCO 2010 (BRCAness signature) is the methods template — we do not yet have their full label set.

**Status:** one small labelled cohort locally; the real task needs TCGA mutation data we pointed at but did not download.

---



### 7.12 Histotype / tumor-vs-normal (not prognosis)

**Have it?** Mixed-histotype series (GSE26193, GSE14764, GSE63885, GSE8842, GSE51088, GSE30161, GSE49997 non-serous) plus GSE14407 (12 vs 12 OSE). Enough to train a histotype classifier as a **quality-control tool** (flag a “HGSOC” model that is actually detecting mucinous samples).

**Recommendation.** Build a small histotype QC classifier if mixed cohorts are used. Do not present it as prognosis.

**Status:** data in hand; out of scope for the product unless QC is needed.

---



### 7.13 DNA-sequence / multi-omic prognosis (the original product, if taken literally)

**Clinical question.** From mutations + copy-number (± expression), predict OS, PFI, or platinum response. This is closer to “look at the gene sequence of the tumor.”

**Required data.** At minimum: MAF (TP53, BRCA1/2, CDK12, NF1, RB1, CCNE1), GISTIC / copy-number (CCNE1 amp, MYC, KRAS), optionally methylation and a genomic HRD score; joined to the same survival table.

**Have it?** **No tables.** We have TCGA sample IDs that *would* join to those tables: mutation 316/630, GISTIC 579/630, methyl27 616/630, RPPA 436/630, miRNA 485/630. All of those files are public (GDC / Xena). CPTAC chemo-refractory proteogenomics (Cell 2023) is a separate, stronger chemo-response resource and is also not downloaded (and part of it is controlled-access).

**Recommendation.** If the long-term product is sequence-based, **stop adding GEO microarrays** and download: (1) PanCanAtlas CDR, (2) TCGA-OV MAF, (3) GISTIC2, (4) optionally the U133A matrix to enlarge expression-OS. Then the model is “expression + CCNE1 amp + BRCA status,” which is how a serious translational paper would be built. Until those files exist here, claiming a sequence model is false.

**Status:** not in hand. Clearly marked so it stays on the roadmap.

---



### 7.14 Complications, CA125, imaging, toxicity, PARP inhibitors, HIPEC

**Required data.** Per-patient events (obstruction, VTE, fistula, neuropathy, febrile neutropenia, …), longitudinal CA125, CT/MRI, drug exposure, or trial arms for PARPi/HIPEC.

**Have it?** No. GSE49997 `peritoneal carcinomatosis` (137 yes / 57 no) is the only “extent of disease” field that is adjacent to a complication. TCGA has `lymphatic_invasion` (127/304 HiSeq) and `venous_invasion` (95/304) — anatomic, not a future event.

**Recommendation.** Keep on the list as **product ideas that need a different dataset** (institutional EHR + biobank, or a trial like ICON7/SOLO1/PRIMA with both omics and toxicity tables). Do not imply the current GEO/TCGA dump can predict “risk of other complications.”

**Status:** not in hand.

---



### 7.15 Single-cell immune / microenvironment prognosis

**Required data.** scRNA with patient-level survival, or bulk expression plus a validated deconvolution that is then tied to survival.

**Have it?** Bulk: yes, plenty (and ESTIMATE / CIBERSORT-style scores can be computed on TCGA and GSE140082 without new downloads). True scRNA: GSE154600 n=5; Olbrecht EGAS00001004987 controlled.

**Recommendation.** Compute bulk immune/stromal scores as **features** for the PFS and platinum models. Do not wait on scRNA.

**Status:** bulk path in hand; scRNA path not.

---



## 8. What we should still get (only if a task above needs it)

Listed with the task they unlock. None of these are required to start PFS or platinum-proxy work on GEO.


| Acquisition                                                  | Unlocks                                                                  | Difficulty                               |
| ------------------------------------------------------------ | ------------------------------------------------------------------------ | ---------------------------------------- |
| **curatedOvarianData** (Bioconductor) or Tothill supplements | OS/PFS for **GSE9891**; harmonized OS for several series we already have | Medium (R package, then join on GSM IDs) |
| **PanCanAtlas CDR** (`TCGA-CDR-SupplementalTableS1.xlsx`)    | Standardized OS, DSS, DFI, **PFI** for TCGA-OV                           | Easy, public                             |
| **TCGA-OV Affymetrix U133A** (Xena)                          | ~565–593 tumors with OS instead of 303                                   | Easy; large file, pack for GitHub        |
| **TCGA-OV MAF + GISTIC**                                     | Sequence-like features; BRCAness labels; CCNE1 amp                       | Easy–medium, public                      |
| cBioPortal OV clinical (BRCA, HRD if present)                | BRCA/HRD without parsing MAF                                             | Easy                                     |
| CPTAC HGSOC proteogenomics                                   | State-of-the-art chemo-refractory prediction                             | Mixed public/controlled                  |
| A second early-stage series                                  | Stage I relapse validation                                               | Search + download                        |
| A second anti-angiogenic trial expression set                | Validate §7.9                                                            | May not exist publicly                   |
| Institutional data with complications / CA125                | The original “complications” product                                     | Not public                               |


GSE9891 without survival is the most embarrassing gap: we already stored 119 MB of expression for the field’s favorite validator and cannot use it for prognosis.

---



## 9. Recommended program (ordered)

This is a re-scope of the project, not a list of notebooks to write this afternoon.

### Do now (data already on disk)

1. **Define the disease.** Default analysis set = high-grade serous / serous advanced-stage. Mixed-histotype series are used only after subsetting, or as a histotype QC task.
2. **PFS as the primary survival endpoint.** Train GSE32062, validate GSE17260 (same platform), then GSE26193 serous and GSE49997 serous (cross-platform). Clinical baseline = residual disease + stage (+ age when present).
3. **Platinum-response as the primary *actionable* endpoint.** Pool explicit labels (GSE63885, GSE51373, GSE131978) with PFS<6-month proxies. Leave-one-cohort-out. Report against residual disease.
4. **Stop treating TCGA OS C-index as the scoreboard.** Keep the existing LASSO-Cox / 3-year notebooks as baselines to beat, not as the destination.



### Do next (small downloads, large gain)

1. Attach **GSE9891 survival** via curatedOvarianData. Then GSE9891 becomes the OS/PFS validator it was always meant to be.
2. Attach **PanCanAtlas PFI**. Then TCGA can enter the PFS study honestly.
3. Optionally download **TCGA U133A** if OS/PFS on TCGA remains a goal — 303 HiSeq samples is the binding constraint, not model class.



### Do as focused side studies

1. **Bevacizumab × subtype / expression interaction** on GSE140082. Pre-register the hypothesis (mesenchymal/proliferative benefit). No external validator — say so in the write-up.
2. Recompute **TCGA subtypes** on HiSeq; use them to explain the PFS/platinum models (not as a new product).



### Do only if the product is truly “sequence”

1. MAF + GISTIC + CDR, then a small model: clinical + CCNE1 amp + BRCA + a *short* expression signature. That is the honest version of “look at the tumor’s genes.”



### Do not do with current files

- Complication prediction.
- “Accurate” individual death dates or calibrated 5-year survival as a clinical test.
- Deep learning on 303 RNA-seq samples as a path to generalization.
- scRNA foundation models (no labelled n).
- Early-stage relapse as a general model (one cohort, n=68 invasive).
- Residual-disease *prediction* sold as a surgical tool (sample timing is wrong).

---



## 10. How this maps to the original product sentence

> “A prediction model that can take a look at the gene sequence for the tumor and accurately predict the future risk factor, risk of death, risk of other complications.”


| Phrase                      | Translation onto this library                                                                      |
| --------------------------- | -------------------------------------------------------------------------------------------------- |
| gene sequence               | **Not available.** Substitute: bulk expression now; mutations/CNV later if downloaded              |
| accurately                  | **Not supported** for death. Supported, weakly, for *ranking* PFS/OS risk and maybe platinum class |
| future risk factor          | Must pick **one** endpoint. The least-wrong default is **PFS / PFI**, not a generic risk score     |
| risk of death               | Possible as Cox OS; we already know the effect size is small and clinical covariates dominate      |
| risk of other complications | **No labels.** Closest available: platinum resistance, residual disease, peritoneal carcinomatosis |


A defensible project title, given the files:

**“Molecular risk of recurrence and platinum resistance in high-grade serous ovarian cancer from tumor gene expression, with clinical covariates as the required baseline.”**

That is less than the original vision. It is also something the data can actually test.

---



## Appendix A — Existing model numbers (unedited)

From `.research/colab/runs/`:

**LASSO-Cox OS (TCGA HiSeq → GSE26712 / GSE14764)**  
Train n=303 (182 events, 121 censored), 20,530 genes, top-500 by variance then L1 Cox (penalizer 0.05), signature size 178, 124/178 genes present on the Affy validators.  
Clinical OOF C-index 0.615 (n=266 with complete covariates). Expression OOF C-index 0.605. Internal KM log-rank p=1.2×10⁻⁵. 3-year OS AUC 0.629.  
GSE26712: n=185, 129 events, C-index 0.560, log-rank p=0.677.  
GSE14764: n=80, 21 events, C-index 0.530, log-rank p=0.881.

**3-year mortality classifier**  
Same train table; 80 dropped (censored <3 years); 223 evaluable; prevalence 0.426.  
OOF AUC: clinical LR 0.646, expression ENET 0.681, expression+clinical ENET **0.695**, HGB 0.638.  
Youden threshold 0.417: sensitivity 0.716, specificity 0.641. Internal KM p=2.3×10⁻⁷.  
GSE26712 AUC 0.615 (169 evaluable, 74 dead). GSE14764 AUC 0.505 (48 evaluable, 13 dead).

Top genes recurring in both signatures include OVGP1, SOSTDC1, MMP1, HLA-DRB6, PI3, OBP2B, NPY. That is a mixture of known ovarian/surface-epithelium and stromal/immune genes; it is **not** independently validated here.

---



## Appendix B — Notes on messy fields (so we do not mis-code them later)

- **GSE26712** `status_2` is GEO’s public-on date. The real vital field is `status` (DOD / AWD / NED). The first inventory pass can miss this because `status` collides with GEO metadata.
- **GSE13876** 415 rows are not 415 patients. Collapse on `assigned unique patient id` (157). `fumnd` = months from surgery; `status` 1 = OC death, 0 = censored *or* non-OC death (DSS-like). Two-color technical replicates.
- **GSE19161** has OS time+event but only **658 probes**. Do not use it to validate a genome-wide signature.
- **GSE51088 and GSE53963** put clinical fields on **channel 2**. A parser that only reads `characteristics_ch1` will conclude there is no survival. There is. GSE51088 also has 23 TCGA IDs (GSE53963 has 14).
- **GSE63885** platinum field contains colons inside the key (`resistant: DFS<180 days; ...`), so naive `key: value` splits truncate the column name. The value is still the class (resistant / moderately sensitive / highly sensitive / NA).
- **GSE30161 and GSE8842** dump one characteristic per sample in inconsistent order; keys must be parsed from each cell (`chemoresponse: CR ...`), not by column index.
- **GSE18520** `surv data`**:** `150 (A)` vs `21`. `(A)` = alive; unmarked likely dead; units months. Confirm against the Mok/Bonome paper before using.
- **GSE9891** GEO phenotype is site/type/subtype/stage/grade only. Do not invent survival from it.
- **GSE140082 times** (max 1326, median OS 770, median PFS 552) are days. OS is immature (25% dead). Prefer `manuscript_analysis359 == 1` (359/380) if matching the paper’s analysis set.
- **TCGA** `days_to_new_tumor_event_after_initial_treatment` is not a complete PFI. Prefer PanCanAtlas.
- **GSE53963** 14 `tcga_sampleid` values — exclude from any analysis that also uses TCGA, or they are not independent.
- **Histotype:** if a paper says “ovarian cancer” it is not HGSOC. Filter.

---



## Appendix C — Files consulted

- `datasets/ovarian-cancer-prognosis-ml/*/REPORT.md`
- Phenotype CSVs where converted (`csv/phenotype.csv`, `csv/OV_clinicalMatrix.csv`, `csv/HiSeqV2.csv`)
- GEO `*_series_matrix.txt` / `.gz` sample headers (`!Sample_characteristics_ch1` and `_ch2`)
- `notebooks/ovarian-os-lasso-cox.ipynb`, `notebooks/ovarian-3yr-mortality-classifier.ipynb`
- `.research/colab/runs/20260824T195053Z-tcga-ov-lasso-cox/run.json`
- `.research/colab/runs/20260825T034757Z-tcga-ov-3yr-mortality-clf/run.json`
- `docs/ovarian-cancer-prognosis-ml.md`, `docs/ovarian-cancer-prognosis-datasets.md`

Phenotype conversion is still missing for several GEO series (GSE140082, GSE63885, GSE51373, GSE131978, GSE53963, GSE51088, GSE8842, GSE13876, …). Expression CSVs exist for the series used in the two notebooks. That does not affect this audit (headers were parsed from the matrices). It will affect the next modelling notebook: convert those phenotypes before training, and pack any CSV >100 MB.