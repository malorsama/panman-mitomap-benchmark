# Methods and interpretation

## Dataset

Human mitochondrial GenBank accession identifiers were exported from MITOMAP
on 2026-09-29. Nucleotide FASTA records were retrieved in batches with NCBI
EDirect. The experiment used 66,774 records after cleaning and sorting unique
accessions. Dataset sizes 100, 500, 1,000, 5,000, and 10,000 were nested prefix
subsets in the resulting FASTA order; they were not randomized or stratified.

This ordering matters. Results describe these exact subsets and must not be
interpreted as an unbiased sample of all human mitochondrial diversity.

## Workflow

Each subset was processed serially through:

1. deterministic `gzip -n -9` as a storage baseline;
2. sequence splitting with the PanMAN workflow helper;
3. tree inference with MashTree 1.4.6;
4. restoration of original sequence labels;
5. multiple sequence alignment with MAFFT 7.526 using
   `--auto --thread CORES --threadit 0`; and
6. PanMAN construction with `panmanUtils` 0.1.4 from the MSA and Newick tree.

Snakemake 9.22.0 orchestrated the stages. The reported workflow time includes
Conda/Snakemake launch overhead and all six workflow stages, but excludes input
subset creation, gzip, post-run validation, and report rendering. Stage wall
times, process exit codes, GNU maximum RSS, and one-second process-tree RSS
samples were recorded.

## Executed configurations

The 100, 500, 1,000, and 5,000 record runs used a budget of 8 cores. The initial
10,000-record attempt in that series was interrupted during MashTree. A clean
10,000-record completion used 4 cores and is reported separately. Each point
has one successful repeat, so no estimate of run-to-run variability is
available.

Hardware metadata recorded 32 logical CPUs and an AMD Ryzen 9 8940HX under
WSL. The 8-core session reported approximately 15.2 GiB RAM; the successful
10,000 run reached about 23.2 GiB sampled process-tree RSS, indicating that its
WSL memory allocation differed. Runtime scaling across those series is
therefore descriptive, not a controlled core-for-core comparison.

## Validation

The archived validation checked input/MSA IDs, MSA length consistency, exact
input recovery after gap removal, Newick leaf count/labels, process exit codes,
non-empty artifacts, and SHA-256 integrity.

It did not decode the PanMAN object. The repository workflow has been upgraded
to extract FASTA tips from each newly generated PanMAN and compare every input
ID and sequence exactly. Existing artifacts are intentionally not relabeled as
round-trip verified until that check is executed and recorded.

## Compression ratios

Ratios are uncompressed FASTA bytes divided by PanMAN bytes and deterministic
gzip bytes divided by PanMAN bytes. PanMAN stores a phylogenetically structured
pangenome rather than the same byte stream as gzip. The ratios are useful size
comparisons but should be interpreted alongside the representation and
validation differences.
