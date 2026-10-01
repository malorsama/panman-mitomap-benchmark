# MSA route from the successfully tested PanMAN workflow.
# Separate stages add measurements; no original Snakefile is edited.
import sys
from pathlib import Path

PYTHON = sys.executable
RUNNER = str(Path("measure.py").resolve())
CONDA = config["conda"]
PANMAN_ENV = config["panman_env"]
MASHTREE_ENV = config["mashtree_env"]
MAFFT_ENV = config["mafft_env"]
FASTA = config["fasta"]
CORES = int(config["cores"])
INTERVAL = config["sample_seconds"]

rule all:
    input:
        "panman/out.panman",
        "output/mafft.aln",
        "output/mashtree.nwk"

rule mashtree:
    input:
        FASTA
    output:
        "output/mashtree.nwk"
    threads: CORES
    shell:
        r"""
        {PYTHON:q} {RUNNER:q} --name split --interval {INTERVAL} -- \
            {PYTHON:q} scripts/splitSeqs.py {input:q} temp
        {PYTHON:q} {RUNNER:q} --name mashtree --interval {INTERVAL} \
            --stdout output/mashtree.raw.nwk -- \
            {CONDA:q} run -n {MASHTREE_ENV:q} --no-capture-output \
            mashtree --numcpus {threads} temp/*.fasta
        {PYTHON:q} {RUNNER:q} --name rename --interval {INTERVAL} -- \
            {PYTHON:q} scripts/updateNewick.py \
            output/mashtree.raw.nwk temp_dir {output:q}
        """

rule mafft:
    input:
        fasta=FASTA,
        tree="output/mashtree.nwk"
    output:
        "output/mafft.aln"
    threads: CORES
    shell:
        r"""
        {PYTHON:q} {RUNNER:q} --name mafft --interval {INTERVAL} \
            --stdout {output:q} -- \
            {CONDA:q} run -n {MAFFT_ENV:q} --no-capture-output \
            mafft --thread {threads} --threadit 0 --auto {input.fasta:q}
        """

rule panman:
    input:
        msa="output/mafft.aln",
        tree="output/mashtree.nwk"
    output:
        "panman/out.panman"
    threads: CORES
    shell:
        r"""
        {PYTHON:q} {RUNNER:q} --name panman --interval {INTERVAL} -- \
            {CONDA:q} run -n {PANMAN_ENV:q} --no-capture-output \
            panmanUtils -M {input.msa:q} -N {input.tree:q} -o out
        """
