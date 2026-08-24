# Dataset verification report

**Location:** `/home/xoot/Projects/research/datasets/ovarian-cancer-prognosis-ml/tcga-ov-xena-rna-seq-hiseqv2`

- Files: 1
- Total size: 16.1 MB
- Tabular files profiled: 0

## `HiSeqV2.gz`  (16.1 MB, .gz)

## Usability verdict
**Usable for training** once joined to the clinical matrix.

- ~20,530 genes × **308** tumor samples (HiSeqV2)
- Pair with `tcga-ov-xena-clinical-matrix` using TCGA barcodes
- Note: clinical file has more rows (630); expression is the limiting set
- Good beginner RNA-seq starting point; Affymetrix TCGA-OV (~500) is larger if needed later
