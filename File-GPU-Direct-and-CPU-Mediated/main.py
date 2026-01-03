# main.py – design space exploration for GPU-Direct storage benchmarks
from pathlib import Path
import itertools, pandas as pd

from config import (
    DEVICES, FILESYSTEMS, BENCHMARK_LEVEL,
    BLOCK_SIZES, QUEUE_DEPTHS, NUMJOBS_LIST,
    IO_ENGINES, POLL_MODES, GPU_IDs,
    WORKLOADS, RUNTIME_SECONDS, SAVE_EXCEL, RESULT_DIR,
)

from fio_runner import (
    prepare_filesystem, prefill_file_if_needed, prefill_device_if_needed
    )
from monitor import run_with_cpu_monitoring


# ───────── helpers ─────────────────────────────────────────────────────────
def valid_poll(engine, mode):           # hipri/sqpoll only on io_uring
    return engine == "io_uring" or mode == "none"

def json_done(p: Path):                 # resume helper
    return p.is_file() and p.stat().st_size


# ───────── design space generator ─────────────────────────────────────────
def points():
    for dev in DEVICES:
        for fs in (FILESYSTEMS if BENCHMARK_LEVEL == "file" else ["raw"]):
            for wl in WORKLOADS:
                for bs in BLOCK_SIZES:
                    for eng in IO_ENGINES:
                        if BENCHMARK_LEVEL == "block" and eng == "libcufile":
                            continue
                        for poll in POLL_MODES:
                            if not valid_poll(eng, poll):
                                continue
                            for qd in QUEUE_DEPTHS:
                                for nj in NUMJOBS_LIST:
                                    for gpu in GPU_IDs:
                                        yield (dev, fs, wl, bs, eng, poll, qd, nj, gpu)


# ───────── output paths ───────────────────────────────────────────────────
results_dir = Path(RESULT_DIR)
results_dir.mkdir(exist_ok=True, parents=True)
partial_csv = results_dir / "partial_results.csv"
excel_path  = results_dir / "dse_results.xlsx"

prefilled, results = set(), []
pts = list(points())
print(f"Total tests: {len(pts)}")

# ───────── main loop ──────────────────────────────────────────────────────
for done, (dev, fs, wl, bs, eng, poll, qd, nj, gpu) in enumerate(pts, 1):

    # pick target
    if BENCHMARK_LEVEL == "file":
        testfile = prepare_filesystem(dev, fs)
        target   = testfile
        pre_key  = testfile
    else:
        target   = dev
        pre_key  = dev

    # optional pre‑fill
    if wl["needs_prefill"] and pre_key not in prefilled:
        (prefill_file_if_needed if BENCHMARK_LEVEL == "file"
         else prefill_device_if_needed)(target)
        prefilled.add(pre_key)

    # build jobinfo
    job_info = {
        "filename": str(target), "device": dev, "fs": fs, "workload": wl,
        "bs": bs, "engine": eng, "poll": poll, "qd": qd, "nj": nj,
        "gpu_id": gpu, "runtime": RUNTIME_SECONDS
    }

    # resume?
    stem     = f"{wl['name']}_{bs}_{eng}_poll{poll}_qd{qd}_nj{nj}_{fs}"
    out_json = results_dir / f"{stem}.json"
    if json_done(out_json):
        print(f"skip {stem}")
        continue
    job_info["result_json"] = str(out_json)

    print(f"[{done}/{len(pts)}] {stem}")

    # run fio + monitor
    res = run_with_cpu_monitoring(job_info)
    if res:
        results.append(res)
        pd.DataFrame([res]).to_csv(
            partial_csv, mode="a", header=not partial_csv.exists(), index=False
        )

# ───────── excel export ───────────────────────────────────────────────────
if SAVE_EXCEL and results:
    pd.DataFrame(results).to_excel(excel_path, index=False)
    print(f"Excel → {excel_path}")
else:
    print("no results or Excel disabled")
