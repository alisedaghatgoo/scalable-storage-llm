#!/usr/bin/env python3
"""
prepare_fs.py  --device /dev/nvme0n1 --fs xfs \
               --mount /mnt/fio/nvme0n1_xfs \
               --file testfile.dat --size auto
"""
import argparse, subprocess, os, sys, shutil, json, pathlib
KB = 1024; MB = 1024*KB

def shell(cmd, **kw):
    print("[RUN]", *cmd); subprocess.run(cmd, check=True, **kw)

def parse():
    p = argparse.ArgumentParser()
    p.add_argument("--device", required=True)
    p.add_argument("--fs",     choices=["xfs", "ext4"], required=True)
    p.add_argument("--mount",  required=True, type=pathlib.Path)
    p.add_argument("--file",   required=True, type=str)
    p.add_argument("--size",   default="auto",
                   help='"auto", "50%%", or bytes')
    return p.parse_args()

def free_bytes(path):
    s = shutil.disk_usage(path)
    return s.free

def compute_size(size_arg, mountpoint):
    if size_arg == "auto":
        return free_bytes(mountpoint) - 4*MB
    if size_arg.endswith("%"):
        pct = float(size_arg.rstrip("%"))/100.0
        return int(free_bytes(mountpoint) * pct)
    return int(size_arg)

def main():
    A = parse()
    A.mount.mkdir(parents=True, exist_ok=True)

    # 1. mkfs  ---------------------------------------------------------------
    shell(["sudo", f"mkfs.{A.fs}", "-F", A.device])

    # 2. mount ---------------------------------------------------------------
    shell(["sudo", "umount", "-fl", A.device], check=False)
    shell(["sudo", "mount", "-o", "noatime", A.device, A.mount])

    # 3. create/resize test file --------------------------------------------
    tfile = A.mount / A.file
    size  = compute_size(A.size, A.mount)
    if not tfile.exists() or tfile.stat().st_size != size:
        shell(["sudo", "fallocate", "-l", str(size), tfile])

    # 4. print path as JSON for caller
    print(json.dumps({"testfile": str(tfile)}))

if __name__ == "__main__":
    main()
