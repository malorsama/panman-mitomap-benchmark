# Reproducibility guide

## Requirements

- Linux or WSL 2
- Conda or Mamba
- GNU time and gzip
- at least 8 CPU threads recommended
- substantially more than 24 GiB RAM for the 10,000-sequence run
- sufficient free disk space for FASTA, MSA, MashTree temporary data, and logs

The successful 10,000-sequence run took about 16.1 hours and sampled about
23.2 GiB process-tree RSS. Plan conservatively; exact requirements depend on
tool versions, WSL configuration, and input composition.

## Create environments

```bash
conda env create -f envs/panman.yml
conda env create -f envs/mashtree.yml
conda env create -f envs/mafft.yml
```

The environment files pin the principal tools used in the recorded run while
allowing compatible dependency resolution.

## Retrieve the exact experimental input

```bash
bash scripts/download_mitomap.sh
sha256sum data/raw/mitomap_mtDNA.fasta
```

Expected SHA-256 for the historical FASTA is
`37fffeb0e0754f763fdf5523eb2d68e3d143ee3380bc17b5b8254f5c645e3c25`.
NCBI records can be revised, so a later download may differ even when accession
versions are specified. Treat a checksum difference as a provenance change and
use a new experiment output directory.

## Run

```bash
bash benchmark/run_benchmark.sh --check-only
bash benchmark/run_benchmark.sh --sizes 100
bash benchmark/run_benchmark.sh --sizes 100 500 1000 5000 10000
```

Useful environment overrides:

```bash
CORES=4 REPEATS=3 SAMPLE_SECONDS=1 \
EXPERIMENT_ROOT="$PWD/work/replicated-run" \
bash benchmark/run_benchmark.sh --sizes 100 500 1000
```

The workflow will not install missing software. It refuses to mix changed
inputs, code, environments, hardware settings, or measurement settings into an
existing experiment root. Successful attempts are skipped only after their
recorded artifact hashes are verified.

## Round-trip validation

For new runs, the workflow now performs:

```bash
panmanUtils -I panman/out.panman --fasta --output-file decoded
```

It then requires every input tip ID and nucleotide sequence to match the
decoded FASTA exactly. PanMAN may emit additional inferred internal nodes;
those do not replace or weaken the required tip comparison.

## Reports

Each experiment root receives Markdown, HTML, and DOCX reports plus:

- `benchmark_summary.tsv`: the latest successful attempt per size/repeat;
- `all_attempts.tsv`: successes, failures, interruptions, and incomplete runs;
- `stage_metrics.tsv`: stage-level timing and memory measurements;
- `aggregate.tsv`: timing summaries over successful repeats; and
- `metadata/`: tool versions, Conda package lists, hardware, and code snapshots.
