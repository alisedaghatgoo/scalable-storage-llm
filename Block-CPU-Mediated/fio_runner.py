# fio_runner.py
import subprocess
from pathlib import Path
from config import RUNTIME_SECONDS, USE_DIRECT

results_dir = Path("results")


def prefill_device_if_needed(device):
    print(f"[Pre-fill] Writing on {device} for read benchmarks ...")
    subprocess.run([
        "fio", "--name=prefill",
        f"--filename={device}",
        "--rw=write",
        "--bs=128k",
        "--iodepth=32",
        "--numjobs=4",
        "--time_based",
        f"--runtime={RUNTIME_SECONDS}",
        f"--direct={int(USE_DIRECT)}",
        "--ioengine=libaio",
        "--group_reporting"
    ])
    print("[Pre-fill] Done.")


def build_fio_command(job_info):
    device = job_info["device"]
    workload = job_info["workload"]
    bs = job_info["bs"]
    engine = job_info["engine"]
    poll = job_info["poll"]
    qd = job_info["qd"]
    nj = job_info["nj"]

    if device.startswith("/dev/pmem") and poll in ["hipri", "full"]:
        print(f"skip, {device} is not supporting '{poll}' mode.")
        return None, None, None

    jobname = f"{workload['name']}_bs{bs}_eng{engine}_poll{poll}_qd{qd}_nj{nj}_{Path(device).name}"
    output_file = results_dir / f"{jobname}.json"

    cmd = [
        "fio",
        f"--name={jobname}",
        f"--filename={device}",
        f"--rw={workload['rw']}",
        f"--bs={bs}",
        f"--iodepth={qd}",
        f"--numjobs={nj}",
        "--time_based",
        f"--runtime={RUNTIME_SECONDS}",
        f"--direct={int(USE_DIRECT)}",
        f"--ioengine={engine}",
        "--group_reporting",
        "--output-format=json",
        f"--output={output_file}"
    ]

    if "rwmixread" in workload:
        cmd.append(f"--rwmixread={workload['rwmixread']}")

    if engine == "io_uring":
        if poll in ["hipri", "full"]:
            cmd.append("--hipri")
        if poll in ["sqpoll", "full"]:
            cmd.append("--sqthread_poll=1")
            cmd.append("--registerfiles=1")

    return cmd, output_file, jobname
