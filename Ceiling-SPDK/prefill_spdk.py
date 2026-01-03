# prefill_spdk.py

import subprocess
import json
import sys
import time
from pathlib import Path
from config import SPDK_DIR, PREFILL_RUNTIME
from utils import block_size_to_bytes, current_timestamp, safe_filename
from multiprocessing import Pool

TEMP_BDEV_NAME = "prefill_nvme"
BLOCK_SIZE = "128k"
MARKER_DIR = Path("prefill_status")
MARKER_DIR.mkdir(exist_ok=True)


def log(msg):
    print(f"[SPDK Prefill] {msg}")


def run_rpc(spdk_dir, args):
    rpc = f"{spdk_dir}/scripts/rpc.py"
    try:
        result = subprocess.run([rpc] + args, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"RPC failed: {' '.join(e.cmd)}\n{e.stderr.strip()}")


def get_device_size_bytes(spdk_dir: str, traddr: str) -> int:
    run_rpc(spdk_dir, [
        "bdev_nvme_attach_controller",
        "-b", TEMP_BDEV_NAME,
        "-t", "PCIe",
        "-a", traddr
    ])
    output = run_rpc(spdk_dir, ["bdev_get_bdevs"])
    bdevs = json.loads(output)
    for bdev in bdevs:
        if bdev["name"].startswith(TEMP_BDEV_NAME):
            return int(bdev["num_blocks"]) * int(bdev["block_size"])
    raise RuntimeError("Could not determine device size from SPDK")


def is_already_prefilled(traddr: str) -> Path:
    marker_file = MARKER_DIR / f"{safe_filename(traddr)}.json"
    return marker_file if marker_file.exists() else None


def mark_prefilled(traddr: str, size, duration):
    marker = MARKER_DIR / f"{safe_filename(traddr)}.json"
    with open(marker, "w") as f:
        json.dump({
            "traddr": traddr,
            "size_bytes": size,
            "duration_sec": duration,
            "timestamp": current_timestamp()
        }, f, indent=2)


def prefill_device_spdk(traddr: str, spdk_dir: str, force=False):
    log(f"Requested prefill: {traddr}")

    marker = is_already_prefilled(traddr)
    if marker and not force:
        log(f"Already prefilled (marker exists): {marker.name}")
        return

    try:
        log("Attaching and determining size...")
        size_bytes = get_device_size_bytes(spdk_dir, traddr)
        bs_bytes = block_size_to_bytes(BLOCK_SIZE)
        log(f"Device size: {size_bytes / (1024**3):.2f} GB, block size: {BLOCK_SIZE}")

        log("Starting prefill write...")
        start_time = time.time()

        perf_cmd = [
            f"{spdk_dir}/build/examples/perf",
            "-q", "32",
            "-s", str(bs_bytes),
            "-w", "write",
            "-t", str(PREFILL_RUNTIME),
            "-r", f"trtype:PCIe traddr:{traddr}"
        ]

        subprocess.run(perf_cmd, check=True)
        elapsed = round(time.time() - start_time, 2)

        log(f"Prefill complete in {elapsed}s")
        mark_prefilled(traddr, size_bytes, elapsed)

    except Exception as e:
        log(f"Error: {e}")

    finally:
        log("Detaching controller...")
        try:
            run_rpc(spdk_dir, ["bdev_nvme_detach_controller", "-b", TEMP_BDEV_NAME])
            log("Detached successfully.")
        except Exception as e:
            log(f"Detach failed: {e}")


# Optional: Prefill multiple in parallel
def prefill_many(traddrs: list, force=False, parallel=False):
    args_list = [(traddr, SPDK_DIR, force) for traddr in traddrs]
    if parallel:
        with Pool(len(traddrs)) as pool:
            pool.starmap(prefill_device_spdk, args_list)
    else:
        for args in args_list:
            prefill_device_spdk(*args)


# CLI usage
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python prefill_spdk.py <traddr1> [traddr2 ...] [--force] [--parallel]")
        sys.exit(1)

    force = "--force" in sys.argv
    parallel = "--parallel" in sys.argv
    traddrs = [arg for arg in sys.argv[1:] if not arg.startswith("--")]

    prefill_many(traddrs, force=force, parallel=parallel)


# Prefill 2 devices (serial)
# python prefill_spdk.py c3:00.0 c4:00.0

# Force prefill again
# python prefill_spdk.py c3:00.0 --force

# Parallel prefill
# python prefill_spdk.py c3:00.0 c4:00.0 --parallel
