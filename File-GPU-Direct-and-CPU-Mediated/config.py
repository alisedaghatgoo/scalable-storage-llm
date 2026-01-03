# ---------------------------------------------------------------------------
# Storage target(s)
# ---------------------------------------------------------------------------
DEVICES = [
    "/dev/nvme0n1",          # add more drives here
]
BENCHMARK_LEVEL = "file" # "file" or "block"

# ---------------------------------------------------------------------------
# Filesystems to benchmark when BENCHMARK_LEVEL == "file"
# Only XFS and EXT4 are certified for GPUDirect Storage; leave
# unsupported FSes here only if you WANT to trigger the CPU fallback path.
# ---------------------------------------------------------------------------
FILESYSTEMS = ["xfs", "ext4"]
TEST_FILE_NAME = "testfile.dat"  # Name of the test file to be created on the device
MOUNT_BASE = "/mnt/fio"

# Size of the test file (used only when BENCHMARK_LEVEL == "file")
#  - "auto" : fills drive except 4 MiB slack
#  - "50%"  : half the free space
#  - int    : explicit bytes, e.g. 50*1024**3
TEST_FILE_SIZE = "auto"
# ---------------------------------------------------------------------------
# Workload matrix
# ---------------------------------------------------------------------------
BLOCK_SIZES   = ["4k", "16k", "1m"]          # 2 kB blocks are < 4 kB sector size
QUEUE_DEPTHS  = [1, 4, 8, 16, 32]
NUMJOBS_LIST  = [1, 2, 4, 8, 16]

POLL_MODES = ["none", "hipri", "sqpoll", "full"]  # (hipri, sqpoll, and full will be ignored by libcufile)

IO_ENGINES = [
    "libcufile",            # GPU zero‑copy
    "io_uring",             # GPU copy via gpu_copy_runner
    "libaio",               # GPU copy via gpu_copy_runner
]

WORKLOADS = [
    {"name": "randwrite", "rw": "randwrite", "needs_prefill": False},
    {"name": "randread", "rw": "randread", "needs_prefill": True},
    {"name": "randrw_30", "rw": "randrw",   "rwmixread": 30, "needs_prefill": True},
    {"name": "randrw_50", "rw": "randrw",   "rwmixread": 50, "needs_prefill": True},
    {"name": "randrw_70", "rw": "randrw",   "rwmixread": 70, "needs_prefill": True},
]

# ---------------------------------------------------------------------------
# Run‑time knobs
# --------------------------------------------------------------

SAVE_EXCEL = True
RUNTIME_SECONDS = 300
USE_DIRECT = True
ENABLE_RESUME = True
GPU_IDs = [0]
LOG_LEVEL = "INFO"
RESULT_DIR = "./results"