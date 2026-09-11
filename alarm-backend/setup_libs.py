# -*- coding: utf-8 -*-
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SDK_ROOT = ROOT.parent
SDK_LIB = SDK_ROOT / "库文件"
DEMO_DIR = SDK_ROOT / "Demo示例" / "5- Python开发示例" / "2-报警布防Demo"
LIB_DIR = ROOT / "lib"

WINDOWS_DLLS = [
    "HCNetSDK.dll",
    "HCCore.dll",
    "hlog.dll",
    "hpr.dll",
    "zlib1.dll",
    "libcrypto-1_1-x64.dll",
    "libssl-1_1-x64.dll",
    "libcrypto-3-x64.dll",
    "libssl-3-x64.dll",
]


def copy_if_exists(src_dir, filename, dst_dir):
    src = src_dir / filename
    if src.is_file():
        shutil.copy2(src, dst_dir / filename)
        return True
    return False


def main():
    LIB_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "pictures").mkdir(parents=True, exist_ok=True)

    demo_hcnetsdk = DEMO_DIR / "HCNetSDK.py"
    if demo_hcnetsdk.is_file():
        shutil.copy2(demo_hcnetsdk, ROOT / "HCNetSDK.py")
        print("copied HCNetSDK.py")

    copied = []
    demo_lib = DEMO_DIR / "lib"
    demo_has_sdk = (demo_lib / "HCNetSDK.dll").is_file() or (demo_lib / "win" / "HCNetSDK.dll").is_file()

    if demo_has_sdk:
        source = demo_lib / "win" if (demo_lib / "win" / "HCNetSDK.dll").is_file() else demo_lib
        for item in source.iterdir():
            if item.is_file():
                shutil.copy2(item, LIB_DIR / item.name)
                copied.append(item.name)
            elif item.is_dir():
                dst = LIB_DIR / item.name
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(item, dst)
                copied.append(item.name + "/")
    else:
        for filename in WINDOWS_DLLS:
            if copy_if_exists(SDK_LIB, filename, LIB_DIR):
                copied.append(filename)
        com_src = SDK_LIB / "HCNetSDKCom"
        if com_src.is_dir():
            dst = LIB_DIR / "HCNetSDKCom"
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(com_src, dst)
            copied.append("HCNetSDKCom/")

    config = ROOT / "config.json"
    example = ROOT / "config.example.json"
    if not config.exists() and example.exists():
        shutil.copy2(example, config)
        print("created config.json")

    if not copied:
        raise SystemExit("No SDK library files copied. Check SDK package paths.")

    print("copied:", ", ".join(copied))


if __name__ == "__main__":
    main()
