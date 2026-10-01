#!/usr/bin/env bash
# Run this file with bash in WSL/Linux. Keep the package files together.
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY="$(cd -- "$SCRIPT_DIR/.." && pwd)"
INPUT_FASTA="${INPUT_FASTA:-$REPOSITORY/data/raw/mitomap_mtDNA.fasta}"
EXPERIMENT_ROOT="${EXPERIMENT_ROOT:-$REPOSITORY/work/benchmark}"
CONDA_EXE="${CONDA_EXE:-$(command -v conda || true)}"
PANMAN_ENV="${PANMAN_ENV:-panman-env}"
MASHTREE_ENV="${MASHTREE_ENV:-mashtree-env}"
MAFFT_ENV="${MAFFT_ENV:-mafft-env}"
CORES="${CORES:-8}"
REPEATS="${REPEATS:-1}"
SAMPLE_SECONDS="${SAMPLE_SECONDS:-1}"
[[ -n "$CONDA_EXE" && -x "$CONDA_EXE" ]] || {
    echo "Conda not found. Set CONDA_EXE to an executable conda path." >&2
    exit 1
}
exec "$CONDA_EXE" run -n "$PANMAN_ENV" --no-capture-output \
    python "$SCRIPT_DIR/benchmark.py" \
    --input "$INPUT_FASTA" \
    --root "$EXPERIMENT_ROOT" --conda "$CONDA_EXE" \
    --panman-env "$PANMAN_ENV" --mashtree-env "$MASHTREE_ENV" \
    --mafft-env "$MAFFT_ENV" --cores "$CORES" --repeats "$REPEATS" \
    --sample-seconds "$SAMPLE_SECONDS" "$@"
