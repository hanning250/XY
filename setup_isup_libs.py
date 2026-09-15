# -*- coding: utf-8 -*-
"""Copy HCISUP SDK runtime DLLs into alarm-backend/lib."""
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
SDK_LIB = os.path.abspath(os.path.join(ROOT, "..", "lib64"))
TARGET = os.path.join(ROOT, "lib")

COPY_FILES = [
    "HCISUPCMS.dll",
    "HCISUPAlarm.dll",
    "HCNetUtils.dll",
    "hpr.dll",
    "zlib1.dll",
    "libeay32.dll",
    "ssleay32.dll",
    "libcrypto-1_1-x64.dll",
    "libssl-1_1-x64.dll",
    "libcrypto-3-x64.dll",
    "libssl-3-x64.dll",
]


def main():
    if not os.path.isdir(SDK_LIB):
        raise SystemExit(f"SDK lib64 目录不存在: {SDK_LIB}")
    os.makedirs(TARGET, exist_ok=True)
    copied = 0
    for name in COPY_FILES:
        src = os.path.join(SDK_LIB, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(TARGET, name))
            print(f"copied {name}")
            copied += 1
    if copied == 0:
        raise SystemExit(f"未复制任何 DLL，请检查 {SDK_LIB}")
    print(f"完成，共复制 {copied} 个文件到 {TARGET}")


if __name__ == "__main__":
    main()
