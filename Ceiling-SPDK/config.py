# config.py

# Path to SPDK root
SPDK_DIR = "/home/ali/spdk"

# Tag for output organization (useful for versioning or experiment names)
TEST_TAG = "spdk_dse_may28"

# Output paths
CSV_FILE = f"{TEST_TAG}.csv"  # Used as base for Excel: spdk_dse_may28.xlsx

# Test durations
RUNTIME = 60             # Benchmark runtime in seconds
PREFILL_RUNTIME = 120    # Prefill runtime in seconds (if needed)

# Feature toggles
ENABLE_JSON = True
ENABLE_EXCEL = True
ENABLE_CPU_MONITORING = True

# Friendly device name → PCIe address (used for info/display; actual selection is dynamic)
NVME_DEVICES = {
    "samsung": "c3:00.0",
    "optane": "c4:00.0"
}

# Block sizes to test (as string for human-readable config)
BLOCK_SIZES = ["2k", "4k", "8k", "16k"]

# Queue depths and parallel jobs
QUEUE_DEPTHS = [1, 4, 8, 16, 32]
NUMJOBS_LIST = [1, 2, 4, 8, 16]

# Workloads to test
WORKLOADS = [
    {"name": "randread",    "rw": "randread", "needs_prefill": True},
    {"name": "randwrite",   "rw": "randwrite", "needs_prefill": False},
    {"name": "randrw_30",   "rw": "randrw", "rwmixread": 30, "needs_prefill": True},
    {"name": "randrw_50",   "rw": "randrw", "rwmixread": 50, "needs_prefill": True},
    {"name": "randrw_70",   "rw": "randrw", "rwmixread": 70, "needs_prefill": True},
]
