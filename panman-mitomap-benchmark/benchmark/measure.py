#!/usr/bin/env python3
"""Measure a command without a shell; intended for Linux/WSL."""
import argparse
import csv
import datetime as dt
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import time


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def atomic_json(path, data):
    path = Path(path)
    tmp = path.with_name(path.name + ".partial")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def terminate_tree(proc):
    import psutil
    try:
        root = psutil.Process(proc.pid)
        descendants = root.children(recursive=True)
    except psutil.Error:
        descendants = []
    # Descendants may start their own sessions, so kill by process objects too.
    for child in reversed(descendants):
        try:
            child.terminate()
        except psutil.Error:
            pass
    try:
        proc.terminate()
    except ProcessLookupError:
        pass
    _, alive = psutil.wait_procs(descendants, timeout=5)
    for child in alive:
        try:
            child.kill()
        except psutil.Error:
            pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def run_measure(command, name, cwd, interval=1.0, stdout_path=None):
    import psutil
    cwd = Path(cwd).resolve()
    logs = cwd / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log_path = logs / f"{name}.log"
    time_path = logs / f"{name}.time.txt"
    sample_path = logs / f"{name}.resources.tsv"
    (logs / f"{name}.command.txt").write_text(shlex.join(command) + "\n", encoding="utf-8")
    result = {"stage": name, "started_utc": now(), "command": command,
              "cwd": str(cwd), "sample_seconds": interval, "exit_code": None}
    peak = 0
    samples = 0
    proc = None
    interrupted = False
    t0 = time.monotonic()
    old_term = signal.getsignal(signal.SIGTERM)
    def stop(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        with log_path.open("wb") as log, sample_path.open("w", newline="", encoding="utf-8") as sf:
            writer = csv.writer(sf, delimiter="\t")
            writer.writerow(["elapsed_seconds", "process_tree_rss_bytes", "process_count", "host_available_bytes"])
            out = log
            if stdout_path:
                target = Path(stdout_path)
                if not target.is_absolute():
                    target = cwd / target
                target.parent.mkdir(parents=True, exist_ok=True)
                out = target.open("wb")
            try:
                env = os.environ.copy()
                env["LC_ALL"] = "C"
                timed = ["/usr/bin/time", "-f", "wall_seconds=%e\nuser_seconds=%U\nsystem_seconds=%S\nmaxrss_kib=%M\nexit_code=%x", "-o", str(time_path), "--", *command]
                proc = subprocess.Popen(timed, cwd=cwd, stdout=out, stderr=log,
                                        env=env, start_new_session=True)
                root = psutil.Process(proc.pid)
                while True:
                    members = []
                    try:
                        members = [root, *root.children(recursive=True)]
                    except psutil.Error:
                        pass
                    rss = count = 0
                    for member in members:
                        try:
                            rss += member.memory_info().rss
                            count += 1
                        except psutil.Error:
                            pass
                    peak = max(peak, rss)
                    samples += 1
                    writer.writerow([round(time.monotonic() - t0, 6), rss, count,
                                     psutil.virtual_memory().available])
                    sf.flush()
                    try:
                        result["exit_code"] = proc.wait(timeout=interval)
                        break
                    except subprocess.TimeoutExpired:
                        pass
            finally:
                if out is not log:
                    out.close()
    except KeyboardInterrupt:
        interrupted = True
        result["exit_code"] = 130
        if proc is not None:
            terminate_tree(proc)
    except Exception as exc:
        result["exit_code"] = 1
        result["error"] = f"{type(exc).__name__}: {exc}"
        if proc is not None and proc.poll() is None:
            terminate_tree(proc)
    finally:
        signal.signal(signal.SIGTERM, old_term)
        result.update(ended_utc=now(), elapsed_seconds=round(time.monotonic() - t0, 6),
                      sampled_tree_peak_rss_bytes=peak, samples=samples)
        if time_path.exists():
            for line in time_path.read_text(errors="replace").splitlines():
                key, sep, value = line.partition("=")
                if sep and key in {"wall_seconds", "user_seconds", "system_seconds", "maxrss_kib"}:
                    try:
                        result["gnu_" + key] = float(value)
                    except ValueError:
                        pass
        atomic_json(logs / f"{name}.metrics.json", result)
    if interrupted:
        raise KeyboardInterrupt
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--interval", type=float, default=1)
    parser.add_argument("--stdout")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or args.interval <= 0:
        parser.error("A command and positive interval are required")
    try:
        metrics = run_measure(command, args.name, Path.cwd(), args.interval, args.stdout)
        raise SystemExit(metrics["exit_code"] if metrics["exit_code"] >= 0 else 1)
    except KeyboardInterrupt:
        raise SystemExit(130)
