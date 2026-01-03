# monitor.py

import psutil
import threading
import time
import subprocess
import csv
from config import SAVE_CPU_TIMELINE


def monitor_process_cpu(proc, stop_event, cpu_usages, sample_interval=1.0, save_per_core=False):
    """
    Monitors total CPU usage of proc and its children. Optionally captures per-core stats.
    """
    try:
        p = psutil.Process(proc.pid)

        # Warm-up
        p.cpu_percent(interval=None)
        time.sleep(0.3)
        for sub in [p] + p.children(recursive=True):
            try:
                sub.cpu_percent(interval=None)
            except psutil.NoSuchProcess:
                continue

        while not stop_event.is_set():
            usage = 0.0
            for child in [p] + p.children(recursive=True):
                try:
                    usage += child.cpu_percent(interval=0.1)
                except psutil.NoSuchProcess:
                    continue

            timestamp = time.time()
            if save_per_core:
                percpu = psutil.cpu_percent(interval=None, percpu=True)
                cpu_usages.append((timestamp, usage, percpu))
            else:
                cpu_usages.append((timestamp, usage))

            time.sleep(sample_interval - 0.1)

    except Exception as e:
        print(f"[Monitor] CPU monitoring error: {e}")


def trim_and_average(samples, trim_ratio=0.1):
    """
    Trims first/last X% and computes average and total CPU usage.
    """
    if not samples:
        return 0.0, 0.0
    usage_values = [s[1] for s in samples]  # only total usage
    n = len(usage_values)
    start = int(n * trim_ratio)
    end = int(n * (1 - trim_ratio))
    trimmed = usage_values[start:end] if end > start else usage_values
    avg = sum(trimmed) / len(trimmed) if trimmed else 0.0
    return round(avg, 2), round(sum(trimmed), 2)


def save_cpu_timeline(samples, output_dir, jobname):
    """
    Save the full CPU usage timeline to a CSV.
    """
    output_dir.mkdir(exist_ok=True, parents=True)
    path = output_dir / f"{jobname}_cpu_timeline.csv"

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        headers = ["timestamp", "total_cpu"]
        if isinstance(samples[0], tuple) and len(samples[0]) == 3:
            core_count = len(samples[0][2])
            headers += [f"core_{i}" for i in range(core_count)]
        writer.writerow(headers)

        for sample in samples:
            if len(sample) == 2:
                writer.writerow([sample[0], sample[1]])
            else:
                writer.writerow([sample[0], sample[1], *sample[2]])


def run_with_cpu_monitoring_spdk(perf_cmd, sample_interval=1.0, output_dir=None, jobname=None):
    """
    Runs SPDK perf command with CPU monitoring.
    Returns: stdout, avg_cpu, total_cpu
    """
    cpu_usages = []
    stop_event = threading.Event()

    try:
        proc = subprocess.Popen(perf_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        monitor_thread = threading.Thread(
            target=monitor_process_cpu,
            args=(proc, stop_event, cpu_usages, sample_interval, SAVE_CPU_TIMELINE)
        )
        monitor_thread.start()

        stdout, stderr = proc.communicate()
        stop_event.set()
        monitor_thread.join()

        avg_cpu, total_cpu = trim_and_average(cpu_usages)

        if SAVE_CPU_TIMELINE and output_dir and jobname:
            save_cpu_timeline(cpu_usages, output_dir, jobname)

        return stdout, avg_cpu, total_cpu

    except Exception as e:
        print(f"[Monitor] Failed to run and monitor SPDK perf: {e}")
        return "", 0.0, 0.0
