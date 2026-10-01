#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY="$(cd -- "$SCRIPT_DIR/.." && pwd)"
INPUT_ACCESSIONS="${INPUT_ACCESSIONS:-$REPOSITORY/data/experiment_accessions.txt}"
OUTPUT_DIR="${OUTPUT_DIR:-$REPOSITORY/data/raw}"
BATCH_SIZE="${BATCH_SIZE:-300}"
MAX_RETRIES="${MAX_RETRIES:-3}"
SLEEP_BETWEEN_BATCHES="${SLEEP_BETWEEN_BATCHES:-2}"

for command in epost efetch paste split awk sort grep sha256sum; do
    command -v "$command" >/dev/null 2>&1 || {
        echo "Missing required command: $command" >&2
        exit 1
    }
done

[[ -f "$INPUT_ACCESSIONS" ]] || {
    echo "Accession file not found: $INPUT_ACCESSIONS" >&2
    exit 1
}
[[ "$BATCH_SIZE" =~ ^[1-9][0-9]*$ ]] || {
    echo "BATCH_SIZE must be a positive integer" >&2
    exit 1
}

mkdir -p "$OUTPUT_DIR/batches" "$OUTPUT_DIR/fasta" "$OUTPUT_DIR/logs"
CLEAN_IDS="$OUTPUT_DIR/clean_ids.txt"
FAILED_LOG="$OUTPUT_DIR/logs/failed_batches.txt"
DOWNLOAD_LOG="$OUTPUT_DIR/logs/download.log"
FINAL_FASTA="$OUTPUT_DIR/mitomap_mtDNA.fasta"

# Accept either a headerless list or a one-column file headed genbank_id.
awk '
    { sub(/\r$/, "") }
    NR == 1 && tolower($0) == "genbank_id" { next }
    /^[[:space:]]*$/ { next }
    { print $1 }
' "$INPUT_ACCESSIONS" | sort -u > "$CLEAN_IDS"

TOTAL="$(wc -l < "$CLEAN_IDS")"
[[ "$TOTAL" -gt 0 ]] || { echo "No accessions found" >&2; exit 1; }
: > "$FAILED_LOG"
: > "$DOWNLOAD_LOG"

if ! compgen -G "$OUTPUT_DIR/batches/batch_*" >/dev/null; then
    split -d -a 4 -l "$BATCH_SIZE" "$CLEAN_IDS" "$OUTPUT_DIR/batches/batch_"
fi

mapfile -t batches < <(find "$OUTPUT_DIR/batches" -maxdepth 1 -type f -name 'batch_*' | sort)
for index in "${!batches[@]}"; do
    batch="${batches[$index]}"
    name="$(basename "$batch")"
    outfile="$OUTPUT_DIR/fasta/${name}.fasta"
    tmpfile="${outfile}.partial"
    expected="$(wc -l < "$batch")"

    if [[ -s "$outfile" ]] && [[ "$(grep -c '^>' "$outfile" || true)" -eq "$expected" ]]; then
        printf '[%d/%d] %s already complete\n' "$((index + 1))" "${#batches[@]}" "$name"
        continue
    fi

    success=0
    for ((attempt = 1; attempt <= MAX_RETRIES; attempt++)); do
        : > "$tmpfile"
        if paste -sd, "$batch" | epost -db nucleotide | efetch -format fasta \
                > "$tmpfile" 2>> "$DOWNLOAD_LOG"; then
            found="$(grep -c '^>' "$tmpfile" || true)"
            if [[ "$found" -eq "$expected" ]]; then
                mv "$tmpfile" "$outfile"
                success=1
                break
            fi
        fi
        rm -f -- "$tmpfile"
        (( attempt < MAX_RETRIES )) && sleep "$((attempt * 5))"
    done

    if [[ "$success" -ne 1 ]]; then
        printf '%s\n' "$name" >> "$FAILED_LOG"
        echo "Failed batch: $name" >&2
    fi
    sleep "$SLEEP_BETWEEN_BATCHES"
done

: > "$FINAL_FASTA"
while IFS= read -r file; do
    cat "$file" >> "$FINAL_FASTA"
done < <(find "$OUTPUT_DIR/fasta" -maxdepth 1 -type f -name 'batch_*.fasta' | sort)

DOWNLOADED="$(grep -c '^>' "$FINAL_FASTA" || true)"
echo "Requested:  $TOTAL"
echo "Downloaded: $DOWNLOADED"
echo "FASTA:      $FINAL_FASTA"
sha256sum "$FINAL_FASTA"

if [[ -s "$FAILED_LOG" || "$DOWNLOADED" -ne "$TOTAL" ]]; then
    echo "Download incomplete; inspect $FAILED_LOG and $DOWNLOAD_LOG" >&2
    exit 1
fi
