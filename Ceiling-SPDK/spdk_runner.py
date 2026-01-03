import subprocess
import re
from pathlib import Path


def run_spdk_perf(spdk_dir, traddr, block_size, queue_depth, numjobs, workload, duration, raw_output_dir=None, jobname=None):
    """
    Executes SPDK perf and returns parsed performance metrics.
    Optionally saves raw output to file if `raw_output_dir` and `jobname` are provided.
    """
    perf_path = f"{spdk_dir}/build/examples/perf"

    cmd = [
        perf_path,
        "-q", str(queue_depth),
        "-s", str(block_size),
        "-w", workload["rw"],
        "-t", str(duration),
        "-r", f"trtype:PCIe traddr:{traddr}"
    ]

    if "rwmixread" in workload:
        cmd += ["--rwmixread", str(workload["rwmixread"])]

    print(f"[SPDK Runner] Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout

        # Save raw output if desired
        if raw_output_dir and jobname:
            raw_output_dir = Path(raw_output_dir)
            raw_output_dir.mkdir(parents=True, exist_ok=True)
            raw_file = raw_output_dir / f"{jobname}.txt"
            with open(raw_file, "w") as f:
                f.write(output)

        parsed = parse_perf_output(output)
        parsed["raw_output"] = output
        return parsed

    except subprocess.CalledProcessError as e:
        print(f"[SPDK Runner] Error running perf:\n{e.stderr}")
        return {
            "iops": None,
            "latency": None,
            "bandwidth": None,
            "raw_output": e.stderr,
            "error": e.stderr.strip()
        }


def parse_perf_output(output: str) -> dict:
    """
    Parses key metrics from SPDK perf output.
    Returns a dictionary with IOPS, average latency (us), and bandwidth (MiB/s).
    """
    metrics = {
        "iops": None,
        "latency": None,
        "bandwidth": None
    }

    for line in output.splitlines():
        # Match IOPS
        iops_match = re.search(r"IOPS\s*=\s*([\d\.]+)\s*([kKmMgG]?)", line)
        if iops_match:
            value, suffix = iops_match.groups()
            metrics["iops"] = normalize_number(value, suffix)

        # Match average latency
        lat_match = re.search(r"clat\s+min/avg/max\s*=\s*\S+/(\S+)/", line)
        if lat_match:
            try:
                metrics["latency"] = float(lat_match.group(1))
            except ValueError:
                pass

        # Match Bandwidth
        bw_match = re.search(r"BW\s*=\s*([\d\.]+)\s*([A-Za-z]{2,4})/s", line)
        if bw_match:
            val, unit = bw_match.groups()
            metrics["bandwidth"] = normalize_bandwidth(val, unit)

    return metrics


def normalize_number(value: str, suffix: str) -> float:
    """
    Converts values with suffixes K, M, G into float.
    """
    try:
        value = float(value)
        multipliers = {
            "": 1,
            "k": 1e3, "K": 1e3,
            "m": 1e6, "M": 1e6,
            "g": 1e9, "G": 1e9,
        }
        return round(value * multipliers.get(suffix, 1), 2)
    except ValueError:
        return None


def normalize_bandwidth(val: str, unit: str) -> float:
    """
    Converts bandwidth to MiB/s.
    """
    try:
        val = float(val)
        unit = unit.strip().lower()

        factor_map = {
            "kib": 1 / 1024,
            "kb": 1 / 1000,
            "mib": 1.0,
            "mb": 1000 / 1024,
            "gib": 1024.0,
            "gb": 1e6 / 1024,
        }

        for prefix in factor_map:
            if unit.startswith(prefix):
                return round(val * factor_map[prefix], 2)

        return round(val, 2)

    except ValueError:
        return None
