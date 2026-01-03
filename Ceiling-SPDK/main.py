import subprocess
import json
import shutil
from pathlib import Path
import pandas as pd

from config import *
from prefill_spdk import prefill_device_spdk
from spdk_runner import run_spdk_perf
from monitor import run_with_cpu_monitoring_spdk
from utils import block_size_to_bytes, current_timestamp, safe_filename


def select_device_whiptail(devices):
    menu_items = []
    for idx, dev in enumerate(devices):
        menu_items += [f"{idx}", dev]

    cmd = ["whiptail", "--title", "Select NVMe Device", "--menu", "Choose a device:", "20", "78", "10"] + menu_items
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        idx = int(result.stdout.strip())
        return devices[idx]
    except Exception:
        print("Device selection cancelled or failed.")
        return None


def calculate_total_tests():
    return len(WORKLOADS) * len(BLOCK_SIZES) * len(QUEUE_DEPTHS) * len(NUMJOBS_LIST)


def save_json_result(output_dir, data, jobname):
    safe_jobname = safe_filename(jobname)
    json_path = output_dir / f"{safe_jobname}.json"
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)


def append_excel_result(excel_path, row):
    df = pd.DataFrame([row])
    if not excel_path.exists():
        df.to_excel(excel_path, index=False)
    else:
        existing = pd.read_excel(excel_path)
        combined = pd.concat([existing, df], ignore_index=True)
        combined.to_excel(excel_path, index=False)


def log_message(log_file, message):
    print(message)
    with open(log_file, "a") as f:
        f.write(message + "\n")


def main():
    print("🔍 Discovering SPDK NVMe devices...\n")
    from nvme_selector import list_spdk_nvme_devices
    devices = list_spdk_nvme_devices(SPDK_DIR)
    if not devices:
        print("No SPDK NVMe devices found.")
        return

    selected_device = select_device_whiptail(devices)
    if not selected_device:
        return

    print(f"Selected device: {selected_device}")

    # Create timestamped output directories
    timestamp = current_timestamp()
    output_base = Path(f"results_{TEST_TAG}_{timestamp}")
    output_base.mkdir(parents=True, exist_ok=True)

    output_dir = output_base / "json"
    raw_output_dir = output_base / "raw"
    output_dir.mkdir(exist_ok=True)
    raw_output_dir.mkdir(exist_ok=True)

    excel_path = output_base / f"{TEST_TAG}.xlsx"
    log_path = output_base / "log.txt"

    # Prefill if needed
    if any(w["needs_prefill"] for w in WORKLOADS):
        log_message(log_path, "Prefill required for some workloads, checking marker file...")
        prefill_device_spdk(selected_device, SPDK_DIR)

    total_tests = calculate_total_tests()
    test_id = 0

    for workload in WORKLOADS:
        for bs in BLOCK_SIZES:
            bs_bytes = block_size_to_bytes(bs)
            for qd in QUEUE_DEPTHS:
                for nj in NUMJOBS_LIST:
                    test_id += 1

                    mix_str = f"_mix{workload['rwmixread']}" if "rwmixread" in workload else ""
                    jobname = f"{workload['name']}{mix_str}_bs{bs}_qd{qd}_nj{nj}_{Path(selected_device).name}"
                    safe_jobname = safe_filename(jobname)
                    json_path = output_dir / f"{safe_jobname}.json"

                    progress = (test_id / total_tests) * 100
                    log_message(log_path, f"\nTest {test_id}/{total_tests} ({progress:.2f}%) → {jobname}")

                    if json_path.exists():
                        log_message(log_path, f"Skipping {jobname}, result already exists.")
                        continue

                    # Build SPDK perf command
                    perf_cmd = [
                        f"{SPDK_DIR}/build/examples/perf",
                        "-q", str(qd),
                        "-s", str(bs_bytes),
                        "-w", workload["rw"],
                        "-t", str(RUNTIME),
                        "-r", f"trtype:PCIe traddr:{selected_device}"
                    ]
                    if "rwmixread" in workload:
                        perf_cmd += ["--rwmixread", str(workload["rwmixread"])]

                    try:
                        output, avg_cpu, total_cpu = run_with_cpu_monitoring_spdk(
                            perf_cmd, output_dir=raw_output_dir, jobname=safe_jobname
                        )

                        metrics = run_spdk_perf(
                            SPDK_DIR,
                            selected_device,
                            bs_bytes,
                            qd,
                            nj,
                            workload,
                            RUNTIME,
                            raw_output_dir=raw_output_dir,
                            jobname=safe_jobname
                        )

                        result = {
                            "test_id": test_id,
                            "jobname": jobname,
                            "device": selected_device,
                            "workload": workload["name"],
                            "block_size": bs,
                            "queue_depth": qd,
                            "numjobs": nj,
                            "iops": metrics.get("iops"),
                            "latency": metrics.get("latency"),
                            "bandwidth": metrics.get("bandwidth"),
                            "cpu_avg": round(avg_cpu, 2),
                            "cpu_total": round(total_cpu, 2)
                        }

                        if ENABLE_JSON:
                            save_json_result(output_dir, result, jobname)
                            log_message(log_path, f"JSON saved: {json_path.name}")

                        if ENABLE_EXCEL:
                            append_excel_result(excel_path, result)
                            log_message(log_path, f"Excel row added: {jobname}")

                    except Exception as e:
                        log_message(log_path, f"ERROR in {jobname}: {e}")

    # Archive results
    archive_path = f"{output_base}.zip"
    shutil.make_archive(str(output_base), 'zip', output_base)
    log_message(log_path, f"\nAll tests complete. Results saved and archived to: {archive_path}")


if __name__ == "__main__":
    main()
