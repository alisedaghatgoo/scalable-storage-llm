# config.py

DEVICES = [
    "/dev/pmem0",
]

BLOCK_SIZES = ["2k", "4k", "8k", "16k"]

IO_ENGINES = ["libaio", "io_uring"]

# only for io uring
POLL_MODES = ["none", "hipri", "sqpoll", "full"]  # full = hipri + sqpoll

WORKLOADS = [
    {"name": "randread", "rw": "randread", "needs_prefill": True},
    {"name": "randwrite", "rw": "randwrite", "needs_prefill": False},
    {"name": "randrw_30", "rw": "randrw", "rwmixread": 30, "needs_prefill": True},
    {"name": "randrw_50", "rw": "randrw", "rwmixread": 50, "needs_prefill": True},
    {"name": "randrw_70", "rw": "randrw", "rwmixread": 70, "needs_prefill": True},
]


WORKLOADS = [
    {"name": "randread", "rw": "randread", "needs_prefill": True},
    {"name": "randwrite", "rw": "randwrite", "needs_prefill": False},
    {"name": "randrw_10", "rw": "randrw", "rwmixread": 10, "needs_prefill": True},
    {"name": "randrw_20", "rw": "randrw", "rwmixread": 20, "needs_prefill": True},
    {"name": "randrw_40", "rw": "randrw", "rwmixread": 40, "needs_prefill": True},
    {"name": "randrw_60", "rw": "randrw", "rwmixread": 60, "needs_prefill": True},
    {"name": "randrw_80", "rw": "randrw", "rwmixread": 80, "needs_prefill": True},
    {"name": "randrw_80", "rw": "randrw", "rwmixread": 90, "needs_prefill": True},
]


# queue depth, numjobs
QUEUE_DEPTHS = [1, 4, 8, 16, 32]
NUMJOBS_LIST = [1, 2, 4, 8, 16]

SAVE_EXCEL = True

RUNTIME_SECONDS = 300

USE_DIRECT = True

ENABLE_RESUME = True