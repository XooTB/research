# Platform annotation download report

**Download date:** 2026-08-27

## Sources

GEO "Download annotation" links resolve to NCBI FTP paths under `GPLnnn/` (not `GPL96nnn` / `GPL570nnn`).

| Platform | Title | Annotation URL |
|----------|-------|----------------|
| GPL96 | [HG-U133A] Affymetrix Human Genome U133A Array | https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPLnnn/GPL96/annot/GPL96.annot.gz |
| GPL570 | [HG-U133_Plus_2] Affymetrix Human Genome U133 Plus 2.0 Array | https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPLnnn/GPL570/annot/GPL570.annot.gz |

GEO accession pages: [GPL96](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GPL96), [GPL570](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GPL570).

**Note:** The paths `.../GPL96nnn/GPL96/...` and `.../GPL570nnn/GPL570/...` return HTTP 404; the working paths use `GPLnnn`.

## Local files

| File | Size (bytes) | Size (human) |
|------|-------------|--------------|
| `GPL96.annot.gz` | 4,522,748 | ~4.3 MiB |
| `GPL570.annot.gz` | 8,471,521 | ~8.1 MiB |

Format: gzip-compressed GEO platform annotation TSV (header lines prefixed with `^`, `!`, `#`; table begins at `!platform_table_begin`).

**Annotation date (in file):** Aug 09 2016 (both platforms).

## Row counts

Data rows = lines after the column header row until end of file (excluding metadata lines).

| File | Data rows | Expected probe sets |
|------|-----------|---------------------|
| GPL96 | 22,284 | ~22,283 |
| GPL570 | 54,676 | ~54,675 |

## Column names

Probe-set identifier column: **`ID`**

Gene symbol column: **`Gene symbol`**

Full header (tab-separated):

```
ID	Gene title	Gene symbol	Gene ID	UniGene title	UniGene symbol	UniGene ID	Nucleotide Title	GI	GenBank Accession	Platform_CLONEID	Platform_ORF	Platform_SPOTID	Chromosome location	Chromosome annotation	GO:Function	GO:Process	GO:Component	GO:Function ID	GO:Process ID	GO:Component ID
```

## Spot checks

| Check | GPL96 | GPL570 |
|-------|-------|--------|
| Probe `1007_s_at` → `Gene symbol` | `MIR4640///DDR1` (includes **DDR1**) | `MIR4640///DDR1` (includes **DDR1**) |
| `AFFX-` control probes present | Yes (68 rows with ID matching `^AFFX-`) | Yes (62 rows) |
| Example AFFX IDs | `AFFX-BioB-3_at`, `AFFX-BioB-5_at`, `AFFX-BioB-M_at` | same |

AFFX control rows typically have empty `Gene symbol` fields, as expected.

---

## Validation-cohort platforms (2026-08-27)

### Sources

For 4–5 digit platforms, NCBI FTP uses a truncated directory prefix (`GPL6nnn`, `GPL14nnn`, `GPL2nnn`) — not `GPLnnn`.

| Platform | Title | Annotation URL | Result |
|----------|-------|----------------|--------|
| GPL6480 | Agilent-014850 Whole Human Genome Microarray 4x44K G4112F | https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPL6nnn/GPL6480/annot/GPL6480.annot.gz | OK (`.annot.gz`) |
| GPL14951 | Illumina HumanHT-12 WG-DASL V4.0 R2 expression beadchip | https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPL14nnn/GPL14951/annot/GPL14951.annot.gz | **404** — no `annot/` directory; see fallback below |
| GPL2986 | ABI Human Genome Survey Microarray Version 2 | https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPL2nnn/GPL2986/annot/GPL2986.annot.gz | OK (`.annot.gz`) |

GEO accession pages: [GPL6480](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GPL6480), [GPL14951](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GPL14951), [GPL2986](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GPL2986).

**GPL14951 fallback:** Platform directory lists only `soft/GPL14951_family.soft.gz` (2.3 GiB; no standalone `GPL14951.soft.gz` or `GPL14951.annot.gz`). Platform annotation table extracted by streaming the first 50 MiB of the family SOFT file (platform table ends at line 38 371 of decompressed content). Saved as `GPL14951.platform_table.soft.gz`.

Source for fallback: https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPL14nnn/GPL14951/soft/GPL14951_family.soft.gz

### Local files

| File | Size (bytes) | Size (human) | Source |
|------|-------------|--------------|--------|
| `GPL6480.annot.gz` | 7,380,104 | ~7.0 MiB | direct download |
| `GPL14951.platform_table.soft.gz` | 11,278,202 | ~10.8 MiB | extracted from family SOFT |
| `GPL2986.annot.gz` | 4,025,879 | ~3.8 MiB | direct download |

Format: gzip-compressed GEO platform annotation TSV (`.annot`) or SOFT platform block (`.soft`); table begins at `!platform_table_begin`.

**Annotation date (in file):** Aug 09 2016 (GPL6480, GPL2986). GPL14951 has no `!Annotation_date`; platform metadata shows `!Platform_last_update_date = Dec 22 2017`.

### Row counts

| File | Data rows | Notes |
|------|-----------|-------|
| GPL6480 | 41,108 | Agilent 4×44K |
| GPL14951 | 29,377 | Illumina HumanHT-12 WG-DASL V4.0 |
| GPL2986 | 32,878 | ABI Human Genome Survey V2 |

### Column names and probe→symbol mapping

| Platform | Probe ID column | Gene symbol column | Notes |
|----------|----------------|-------------------|-------|
| GPL6480 | `ID` | `Gene symbol` | Agilent probe names (e.g. `A_23_P100001`) |
| GPL14951 | `ID` | `Symbol` | Illumina probe IDs (e.g. `ILMN_3166687`); `ILMN_Gene` is identical to `Symbol` for all 29 377 rows |
| GPL2986 | `ID` | `Gene symbol` | ABI numeric probe IDs (e.g. `139282`) |

**GPL6480** full header (22 columns, tab-separated):

```
ID	Gene title	Gene symbol	Gene ID	UniGene title	UniGene symbol	UniGene ID	Nucleotide Title	GI	GenBank Accession	Platform_CLONEID	Platform_ORF	Platform_SPOTID	Chromosome location	Chromosome annotation	GO:Function	GO:Process	GO:Component	GO:Function ID	GO:Process ID	GO:Component ID	Platform_SEQUENCE
```

**GPL14951** full header (28 columns, tab-separated):

```
ID	Transcript	Species	Source	Search_Key	ILMN_Gene	Source_Reference_ID	RefSeq_ID	Entrez_Gene_ID	GI	Accession	Symbol	Protein_Product	Array_Address_Id	Probe_Type	Probe_Start	SEQUENCE	Chromosome	Probe_Chr_Orientation	Probe_Coordinates	Cytoband	Definition	Ontology_Component	Ontology_Process	Ontology_Function	Synonyms	Obsolete_Probe_Id	GB_ACC
```

**GPL2986** full header (21 columns, tab-separated):

```
ID	Gene title	Gene symbol	Gene ID	UniGene title	UniGene symbol	UniGene ID	Nucleotide Title	GI	GenBank Accession	Platform_CLONEID	Platform_ORF	Platform_SPOTID	Chromosome location	Chromosome annotation	GO:Function	GO:Process	GO:Component	GO:Function ID	GO:Process ID	GO:Component ID
```

### Spot checks

| Check | GPL6480 | GPL14951 | GPL2986 |
|-------|---------|----------|---------|
| Example probe → symbol | `A_23_P100001` → **FAM174B** | `ILMN_1755789` → **MEI1** | `139282` → **GAP43** |
| Second example | `A_23_P100011` → **AP3S2** | `ILMN_1667034` → **PDPR** | `131316` → **GPHN** |
| Third example | `A_23_P162945` → **SRP54** | `ILMN_3166687` → **ERCC-00162** (spike-in control) | `206338` → **MFSD7** |
| Empty symbol rows | rare | none (all 29 377 populated) | some (e.g. probe `156427` has empty `Gene symbol`) |
