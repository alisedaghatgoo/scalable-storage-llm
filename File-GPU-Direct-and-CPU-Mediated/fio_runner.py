# fio_runner.py
import subprocess, shlex
from pathlib import Path
from config import (
    RUNTIME_SECONDS, USE_DIRECT,
    TEST_FILE_SIZE, TEST_FILE_NAME, MOUNT_BASE,
)

results_dir = Path("results")
MOUNT_BASE  = Path(MOUNT_BASE)


# ──────────────────────────────────────────────────────────────────────
def prepare_filesystem(device: str, fs: str) -> Path:
    """
    mkfs.<fs>  →  mount  →  create/resize TEST_FILE_NAME
    Return Path to the file
    """
    devname    = Path(device).name
    mountpoint = MOUNT_BASE / f"{devname}_{fs}"
    mountpoint.mkdir(parents=True, exist_ok=True)

    subprocess.run(["sudo", f"mkfs.{fs}", "-F", device], check=True)
    subprocess.run(["sudo", "umount", "-fl", device], check=False)
    subprocess.run(["sudo", "mount", "-o", "noatime", device, mountpoint], check=True)

    free_kib = int(subprocess.check_output(
        ["df", "--output=avail", "-k", str(mountpoint)]).splitlines()[-1])

    if TEST_FILE_SIZE == "auto":
        bytes_needed = free_kib * 1024 - 4 * 1024**2
    elif isinstance(TEST_FILE_SIZE, str) and TEST_FILE_SIZE.endswith("%"):
        pct = float(TEST_FILE_SIZE.rstrip("%")) / 100.0
        bytes_needed = int(free_kib * 1024 * pct)
    else:
        bytes_needed = int(TEST_FILE_SIZE)

    testfile = mountpoint / TEST_FILE_NAME
    if not testfile.exists() or testfile.stat().st_size != bytes_needed:
        print(f"[Create] allocating {bytes_needed/1024**3:.1f} GiB → {testfile}")
        subprocess.run(["sudo", "fallocate", "-l", str(bytes_needed), testfile], check=True)

    return testfile


# ──────────────────────────────────────────────────────────────────────
def prefill_device_if_needed(device: str):
    """Sequentially write the whole block device once."""
    print(f"[Pre‑fill] writing {device} …")
    subprocess.run([
        "fio", "--name=prefill", f"--filename={device}",
        "--rw=write", "--bs=128k", "--iodepth=32", "--numjobs=4",
        "--time_based", f"--runtime={RUNTIME_SECONDS}",
        f"--direct={int(USE_DIRECT)}", "--ioengine=libaio",
        "--group_reporting"
    ], check=True)
    print("[Pre‑fill] done.")


def prefill_file_if_needed(file_path: str):
    """Sequentially write a test file once (for randread workloads)."""
    print(f"[Pre‑fill] writing {file_path} …")
    subprocess.run([
        "fio", "--name=prefill", f"--filename={file_path}",
        "--rw=write", "--bs=128k", "--iodepth=32", "--numjobs=4",
        "--time_based", f"--runtime={RUNTIME_SECONDS}",
        f"--direct={int(USE_DIRECT)}", "--ioengine=libaio",
        "--group_reporting"
    ], check=True)
    print("[Pre‑fill] done.")


# ──────────────────────────────────────────────────────────────────────
def build_fio_command(job_info):
    """Return (cmd:list, output_file:Path, jobname:str)"""
    filename = job_info["filename"]
    device   = job_info["device"]
    wl       = job_info["workload"]
    bs, eng, poll, qd, nj = job_info["bs"], job_info["engine"], job_info["poll"], job_info["qd"], job_info["nj"]

    if device.startswith("/dev/pmem") and poll in ["hipri", "full"]:
        print(f"[Skip] {device} does not support poll '{poll}'")
        return None, None, None

    jobname     = f"{wl['name']}_bs{bs}_eng{eng}_poll{poll}_qd{qd}_nj{nj}_{Path(filename).parts[-2]}"
    output_file = results_dir / f"{jobname}.json"

    cmd = [
        "fio",
        f"--name={jobname}",
        f"--filename={filename}",
        f"--rw={wl['rw']}",
        f"--bs={bs}",
        f"--iodepth={qd}",
        f"--numjobs={nj}",
        "--time_based",
        f"--runtime={RUNTIME_SECONDS}",
        f"--direct={int(USE_DIRECT)}",
        f"--ioengine={eng}",
        "--group_reporting",
        "--output-format=json",
        f"--output={output_file}"
    ]

    if "rwmixread" in wl:
        cmd.append(f"--rwmixread={wl['rwmixread']}")

    if eng == "io_uring":
        if poll in ["hipri", "full"]:
            cmd.append("--hipri")
        if poll in ["sqpoll", "full"]:
            cmd += ["--sqthread_poll=1", "--registerfiles=1"]
    elif eng == "libcufile":
        cmd += ["--cuda_io=cufile", "--gpu_dev_ids=0"]

    return cmd, output_file, jobname
