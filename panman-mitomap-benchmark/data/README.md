# Data manifests

`mitomap_accessions_original.tsv` is the original 2026-09-29 export with the
header `genbank_id` and 66,775 unique accessions.

`experiment_accessions.txt` contains the exact 66,774 accessions used in the
reported benchmark. It begins with `AB626609.1`; `AB055387.1` is absent because
the historical downloader treated the first line of a headerless intermediate
file as a header. This is an input-provenance issue, not a failed NCBI batch.

The resulting experimental FASTA contained 66,774 sequences, 1,105,169,064
bases, and 1,125,934,368 bytes. Its SHA-256 was:

```text
37fffeb0e0754f763fdf5523eb2d68e3d143ee3380bc17b5b8254f5c645e3c25
```

Downloaded files belong under `data/raw/` and are excluded from Git.
