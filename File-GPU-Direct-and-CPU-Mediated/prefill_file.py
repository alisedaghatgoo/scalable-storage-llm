#!/usr/bin/env python3
"""
prefill_file.py  --file /mnt/fio/nvme0n1_xfs/testfile.dat --bs 128k
"""
import argparse, subprocess, os, json, pathlib, sys

def shell(cmd): subprocess.run(cmd, check=True)

def parse():
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True, type=pathlib.Path)
    p.add_argument("--bs",   default="128k")
    return p.parse_args()

def main():
    A   = parse()
    cfg = ["fio", "--name=prefill",
           f"--filename={A.file}", "--rw=write", f"--bs={A.bs}",
           "--ioengine=libaio", "--iodepth=32", "--numjobs=4",
           "--direct=1", "--group_reporting"]
    print("[FIO]", " ".join(cfg))
    shell(cfg)

if __name__ == "__main__":
    main()
