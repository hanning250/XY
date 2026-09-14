# -*- coding: utf-8 -*-
"""把 ISUP SDK 的运行库（DLL）+ 证书拷进 alarm-backend/lib_isup。

ISUP SDK 目录（new_sdk）在工作区外面，不能直接引用，所以统一拷一份到项目里。

用法：
    python setup_libs.py
    python setup_libs.py --sdk-root "D:\\path\\to\\HCISUPSDKV..._Win64_ZH"
    python setup_libs.py --force      # 已存在也重拷
"""

import argparse
import os
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(BASE_DIR, "lib_isup")

# SDK 里 lib64 目录下这些文件是跑 ISUP 报警接收必须的
REQUIRED_DLLS = [
    "HCISUPCMS.dll",  # 设备注册监听（CMS）
    "HCISUPAlarm.dll",  # 报警监听 ← 收报警和图片靠它
    "HCISUPSS.dll",  # 存储服务（部分固件图片回传会用到）
    "HCISUPStream.dll",  # 取流（预留）
    "HCNetUtils.dll",
    "libeay32.dll",  # OpenSSL 1.0.x，ISUP 强依赖
    "ssleay32.dll",
    "zlib1.dll",
    "hpr.dll",
    "NPQos.dll",
    "AudioRender.dll",
]

# 这两个在 lib64/HCAapSDKCom/ 下，由 SUBDIRS 整体拷贝，不在这里单独列
NESTED_DLLS = ["SystemTransform.dll", "libiconv2.dll"]

# 可选：预览/回放/对讲才用到，收报警用不到，缺了不算错
OPTIONAL_DLLS = [
    "sqlite3.dll",
    "AudioIntercom.dll",
    "OpenAL32.dll",
    "SuperRender.dll",
    "PlayCtrl.dll",
    "d3dx9_43.dll",
    "msvcr90.dll",
]

# SDK 里 lib64 下的子目录，整体拷贝
SUBDIRS = ["Cert", "HCAapSDKCom"]


def find_sdk_root(explicit=None):
    """定位 HCISUPSDKV*_Win64_ZH 目录。"""
    if explicit:
        if not os.path.isdir(explicit):
            raise FileNotFoundError(f"指定的 SDK 目录不存在: {explicit}")
        # 允许直接指到 lib64
        parent = os.path.dirname(os.path.abspath(explicit.rstrip("\\/")))
        if os.path.basename(os.path.abspath(explicit)).lower().startswith("lib"):
            return parent
        return os.path.abspath(explicit)

    candidates = [
        r"D:\work\xinyiwork\new_sdk",
        os.path.abspath(os.path.join(BASE_DIR, "..", "..", "new_sdk")),
        os.path.abspath(os.path.join(BASE_DIR, "..", "new_sdk")),
    ]

    for candidate in candidates:
        if not os.path.isdir(candidate):
            continue
        for name in sorted(os.listdir(candidate)):
            full = os.path.join(candidate, name)
            if os.path.isdir(full) and name.upper().startswith("HCISUPSDK"):
                return full

    raise FileNotFoundError(
        "没找到 ISUP SDK 目录。请用 --sdk-root 指定，例如：\n"
        r'  python setup_libs.py --sdk-root "D:\work\xinyiwork\new_sdk\HCISUPSDKV2.5.1.35_build20241101_Win64_ZH"'
    )


def find_lib_source(sdk_root):
    """SDK 里的运行库目录一般是 lib64。"""
    for name in ("lib64", "lib", "lib32"):
        full = os.path.join(sdk_root, name)
        if os.path.isdir(full):
            return full
    raise FileNotFoundError(f"{sdk_root} 下找不到 lib64/lib 目录")


def copy_tree_if_missing(src, dst, force):
    if not os.path.isdir(src):
        return 0
    count = 0
    for root, _dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target_dir = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(target_dir, exist_ok=True)
        for name in files:
            target = os.path.join(target_dir, name)
            if os.path.isfile(target) and not force:
                continue
            shutil.copy2(os.path.join(root, name), target)
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description="拷贝 ISUP SDK 运行库到 lib_isup")
    parser.add_argument("--sdk-root", help="HCISUPSDKV*_Win64_ZH 目录")
    parser.add_argument("--force", action="store_true", help="已存在也重新拷贝")
    args = parser.parse_args()

    sdk_root = find_sdk_root(args.sdk_root)
    lib_src = find_lib_source(sdk_root)
    print(f"[setup] SDK 根目录 : {sdk_root}")
    print(f"[setup] 运行库目录 : {lib_src}")
    print(f"[setup] 目标目录   : {LIB_DIR}")

    os.makedirs(LIB_DIR, exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "data", "pictures"), exist_ok=True)

    copied, skipped, missing = 0, 0, []
    for name in REQUIRED_DLLS + OPTIONAL_DLLS:
        src = os.path.join(lib_src, name)
        dst = os.path.join(LIB_DIR, name)
        if not os.path.isfile(src):
            if name in REQUIRED_DLLS:
                missing.append(name)
            continue
        if os.path.isfile(dst) and not args.force:
            skipped += 1
            continue
        shutil.copy2(src, dst)
        copied += 1
        print(f"  + {name}")

    for sub in SUBDIRS:
        n = copy_tree_if_missing(
            os.path.join(lib_src, sub), os.path.join(LIB_DIR, sub), args.force
        )
        if n:
            print(f"  + {sub}/ ({n} 个文件)")
            copied += n

    print()
    print(f"[setup] 新拷贝 {copied} 个，已存在跳过 {skipped} 个")
    if missing:
        print(f"[setup] ⚠ 以下文件 SDK 里没找到（个别版本没有，一般可忽略）: {', '.join(missing)}")

    critical = ["HCISUPCMS.dll", "HCISUPAlarm.dll", "libeay32.dll", "ssleay32.dll"]
    lack = [n for n in critical if not os.path.isfile(os.path.join(LIB_DIR, n))]
    if lack:
        print(f"[setup] ✗ 关键库缺失: {', '.join(lack)}")
        return 1

    print("[setup] ✓ 关键库齐了，可以启动: python main.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
