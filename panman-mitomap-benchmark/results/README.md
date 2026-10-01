# Results

`combined_summary.tsv` is the curated five-scale overview. The 10,000-sequence
row comes from the successful 4-core completion series; the smaller rows come
from the 8-core series.

`raw/` preserves the original numeric reports and tab-separated measurements,
including failed/incomplete attempts. Only the local username in absolute
historical paths was normalized from `/home/<local-user>` to `/home/USER`
before publication.

`panman/` contains the five compact PanMAN artifacts. `SHA256SUMS` can be used
to check them after download.

`validation/` contains the original validation, result, checksum, and success
JSON records. These records confirm the MSA/tree checks documented in the main
README. Their `panman_validation` field explicitly records that the archived
runs did not perform a PanMAN-to-FASTA round trip.
