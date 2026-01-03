# main.py
import itertools
from config import DEVICES, BLOCK_SIZES, IO_ENGINES, POLL_MODES, WORKLOADS, QUEUE_DEPTHS, NUMJOBS_LIST, SAVE_EXCEL
from fio_runner import prefill_device_if_needed
from monitor import run_with_cpu_monitoring
import pandas as pd
from pathlib import Path

results_dir = Path("results")
results_dir.mkdir(parents=True, exist_ok=True)
output_csv_path = Path("output/partial_results.csv")
output_csv_path.parent.mkdir(parents=True, exist_ok=True)

def count_total_tests():
    total = 0
    for device in DEVICES:
        for workload in WORKLOADS:
            for bs in BLOCK_SIZES:
                for engine in IO_ENGINES:
                    applicable_polls = POLL_MODES if engine == "io_uring" else ["none"]
                    for poll in applicable_polls:
                        for qd in QUEUE_DEPTHS:
                            for nj in NUMJOBS_LIST:
                                total += 1
    return total

all_results = []
device_prefilled = {}
total_tests = count_total_tests()
completed_tests = 0

print(f"All test cases: {total_tests}")

for device in DEVICES:
    for workload in WORKLOADS:
        workload_name = workload['name']
        needs_prefill = workload.get('needs_prefill', False)

        if needs_prefill and not device_prefilled.get(device):
            prefill_device_if_needed(device)
            device_prefilled[device] = True

        for bs, engine in itertools.product(BLOCK_SIZES, IO_ENGINES):
            applicable_polls = POLL_MODES if engine == "io_uring" else ["none"]

            for poll, qd, nj in itertools.product(applicable_polls, QUEUE_DEPTHS, NUMJOBS_LIST):
                job_info = {
                    "device": device,
                    "workload": workload,
                    "bs": bs,
                    "engine": engine,
                    "poll": poll,
                    "qd": qd,
                    "nj": nj,
                }

                completed_tests += 1
                print(f"Case {completed_tests}/{total_tests} is running ...", flush=True)

                result = run_with_cpu_monitoring(job_info)
                if result:
                    all_results.append(result)

                    df = pd.DataFrame([result])
                    df.to_csv(output_csv_path, mode='a', index=False, header=not output_csv_path.exists())

                percent_done = (completed_tests / total_tests) * 100
                print(f"Progress: {completed_tests}/{total_tests} ({percent_done:.1f}%)\n", flush=True)

if SAVE_EXCEL:
    df = pd.DataFrame(all_results)
    df.to_excel("output/dse_results.xlsx", index=False)
    print("Results saved.")
else:
    print("Excel output saving was disabled.")