# Third-party notices

## PanMAN

PanMAN and the helper scripts vendored under `benchmark/upstream/` originate
from <https://github.com/TurakhiaLab/panman>, commit `1c3c620`, and are provided
under the MIT License. The full upstream source is not duplicated here.

## MITOMAP

The accession metadata was exported from MITOMAP on 2026-09-29. MITOMAP asks
users to cite the database and states that site content is licensed under
Creative Commons Attribution 3.0 unless otherwise noted:

- <https://www.mitomap.org/MITOMAP/CitingMitomap>
- <https://www.mitomap.org/MITOWIKI/HelpTerms>

The accession lists in `data/` are included for provenance and reproducibility.

## NCBI GenBank

Sequence records were retrieved from the NCBI Nucleotide database with NCBI
EDirect (`epost` and `efetch`). Raw FASTA records are intentionally not stored
in this Git repository; they can be regenerated from accession identifiers.
Users remain responsible for following NCBI usage policies and for citing the
original sequence submitters where appropriate.

## Other tools

The workflow also invokes Snakemake, MashTree, MAFFT, Biopython, ETE3, psutil,
GNU time, and gzip. These projects retain their respective licenses.
