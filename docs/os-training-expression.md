# OS training-pool expression

Gene-symbol expression matrix for the RNA-seq + Affymetrix training pool defined in `docs/os-train-validation-split.md`. Join to `datasets/ovarian-cancer-prognosis-ml/os-training-pool/labels.csv` on `sample_id` (matrix columns are that file’s row order).

**Script:** `agent/scripts/os_pool_expression.py` (Python 3 stdlib only).
**Outputs** (under `datasets/ovarian-cancer-prognosis-ml/`):

| File | What |
|---|---|
| `platform-annotations/GPL96.probe2symbol.tsv` | 1:1 probe → symbol after drop rules |
| `platform-annotations/GPL570.probe2symbol.tsv` | same for U133 Plus 2.0 |
| `os-training-pool/expression/<cohort>.csv` | per-cohort collapsed symbol × sample |
| `os-training-pool/expression_pool.csv` | common symbols × 751 samples |
| `os-training-pool/expression_pool.symbols.txt` | row order of the pool matrix |
| `os-training-pool/expression_manifest.json` | counts, collapse rule, anomalies |

This is **not** batch-corrected. Platform-family values stay on their native scales (Xena log2-ish RNA-seq vs Affymetrix MAS5-style). Downstream models must handle that (combat / cohort intercepts / rank-based features).

---

## How to run

```bash
python3 agent/scripts/os_pool_expression.py all       # annotate + collapse + merge + verify
python3 agent/scripts/os_pool_expression.py annotate
python3 agent/scripts/os_pool_expression.py collapse
python3 agent/scripts/os_pool_expression.py merge
python3 agent/scripts/os_pool_expression.py verify     # exit 1 on failure
```

`--data-root`, `--labels`, `--annot-dir`, `--expr-out`, `--pool-csv` override defaults. `verify` checks: dims == (intersection size) × 751; `sample_id` columns equal `labels.csv` order; no empty cells; every value is a finite float; per-cohort column counts match labels.

Numeric strings are copied from the source CSVs **unchanged** (no rounding). Means are used only to pick a winning probe.

If `expression_pool.csv` exceeds 100 MB the `all`/`merge` path runs `agent/scripts/github_pack.py pack --path …/os-training-pool`. The file written on 27 Aug 2026 is **76.7 MB**, so packing was skipped.

---

## Annotation provenance

GEO platform annotations dated **Aug 09 2016**, downloaded 27 Aug 2026. Full URLs, byte sizes, and the `1007_s_at` spot-check: `datasets/ovarian-cancer-prognosis-ml/platform-annotations/REPORT.md`.

Modern GEO annotation **adds** gene symbols the original array CDF did not carry. The canonical example:

```
1007_s_at  →  MIR4640///DDR1
```

DDR1 is the gene this probe was designed against; MIR4640 is a later locus annotation. This pipeline **drops** that probe (and every other `///` multi-mapper) instead of picking a side. Reproducibility over maximal probe count.

Drop rules (exclusive priority: AFFX, then empty/`---`, then `///`):

| Platform | Probe rows | AFFX- | empty/`---` | `///` multi | kept probes | unique symbols |
|---|---:|---:|---:|---:|---:|---:|
| GPL96 (HG-U133A) | 22,283 | 68 | 1,069 | 1,223 | 19,923 | **12,502** |
| GPL570 (HG-U133 Plus 2.0) | 54,675 | 62 | 9,505 | 2,214 | 42,894 | **20,848** |

Unmapped probes in the expression CSVs equal the dropped-probe total (GPL96 2,360; GPL570 11,781). No probe with a map entry lacked a finite mean on the analysis samples.

---

## Collapse rule

**Max-mean, per cohort, on that cohort’s `labels.csv` samples.**

For each gene symbol, among the probes that map 1:1 onto it, keep the probe with the highest mean expression across the analysis samples. Ties (none observed) break on lexicographically smaller probe ID. For HiSeqV2, rows are already gene symbols; the same rule would apply to duplicate symbol rows (none present: 20,530 rows, 20,530 unique symbols).

Rationale: this is the field default for HG-U133 collapse (Riester / curatedOvarianData / most MAS5-era signatures). It is deterministic given a frozen annotation and a frozen sample list, and it does not invent a new numeric scale. Averaging probes mixes isoform / cross-hybridization signals; IQR is a noise filter, not a representative.

Columns of each `<cohort>.csv` are that cohort’s `sample_id`s in `labels.csv` order. Extra expression samples (HOSE controls, non-serous, missing OS, 5 TCGA recurrent tumors, etc.) are ignored, not written.

---

## Per-stage symbol counts

| Stage | n |
|---|---:|
| HiSeqV2 symbols (RNA-seq family) | 20,530 |
| GPL96 collapsed (both cohorts identical) | 12,502 |
| GPL570 collapsed (all three cohorts identical) | 20,848 |
| **3-family intersection** | **11,474** |

The split doc guessed ~12k (HiSeq 20,530 ∩ GPL96 ~13k ∩ GPL570 ~20k). The real bottleneck is GPL96 after dropping multi-mappers (12,502, not ~13k), and the RNA-seq ∩ GPL96 ∩ GPL570 overlap is **11,474**.

Within each Affy family, every cohort has the same collapsed symbol set (union = intersection). No within-family drop.

### Per-cohort collapsed matrices

| Cohort | Platform | dims (symbols × samples) | file |
|---|---|---|---|
| tcga-ov-hiseqv2 | rnaseq_hiseqv2 | 20,530 × 302 | 42.8 MB |
| gse26712 | GPL96 | 12,502 × 185 | 26.3 MB |
| gse14764 | GPL96 | 12,502 × 68 | 9.7 MB |
| gse63885 | GPL570 | 20,848 × 70 | 16.7 MB |
| gse26193 | GPL570 | 20,848 × 79 | 12.5 MB |
| gse30161 | GPL570 | 20,848 × 47 | 6.7 MB |

---

## Final matrix

`expression_pool.csv`: **11,474 symbols × 751 samples**, 80,375,625 bytes (76.7 MB).

- Rows: common symbols, lexicographically sorted (`A1CF` … `ZZZ3`); same order as `expression_pool.symbols.txt`.
- Columns: `symbol`, then all 751 `sample_id`s in `labels.csv` row order (302 + 185 + 70 + 79 + 47 + 68).
- No empty cells; every value parses as a finite float (`verify` OK, 27 Aug 2026).
- GitHub packing **not** needed (< 100 MB).

Values are still platform-native. A1CF’s first three TCGA columns are `0.0000`, `0.4125`, `0.0000` (Xena); the last two (GSE14764) are `7.804439854`, `8.776534552` (Affy). Do not treat a row as a single homogeneous scale.

---

## Verification results

`python3 agent/scripts/os_pool_expression.py all` (27 Aug 2026) exited 0.

| Check | Result |
|---|---|
| dims 11,474 × 751 | OK |
| columns == labels.csv `sample_id` order | OK |
| empty / NA cells | 0 |
| non-finite / non-float cells | 0 |
| tcga-ov-hiseqv2 columns | 302 |
| gse26712 | 185 |
| gse63885 | 70 |
| gse26193 | 79 |
| gse30161 | 47 |
| gse14764 | 68 |
| packing | skipped (76.7 MB) |

---

## Decisions and anomalies

None of these changed counts vs the split-doc roles; they are recorded so a later re-run can be compared.

- **Multi-map drop is a gene-loss, not just a probe-loss.** `DDR1` and `MIR4640` are absent from the pool because `1007_s_at` (and any other DDR1 probe that GEO now annotates with `///`) was dropped. That is the cost of the frozen `///` rule.
- **HiSeqV2 has no duplicate symbol rows.** The max-mean branch for RNA-seq did not fire. Empty/`///` HiSeq symbols: 0.
- **No mean ties** on any Affy cohort (0 probes with equal means competing for a symbol).
- **Every labels.csv sample is on its expression matrix.** Extra expression columns (6 TCGA, 10/12 GPL96, 31/28/11 GPL570) are non-analysis samples and were not written.
- **No labels sample is missing from expression** (would have aborted collapse).
- **GPL96 is the intersection bottleneck**, not GPL570. Adding more GPL570 cohorts cannot grow the pool’s gene set.
- **No batch correction** at this step. The matrix is model-ready in *shape* (common genes, aligned columns), not in *scale*.

---

## Pointers

- Labels: `docs/os-training-labels.md`
- Split decision: `docs/os-train-validation-split.md`
- Annotation download: `datasets/ovarian-cancer-prognosis-ml/platform-annotations/REPORT.md`
- Validation-side mirror: `docs/os-validation-expression.md`
- Workstream: `research/os-hgsoc/workstream.md`
