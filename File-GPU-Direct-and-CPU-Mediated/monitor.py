# monitor.py
import psutil
import threading
import time
import json
import subprocess
from pathlib import Path
from config import ENABLE_RESUME
from fio_runner import build_fio_command


def monitor_process_cpu(proc, interval, stop_event, cpu_usages):
    try:
        p = psutil.Process(proc.pid)

        p.cpu_percent(interval=None)

        print("fio job started, monitoring CPU usage...")
        time.sleep(0.5) 

        for sub in [p] + p.children(recursive=True):
            try:
                sub.cpu_percent(interval=None)
            except psutil.NoSuchProcess:
                continue

        while not stop_event.is_set():
            total = 0.0
            processes = [p] + p.children(recursive=True)
            for proc_ in processes:
                try:
                    total += proc_.cpu_percent(interval=0.1)
                except psutil.NoSuchProcess:
                    continue

            cpu_usages.append(total)
            time.sleep(0.9)

    except Exception as e:
        print(f"Error in monitoring CPU: {e}")


def run_with_cpu_monitoring(job_info):
    cpu_usages = []
    stop_event = threading.Event()

    fio_cmd, output_file_path, jobname = build_fio_command(job_info)

    if output_file_path is None:
        return None

    if ENABLE_RESUME and output_file_path.exists():
        print(f"[Resume] The test case is available from before {output_file_path.name}, skipping...")
        return None

    try:
        proc = subprocess.Popen(fio_cmd)
        monitor_thread = threading.Thread(target=monitor_process_cpu, args=(proc, 1.0, stop_event, cpu_usages))
        monitor_thread.start()

        proc.wait()
        stop_event.set()
        monitor_thread.join()

    except Exception as e:
        print(f"[Error] in running FIO: {e}")
        return None

    try:
        with open(output_file_path) as f:
            data = json.load(f)

        read_iops = data['jobs'][0]['read']['iops']
        write_iops = data['jobs'][0]['write']['iops']
        total_iops = read_iops + write_iops

        latency = data['jobs'][0]['read']['lat_ns']['mean'] if read_iops > 0 else data['jobs'][0]['write']['lat_ns']['mean']
        bw = data['jobs'][0]['read']['bw'] + data['jobs'][0]['write']['bw']

        sample_count = len(cpu_usages)
        trimmed = cpu_usages[int(sample_count * 0.05): int(sample_count * 0.95)]
        avg_cpu = sum(trimmed) / len(trimmed) if trimmed else 0.0
        total_cpu = sum(trimmed) if trimmed else 0.0

        return {
            "device": job_info['device'],
            "workload": job_info['workload']['name'],
            "block_size": job_info['bs'],
            "engine": job_info['engine'],
            "poll": job_info['poll'],
            "iodepth": job_info['qd'],
            "numjobs": job_info['nj'],
            "iops": total_iops,
            "latency_ns": latency,
            "bandwidth_kbps": bw,
            "cpu_usage_avg": round(avg_cpu, 2),
            "cpu_usage_total": round(total_cpu, 2)
        }

    except Exception as e:
        print(f"Error in reading or processing FIO output: {e}")
        return None
