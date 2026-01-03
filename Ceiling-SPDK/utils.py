# utils.py

import datetime
import re

def block_size_to_bytes(bs_str):
    """
    Convert a block size string like '4k', '1m', '1g', or '512' to bytes.
    """
    units = {"b": 1, "k": 1024, "m": 1024 ** 2, "g": 1024 ** 3}
    bs_str = bs_str.strip().lower()
    for unit, factor in units.items():
        if bs_str.endswith(unit):
            return int(bs_str[:-len(unit)]) * factor
    return int(bs_str)  # If no suffix, assume it's in bytes


def bytes_to_human(num_bytes):
    """
    Convert a byte value to a human-readable format like '4k', '1m'.
    """
    thresholds = [("g", 1024 ** 3), ("m", 1024 ** 2), ("k", 1024), ("b", 1)]
    for suffix, size in thresholds:
        if num_bytes >= size and num_bytes % size == 0:
            return f"{num_bytes // size}{suffix}"
    return str(num_bytes)


def current_timestamp():
    """
    Return the current timestamp string for filenames or logs.
    Format: YYYYMMDD_HHMMSS
    """
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_filename(name):
    """
    Sanitize a string to be safe for filesystem filenames.
    Removes or replaces problematic characters.
    """
    return re.sub(r'[^\w\-_.]', '_', name)
