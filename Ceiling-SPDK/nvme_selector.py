# nvme_selector.py

import subprocess
import re


def list_spdk_nvme_devices(spdk_dir: str) -> list:
    """
    Parses the SPDK setup.sh status output and extracts NVMe PCIe addresses
    bound to UIO or VFIO drivers.
    Returns list of tuples: (pci_addr, driver)
    """
    status_script = f"{spdk_dir}/scripts/setup.sh"
    try:
        result = subprocess.run([status_script, "status"], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print("Error running setup.sh:", e)
        return []

    devices = []
    for line in result.stdout.splitlines():
        line = line.strip()
        # Example: 0000:c3:00.0 (8086 a52b) uio_pci_generic
        match = re.match(r"^(0000:[0-9a-f]{2}:[0-9a-f]{2}\.\d+).+\s+(\w+)$", line, re.IGNORECASE)
        if match:
            pci_addr, driver = match.groups()
            if driver.lower() in ("uio_pci_generic", "vfio-pci"):
                devices.append((pci_addr, driver))

    return devices


def select_nvme_device(devices: list) -> str:
    """
    Prompts user to select from the list of NVMe devices.
    Returns the selected PCI address (str), or None.
    """
    if not devices:
        print("No SPDK-compatible NVMe devices found.")
        return None

    print("Available NVMe Devices:\n")
    for idx, (pci, driver) in enumerate(devices):
        print(f"  [{idx}] {pci}  ({driver})")

    while True:
        try:
            choice = int(input("\nSelect device index: "))
            if 0 <= choice < len(devices):
                return devices[choice][0]  # Return only PCI address
        except ValueError:
            pass
        print("Invalid input. Please enter a valid index.")


# CLI usage
if __name__ == "__main__":
    from config import SPDK_DIR

    devices = list_spdk_nvme_devices(SPDK_DIR)
    selected = select_nvme_device(devices)

    if selected:
        print(f"\nSelected device: {selected}")
