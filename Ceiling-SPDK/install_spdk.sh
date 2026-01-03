#!/bin/bash
set -e

SPDK_DIR="$HOME/spdk"
NUM_HUGEPAGES=2048
HUGEPAGE_MOUNT="/mnt/huge"
VENV_PATH="$HOME/spdk-venv"

echo "[*] Step 1: Installing system dependencies..."
sudo apt update
sudo apt install -y \
  git gcc g++ make cmake libaio-dev libssl-dev \
  uuid-dev libnuma-dev python3-pip libjson-c-dev \
  libudev-dev libtool pkg-config python3-pyelftools \
  python3-dev libfuse3-dev meson ninja-build autoconf automake \
  libcunit1 libcunit1-dev libcunit1-doc libncurses-dev \
  python3-venv

echo "[*] Step 2: Cloning or updating SPDK..."
if [ ! -d "$SPDK_DIR" ]; then
  git clone https://github.com/spdk/spdk.git "$SPDK_DIR"
  cd "$SPDK_DIR"
  git submodule update --init --recursive
else
  echo "[✔] SPDK already exists at $SPDK_DIR"
  cd "$SPDK_DIR"
  git pull
  git submodule update --init --recursive
fi

echo "[*] Step 3: Configuring and building SPDK with unit tests..."
./configure --with-shared
make -j"$(nproc)"

echo "[*] Step 4: Setting up hugepages..."
echo $NUM_HUGEPAGES | sudo tee /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages > /dev/null

if ! mountpoint -q "$HUGEPAGE_MOUNT"; then
  sudo mkdir -p "$HUGEPAGE_MOUNT"
  sudo mount -t hugetlbfs nodev "$HUGEPAGE_MOUNT"
else
  echo "[✔] Hugepages already mounted at $HUGEPAGE_MOUNT"
fi
grep -i huge /proc/mounts

echo "[*] Step 5: Setting up Python virtual environment at $VENV_PATH..."
if [ ! -d "$VENV_PATH" ]; then
  python3 -m venv "$VENV_PATH"
  echo "[✔] Virtualenv created."
else
  echo "[✔] Virtualenv already exists. Reusing."
fi
source "$VENV_PATH/bin/activate"

echo "[*] Step 6: Installing Python packages..."
pip install --upgrade pip
pip install psutil

echo ""
echo "SPDK is fully installed with unit test support at: $SPDK_DIR"
echo "To activate your SPDK Python environment later, run: source $VENV_PATH/bin/activate"
