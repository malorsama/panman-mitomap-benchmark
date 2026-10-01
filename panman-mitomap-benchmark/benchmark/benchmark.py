#!/usr/bin/env python3
"""Human mtDNA PanMAN benchmark: isolated attempts, measured stages, reports."""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from measure import atomic_json, now, run_measure
from report import build_report

PACKAGE = Path(__file__).resolve().parent
REPOSITORY = PACKAGE.parent
SIZES = [100, 500, 1000, 5000, 10000]
ARTIFACTS = ["input.fasta", "input.fasta.gz", "output/mafft.aln",
             "output/mashtree.nwk", "panman/out.panman", "info/decoded_0.fasta"]


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def records(path):
    header = None
    sequence = []
    with Path(path).open(encoding="utf-8-sig") as handle:
        for number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(sequence)
                header = line[1:].strip()
                if not header:
                    raise ValueError(f"Empty FASTA header at line {number}")
                sequence = []
            else:
                if header is None:
                    raise ValueError(f"Sequence before FASTA header at line {number}")
                sequence.append("".join(line.split()))
    if header is not None:
        yield header, "".join(sequence)


def check_records(items):
    ids = set()
    for header, sequence in items:
        ident = header.split()[0]
        if ident in ids:
            raise ValueError(f"Duplicate FASTA ID: {ident}")
        ids.add(ident)
        if not sequence or set(sequence.upper()) - set("ACGTRYSWKMBDHVN"):
            raise ValueError(f"Empty or non-IUPAC DNA sequence: {ident}")
    return ids


def checked(command, timeout=90):
    result = subprocess.run(command, text=True, encoding="utf-8", errors="replace",
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {command}\n{result.stdout[-6000:]}")
    return result.stdout


def conda_cmd(args, env, *command):
    return [args.conda, "run", "-n", env, "--no-capture-output", *command]


def preflight(args):
    if sys.platform != "linux":
        raise RuntimeError("Run this benchmark inside Linux/WSL, not Windows Python")
    for module in ("psutil", "Bio", "ete3"):
        __import__(module)
    upstream = PACKAGE / "upstream"
    for path in [args.input, upstream / "scripts/splitSeqs.py",
                 upstream / "scripts/updateNewick.py"]:
        if not Path(path).is_file():
            raise FileNotFoundError(path)
    for command in (args.conda, "/usr/bin/time", "gzip"):
        if shutil.which(command) is None:
            raise RuntimeError(f"Missing executable: {command}")
    import psutil
    available_cpus = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count()
    if args.cores > available_cpus:
        raise ValueError(f"CORES={args.cores} exceeds {available_cpus} CPUs available in this WSL/Linux session")
    versions = {
        "snakemake": checked(conda_cmd(args, args.panman_env, "snakemake", "--version")),
        "mashtree": checked(conda_cmd(args, args.mashtree_env, "mashtree", "--version")),
        "mafft": checked(conda_cmd(args, args.mafft_env, "mafft", "--version")),
        "panman_help": checked(conda_cmd(args, args.panman_env, "panmanUtils", "--help")),
        "gnu_time": checked(["/usr/bin/time", "--version"]),
        "python": sys.version,
    }
    envs = {}
    for name in [args.panman_env, args.mashtree_env, args.mafft_env]:
        packages = json.loads(checked([args.conda, "list", "-n", name, "--json"]))
        envs[name] = sorted([{k: p.get(k) for k in ("name", "version", "build_string", "channel")}
                             for p in packages], key=lambda p: p["name"])
    hardware = {"platform": os.uname()._asdict() if hasattr(os.uname(), "_asdict") else list(os.uname()),
                "cpus_available": available_cpus,
                "ram_bytes": psutil.virtual_memory().total,
                "swap_bytes": psutil.swap_memory().total,
                "cpuinfo": Path("/proc/cpuinfo").read_text(errors="replace")}
    return versions, envs, hardware


def dataset_info(path, limit):
    selected = []
    count = bases = 0
    smallest = None
    largest = 0
    for header, sequence in records(path):
        count += 1
        bases += len(sequence)
        smallest = len(sequence) if smallest is None else min(smallest, len(sequence))
        largest = max(largest, len(sequence))
        if count <= limit:
            selected.append((header, sequence))
    if not count:
        raise ValueError("Input contains no FASTA sequences")
    check_records(selected)
    return selected, {"total_sequences": count, "total_bases": bases,
                      "min_length": smallest, "max_length": largest,
                      "mean_length": bases / count, "bytes": Path(path).stat().st_size}


def save_subset(path, items):
    path = Path(path)
    tmp = path.with_name(path.name + ".partial")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        for header, sequence in items:
            handle.write(f">{header}\n{sequence}\n")
    if path.exists():
        if sha256(path) != sha256(tmp):
            tmp.unlink()
            raise RuntimeError(f"Existing dataset differs: {path}; use a new EXPERIMENT_ROOT")
        tmp.unlink()
    else:
        os.replace(tmp, path)


def valid_success(directory):
    marker = directory / "SUCCESS.json"
    if not marker.is_file():
        return False
    try:
        result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
        if result["status"] != "SUCCESS":
            return False
        expected = json.loads(marker.read_text(encoding="utf-8"))["sha256"]
        if set(expected) != set(ARTIFACTS):
            return False
        return all((directory / f).is_file() and (directory / f).stat().st_size > 0
                   and sha256(directory / f) == digest for f, digest in expected.items())
    except (OSError, ValueError, KeyError):
        return False


def validate_outputs(run_dir, n):
    from Bio import Phylo
    fasta = {h.split()[0]: s.upper() for h, s in records(run_dir / "input.fasta")}
    aligned_items = list(records(run_dir / "output/mafft.aln"))
    aligned = {h.split()[0]: s.upper() for h, s in aligned_items}
    if len(aligned_items) != n or len(aligned) != n or set(aligned) != set(fasta):
        raise ValueError("Alignment sequence count or IDs do not match input")
    lengths = {len(s) for s in aligned.values()}
    if len(lengths) != 1:
        raise ValueError("Aligned sequences are not all the same length")
    if any(aligned[i].replace("-", "") != fasta[i] for i in fasta):
        raise ValueError("Removing alignment gaps does not reproduce input sequences")
    tree = Phylo.read(str(run_dir / "output/mashtree.nwk"), "newick")
    leaves = [leaf.name for leaf in tree.get_terminals()]
    descriptions = {h for h, _ in records(run_dir / "input.fasta")}
    if len(leaves) != n or len(set(leaves)) != n:
        raise ValueError("Tree leaf count or uniqueness does not match input")
    if set(leaves) not in (set(fasta), descriptions):
        raise ValueError("Tree leaf labels do not match FASTA IDs or full headers")
    for filename in ARTIFACTS:
        if not (run_dir / filename).is_file() or (run_dir / filename).stat().st_size == 0:
            raise ValueError(f"Missing or empty result: {filename}")
    decoded_items = list(records(run_dir / "info/decoded_0.fasta"))
    decoded_tips = {}
    for header, sequence in decoded_items:
        ident = header.split()[0]
        if ident in fasta:
            if ident in decoded_tips:
                raise ValueError(f"Duplicate decoded tip: {ident}")
            decoded_tips[ident] = sequence.upper()
    if set(decoded_tips) != set(fasta):
        missing = sorted(set(fasta) - set(decoded_tips))[:10]
        raise ValueError(f"Decoded PanMAN tips do not match input IDs; missing examples: {missing}")
    if any(decoded_tips[ident] != fasta[ident] for ident in fasta):
        raise ValueError("PanMAN decoding does not reproduce the input sequences")
    return {"input_count": n, "alignment_count": len(aligned),
            "alignment_length": next(iter(lengths)), "tree_leaves": len(leaves),
            "ungapped_alignment_matches_input": True,
            "decoded_record_count": len(decoded_items),
            "decoded_tip_count": len(decoded_tips),
            "panman_roundtrip_matches_input": True,
            "panman_validation": "decoded FASTA tips exactly match input IDs and sequences"}


def run_one(args, root, subset, n, rep, snapshot):
    base = root / "results" / str(n) / f"rep_{rep:02d}"
    base.mkdir(parents=True, exist_ok=True)
    attempts = sorted(base.glob("attempt_*"))
    # Earlier successful attempt may be reused only after artifact checksums pass.
    for previous in reversed(attempts):
        if valid_success(previous):
            print(f"[SKIP VERIFIED] n={n} rep={rep}: {previous}", flush=True)
            return True
        result_path = previous / "result.json"
        if result_path.exists():
            old = json.loads(result_path.read_text(encoding="utf-8"))
            if old.get("status") == "SUCCESS":
                old.update(status="INTEGRITY_FAILED", failure_reason="Previously successful artifacts failed checksum verification")
                atomic_json(result_path, old)
    index = max([int(p.name.split("_")[-1]) for p in attempts] + [0]) + 1
    run_dir = base / f"attempt_{index:03d}"
    run_dir.mkdir()
    for folder in ("output", "panman", "info", "logs", "tmp"):
        (run_dir / folder).mkdir()
    shutil.copy2(subset, run_dir / "input.fasta")
    shutil.copytree(snapshot / "scripts", run_dir / "scripts")
    for name in ("benchmark.smk", "measure.py"):
        shutil.copy2(snapshot / name, run_dir / name)
    config = {"conda": args.conda, "panman_env": args.panman_env,
              "mashtree_env": args.mashtree_env, "mafft_env": args.mafft_env,
              "fasta": "input.fasta", "cores": args.cores, "sample_seconds": args.sample_seconds}
    atomic_json(run_dir / "config.json", config)
    row = {"sequences": n, "repeat": rep, "attempt": index, "status": "RUNNING",
           "started_utc": now(), "run_directory": str(run_dir), "cores": args.cores,
           "fasta_bytes": subset.stat().st_size, "failure_reason": ""}
    atomic_json(run_dir / "result.json", row)
    print(f"[START] n={n} rep={rep} attempt={index}: {run_dir}", flush=True)
    started = time.monotonic()
    old_tmp = os.environ.get("TMPDIR")
    os.environ["TMPDIR"] = str(run_dir / "tmp")
    try:
        gzip_metrics = run_measure(["gzip", "-n", "-9", "-c", "input.fasta"], "gzip", run_dir,
                                   args.sample_seconds, "input.fasta.gz")
        if gzip_metrics["exit_code"] != 0:
            raise RuntimeError("gzip baseline failed; see logs/gzip.log")
        row["gzip_bytes"] = (run_dir / "input.fasta.gz").stat().st_size
        command = conda_cmd(args, args.panman_env, "snakemake", "--snakefile", "benchmark.smk",
                            "--configfile", "config.json", "--cores", str(args.cores),
                            "--rerun-incomplete", "--printshellcmds", "--latency-wait", "30")
        workflow = run_measure(command, "workflow", run_dir, args.sample_seconds)
        row.update(workflow_seconds=workflow["elapsed_seconds"], exit_code=workflow["exit_code"],
                   workflow_gnu_maxrss_kib=workflow.get("gnu_maxrss_kib"),
                   workflow_sampled_tree_peak_rss_mib=workflow["sampled_tree_peak_rss_bytes"] / 1048576)
        if workflow["exit_code"] != 0:
            raise RuntimeError("Snakemake failed; see logs/workflow.log and the stage logs")
        decode = run_measure(
            conda_cmd(args, args.panman_env, "panmanUtils", "-I", "panman/out.panman",
                      "--fasta", "--output-file", "decoded"),
            "decode", run_dir, args.sample_seconds)
        if decode["exit_code"] != 0:
            raise RuntimeError("PanMAN FASTA extraction failed; see logs/decode.log")
        validation = validate_outputs(run_dir, n)
        atomic_json(run_dir / "validation.json", validation)
        digest = {f: sha256(run_dir / f) for f in ARTIFACTS}
        atomic_json(run_dir / "checksums.json", digest)
        row.update(status="SUCCESS", alignment_length=validation["alignment_length"],
                   alignment_bytes=(run_dir / "output/mafft.aln").stat().st_size,
                   tree_bytes=(run_dir / "output/mashtree.nwk").stat().st_size,
                   panman_bytes=(run_dir / "panman/out.panman").stat().st_size)
        row["fasta_to_panman_ratio"] = row["fasta_bytes"] / row["panman_bytes"]
        row["gzip_to_panman_ratio"] = row["gzip_bytes"] / row["panman_bytes"]
        row["alignment_to_panman_ratio"] = row["alignment_bytes"] / row["panman_bytes"]
        atomic_json(run_dir / "SUCCESS.json", {"completed_utc": now(), "sha256": digest})
    except KeyboardInterrupt:
        row.update(status="INTERRUPTED", failure_reason="Interrupted; next run starts a fresh attempt")
        raise
    except Exception as exc:
        row.update(status="FAILED", failure_reason=str(exc))
    finally:
        if old_tmp is None:
            os.environ.pop("TMPDIR", None)
        else:
            os.environ["TMPDIR"] = old_tmp
        row.update(ended_utc=now(), attempt_seconds=round(time.monotonic() - started, 6),
                   disk_free_bytes_end=shutil.disk_usage(run_dir).free)
        wf_path = run_dir / "logs/workflow.metrics.json"
        if wf_path.exists() and "workflow_seconds" not in row:
            wf = json.loads(wf_path.read_text(encoding="utf-8"))
            row.update(workflow_seconds=wf["elapsed_seconds"], exit_code=wf["exit_code"],
                       workflow_gnu_maxrss_kib=wf.get("gnu_maxrss_kib"),
                       workflow_sampled_tree_peak_rss_mib=wf["sampled_tree_peak_rss_bytes"] / 1048576)
        # Include available stage results even for failed attempts.
        for name in ("gzip", "split", "mashtree", "rename", "mafft", "panman", "decode"):
            p = run_dir / "logs" / f"{name}.metrics.json"
            if p.exists():
                metric = json.loads(p.read_text(encoding="utf-8"))
                row[name + "_seconds"] = metric["elapsed_seconds"]
        atomic_json(run_dir / "result.json", row)
        build_report(root)
        print(f"[{row['status']}] n={n} rep={rep}: {row.get('failure_reason', '')}", flush=True)
    return row["status"] == "SUCCESS"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(REPOSITORY / "data/raw/mitomap_mtDNA.fasta"))
    parser.add_argument("--root", default=str(REPOSITORY / "work/benchmark"))
    parser.add_argument("--conda", default=shutil.which("conda") or "conda")
    parser.add_argument("--panman-env", default="panman-env")
    parser.add_argument("--mashtree-env", default="mashtree-env")
    parser.add_argument("--mafft-env", default="mafft-env")
    parser.add_argument("--cores", type=int, default=8)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--sample-seconds", type=float, default=1.0)
    parser.add_argument("--sizes", nargs="+", type=int, default=SIZES)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()
    if args.cores < 1 or args.repeats < 1 or args.sample_seconds <= 0:
        parser.error("cores, repeats, sample-seconds must be positive")
    if not args.sizes or any(n < 2 or n > 10000 for n in args.sizes):
        parser.error("Every requested size must be between 2 and 10000")
    args.sizes = sorted(set(args.sizes))
    root = Path(args.root).expanduser().resolve()
    if args.report_only:
        if not (root / "metadata/experiment.json").is_file():
            parser.error("No existing experiment metadata at this root")
        if sys.platform != "linux":
            parser.error("Run --report-only in Linux/WSL")
        import fcntl
        with (root / ".benchmark.lock").open("a") as report_lock:
            try:
                fcntl.flock(report_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                parser.error("The benchmark is running; read its existing reports instead")
            build_report(root)
        return 0
    versions, envs, hardware = preflight(args)
    if args.check_only:
        print("Preflight OK: all three environments, Python modules, GNU time, gzip and source scripts are usable.")
        print(f"Requested sizes: {args.sizes}; CPUs: {args.cores}; repeats: {args.repeats}")
        return 0
    root.mkdir(parents=True, exist_ok=True)
    # flock is released by the OS after exit/crash; the lock file may safely remain.
    import fcntl
    lock = (root / ".benchmark.lock").open("a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise RuntimeError(f"Another benchmark is writing {root}")
    meta = root / "metadata"
    meta.mkdir(exist_ok=True)
    source = PACKAGE / "upstream"
    files = {}
    for p in sorted((source / "scripts").rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            files[str(p.relative_to(source))] = sha256(p)
    for name in ("run_benchmark.sh", "benchmark.py", "measure.py", "report.py", "benchmark.smk"):
        files["package/" + name] = sha256(PACKAGE / name)
    print("[INFO] Hashing and scanning the source FASTA...", flush=True)
    source_digest = sha256(args.input)
    selected, info = dataset_info(args.input, max(args.sizes))
    signature_data = {"input_sha256": source_digest, "source_files": files, "environments": envs,
                      "cores": args.cores, "sample_seconds": args.sample_seconds,
                      "hardware": {k: hardware[k] for k in ("platform", "cpus_available", "ram_bytes", "swap_bytes")},
                      "sampling": "prefix_in_original_order", "mafft": "--auto --thread CORES --threadit 0"}
    signature = hashlib.sha256(json.dumps(signature_data, sort_keys=True).encode()).hexdigest()
    exp_file = meta / "experiment.json"
    if exp_file.exists():
        previous = json.loads(exp_file.read_text(encoding="utf-8"))
        if previous["signature"] != signature:
            raise RuntimeError("Input, code, environments or measurement settings changed. Use a new EXPERIMENT_ROOT.")
        planned = sorted(set(previous["sizes"]) | set(args.sizes))
        repeat_count = max(previous["repeats"], args.repeats)
        # Expand a partial run to the full requested plan without losing earlier records.
        args.sizes, args.repeats = planned, repeat_count
        if len(selected) < min(max(planned), info["total_sequences"]):
            selected, info = dataset_info(args.input, max(planned))
    snapshot = meta / "workflow_snapshot"
    if not snapshot.exists():
        snapshot.mkdir()
        shutil.copytree(source / "scripts", snapshot / "scripts", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name in ("benchmark.smk", "measure.py", "benchmark.py", "report.py", "run_benchmark.sh"):
            shutil.copy2(PACKAGE / name, snapshot / name)
    # Refuse a partial or edited snapshot instead of silently mixing source versions.
    for key, expected in files.items():
        relative = key.removeprefix("package/")
        actual = snapshot / relative
        if not actual.is_file() or sha256(actual) != expected:
            raise RuntimeError(f"Snapshot missing/modified: {actual}; use a new EXPERIMENT_ROOT")
    experiment = {"signature": signature, "fingerprint": signature_data,
                  "input": str(Path(args.input).resolve()), "dataset": info,
                  "sizes": args.sizes, "repeats": args.repeats, "cores": args.cores,
                  "sampling": "prefix_in_original_order", "updated_utc": now(),
                  "hardware": hardware, "versions": versions}
    atomic_json(exp_file, experiment)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    atomic_json(meta / f"session_{stamp}.json", {"arguments": vars(args), "versions": versions,
                                               "hardware": hardware, "started_utc": now()})
    data = root / "data"
    data.mkdir(exist_ok=True)
    for n in args.sizes:
        if n <= info["total_sequences"]:
            save_subset(data / f"mtDNA_{n}.fasta", selected[:n])
    del selected
    import gc
    gc.collect()
    build_report(root)
    any_failed = False
    try:
        for n in args.sizes:
            if n > info["total_sequences"]:
                print(f"[SKIPPED_INSUFFICIENT_INPUT] requested={n}, available={info['total_sequences']}", flush=True)
                any_failed = True
                continue
            for rep in range(1, args.repeats + 1):
                success = run_one(args, root, data / f"mtDNA_{n}.fasta", n, rep, snapshot)
                if not success:
                    any_failed = True
                    if not args.continue_on_error:
                        print("Stopped after failure. Fix the cause, then run the same command to retry.", flush=True)
                        return 1
    except KeyboardInterrupt:
        print("Interrupted. Existing records were retained.", flush=True)
        return 130
    finally:
        build_report(root)
    print(f"Report: {root / 'experiment_report.html'}", flush=True)
    return 1 if any_failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
