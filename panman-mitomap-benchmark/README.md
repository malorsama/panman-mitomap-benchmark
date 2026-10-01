# PanMAN compression benchmark on human mitochondrial genomes

This repository is a reproducible, independent benchmark of
[PanMAN](https://github.com/TurakhiaLab/panman) on human mitochondrial genome
sequences selected through MITOMAP accession metadata and retrieved from NCBI
GenBank. It packages the executed workflow, provenance, measured results, and
small PanMAN artifacts while excluding multi-gigabyte raw and intermediate
FASTA/alignment files.

> Scope: this is a human-mtDNA extension experiment that reproduces PanMAN's
> compression behavior on a new dataset. It is not a complete re-execution of
> every dataset and comparison in the PanMAN paper.

中文说明：本仓库整理了基于 MITOMAP accession、从 NCBI 获取的人类线粒体
基因组 PanMAN 压缩实验。仓库保留复现脚本、环境、汇总指标和 PanMAN 文件，
不提交约 4 GB 的原始与中间数据。

## Main result

Five nested prefix subsets were tested. The 100--5,000 sequence series used an
8-core budget. The 10,000-sequence completion run used 4 cores, so its runtime
must not be interpreted as a like-for-like scaling point against the 8-core
series. File-size ratios remain directly informative.

| Sequences | Cores | Workflow time | PanMAN build | FASTA | gzip -9 | PanMAN | FASTA / PanMAN | gzip / PanMAN |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 8 | 22.46 s | 2.92 s | 1.59 MiB | 29.81 KiB | 1.37 KiB | 1,184.73x | 21.74x |
| 500 | 8 | 81.89 s | 7.35 s | 7.86 MiB | 113.90 KiB | 5.44 KiB | 1,479.41x | 20.95x |
| 1,000 | 8 | 234.90 s | 13.81 s | 15.79 MiB | 224.45 KiB | 10.11 KiB | 1,600.45x | 22.21x |
| 5,000 | 8 | 8,083.36 s | 229.26 s | 78.40 MiB | 0.99 MiB | 48.16 KiB | 1,666.80x | 21.14x |
| 10,000 | 4 | 58,083.40 s | 418.25 s | 157.75 MiB | 1.93 MiB | 97.04 KiB | 1,664.72x | 20.41x |

The reported ratios compare different representations: raw FASTA and gzip are
not equivalent in semantics to PanMAN. They demonstrate storage behavior, not
by themselves losslessness or biological fidelity.

Machine-readable values are in
[`results/combined_summary.tsv`](results/combined_summary.tsv). The generated
PanMAN objects and SHA-256 checksums are under [`results/panman`](results/panman).

## What was validated

For the archived runs, success required:

- every workflow stage to exit successfully;
- non-empty MSA, Newick, and PanMAN outputs;
- identical input and alignment record IDs;
- equal alignment lengths;
- exact recovery of every input sequence after removing alignment gaps; and
- matching tree leaf counts and labels.

The archived runs did **not** decode PanMAN back to FASTA. The public workflow
in this repository now adds that stricter round-trip check: `panmanUtils
--fasta` must reproduce every input tip ID and sequence exactly. Because the
packaging environment could not execute the user's WSL installation, the
archived artifacts remain marked `roundtrip_not_run`; no round-trip result is
claimed without evidence.

## Reproduce

Linux or WSL is required. Conda is used only for environment isolation.

```bash
git clone <this-repository-url>
cd panman-mitomap-benchmark

conda env create -f envs/panman.yml
conda env create -f envs/mashtree.yml
conda env create -f envs/mafft.yml

bash scripts/download_mitomap.sh
bash benchmark/run_benchmark.sh --check-only
bash benchmark/run_benchmark.sh --sizes 100
bash benchmark/run_benchmark.sh
```

The default accession file is the exact 66,774-accession manifest used in the
reported experiment. To fetch the full original 66,775-accession export,
including `AB055387.1`, run:

```bash
INPUT_ACCESSIONS=data/mitomap_accessions_original.tsv \
OUTPUT_DIR=data/raw-full bash scripts/download_mitomap.sh
```

See [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) for configuration,
resource expectations, resuming, and output interpretation.

## Repository layout

```text
benchmark/       measured Snakemake workflow and report code
data/            accession manifests; downloaded sequences are ignored
docs/            methods, provenance, limitations, and reproduction guide
envs/            Conda environment definitions
results/raw/     original numeric reports/TSVs with local path prefixes redacted
results/panman/  compact PanMAN outputs for all five dataset sizes
results/validation/ archived validation/checksum records
scripts/         robust accession downloader
```

## Data provenance note

The original accession export contained 66,775 IDs. The historical downloader
unconditionally removed its first line as if it were a header, but the file
used at that point was already headerless. Consequently `AB055387.1` was
omitted and the executed experiment used 66,774 sequences. Both manifests are
preserved, the discrepancy is documented, and the downloader has been fixed to
detect an optional header rather than always discarding line 1.

## Citation

Please cite PanMAN and MITOMAP when reusing this workflow or its results:

- Walia S, Motwani H, Tseng YH, Smith K, Corbett-Detig R, Turakhia Y.
  *Compressive pangenomics using mutation-annotated networks*. Nature Genetics
  (2026). <https://doi.org/10.1038/s41588-025-02478-7>
- Lott MT, Leipzig JN, Derbeneva O, et al. mtDNA variation and analysis using
  MITOMAP and MITOMASTER. *Current Protocols in Bioinformatics* (2013).
  <https://mitomap.org/MITOMAP/CitingMitomap>

Software in this repository is MIT licensed. Third-party data, software, and
vendored helper files retain their own terms; see
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
