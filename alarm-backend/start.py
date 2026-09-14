# -*- coding: utf-8 -*-
"""一键启动：检查环境 → 补依赖 → 拷运行库 → 起服务。

用法（在 alarm-backend 目录下）：
    python start.py                  # 正常运行（开 ISUP 监听）
    python start.py --api-only       # 只起接口，不连设备
    python start.py --check          # 只做环境检查，不启动
    python start.py --install        # 缺依赖时自动尝试安装

推荐用 uv 跑（环境由 uv 管，不用手动激活 venv）：
    uv run python start.py
    uv run python main.py

也能用传统方式：
    .venv\\Scripts\\python.exe start.py

直接双击 start.bat 也可以。
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
LIB_ISUP = os.path.join(BASE, "lib_isup")

# 运行时必须有的库
CRITICAL_LIBS = ["HCISUPCMS.dll", "HCISUPAlarm.dll", "libeay32.dll", "ssleay32.dll"]
# Python 依赖
REQUIRED_MODULES = [("fastapi", "fastapi"), ("pydantic", "pydantic")]
# uvicorn 只有真正启动服务时才需要
SERVER_MODULES = [("uvicorn", "uvicorn[standard]")]

OK = "  [OK]  "
BAD = "  [!!]  "
INFO = "  --    "


def title(text):
    print()
    print("=" * 66)
    print(f"  {text}")
    print("=" * 66)


def find_uv():
    """找 uv。uv 常装在 %APPDATA%\\Python\\Scripts 但不在 PATH 上。"""
    found = shutil.which("uv")
    if found:
        return found
    candidates = [
        os.path.join(os.environ.get("APPDATA", ""), "Python", "Scripts", "uv.exe"),
        os.path.join(os.environ.get("USERPROFILE", ""), ".local", "bin", "uv.exe"),
        os.path.join(os.environ.get("USERPROFILE", ""), ".cargo", "bin", "uv.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "uv", "uv.exe"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def check_python():
    title("1/5  Python 环境")
    version = sys.version.split()[0]
    bits = platform.architecture()[0]
    print(f"{INFO}解释器 : {sys.executable}")
    print(f"{INFO}版本   : {version}  ({bits})")

    uv = find_uv()
    if uv:
        print(f"{INFO}uv     : {uv}")
    else:
        print(f"{INFO}uv     : 未找到（可选，用 venv 也能跑）")

    if "64" not in bits:
        print(f"{BAD}ISUP SDK 只有 Win64 库，必须用 64 位 Python")
        return False

    if platform.system().lower() != "windows":
        print(f"{BAD}当前项目只支持 Windows（SDK 是 Win64 库）")
        return False

    print(f"{OK}64 位 Windows，符合要求")
    return True


def check_libs(auto_install):
    title("2/5  ISUP SDK 运行库")
    missing = [n for n in CRITICAL_LIBS if not os.path.isfile(os.path.join(LIB_ISUP, n))]

    if not missing:
        count = len(os.listdir(LIB_ISUP)) if os.path.isdir(LIB_ISUP) else 0
        print(f"{OK}lib_isup 齐全（{count} 项）")
        return True

    print(f"{BAD}lib_isup 缺少: {', '.join(missing)}")
    print(f"{INFO}正在从 new_sdk 拷贝...")
    result = subprocess.run(
        [sys.executable, os.path.join(BASE, "setup_libs.py")],
        cwd=BASE,
    )
    if result.returncode != 0:
        print(f"{BAD}拷贝失败。请确认 new_sdk 目录存在，或手动指定：")
        print(f'{INFO}python setup_libs.py --sdk-root "<HCISUPSDK..._Win64_ZH 的路径>"')
        return False

    still = [n for n in CRITICAL_LIBS if not os.path.isfile(os.path.join(LIB_ISUP, n))]
    if still:
        print(f"{BAD}拷贝后仍缺少: {', '.join(still)}")
        return False
    print(f"{OK}运行库已就绪")
    return True


def _has_module(name):
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def check_deps(auto_install, need_server):
    title("3/5  Python 依赖")
    needed = list(REQUIRED_MODULES) + (SERVER_MODULES if need_server else [])

    missing = [(mod, pkg) for mod, pkg in needed if not _has_module(mod)]
    for mod, _pkg in needed:
        mark = OK if _has_module(mod) else BAD
        print(f"{mark}{mod}")

    if not missing:
        # 已经是 uv 项目的话，提醒一下 lock 是否同步
        if find_uv() and os.path.isfile(os.path.join(BASE, "pyproject.toml")):
            print(f"{INFO}本项目是 uv 项目，加依赖用: uv add <包名>")
        return True

    packages = [pkg for _mod, pkg in missing]
    print()
    print(f"{INFO}缺少: {', '.join(packages)}")

    project_has_pyproject = os.path.isfile(os.path.join(BASE, "pyproject.toml"))
    uv = find_uv()

    if not auto_install:
        print(f"{INFO}加上 --install 参数可自动安装，或手动执行：")
        if uv and project_has_pyproject:
            print(f"{INFO}{uv} add {' '.join(packages)}")
        else:
            print(f"{INFO}{sys.executable} -m pip install {' '.join(packages)}")
        return False

    # 优先用 uv（会把依赖写进 pyproject.toml 并更新 uv.lock）
    if uv and project_has_pyproject:
        print(f"{INFO}用 uv 安装...")
        result = subprocess.run([uv, "add", *packages], cwd=BASE)
        if result.returncode != 0:
            print(f"{BAD}uv add 失败，请手动执行: uv add {' '.join(packages)}")
            return False
    else:
        if not _has_module("pip"):
            print(f"{BAD}这个 Python 连 pip 都没有。有两条路：")
            print(f"{INFO}1) 装 uv 后用 uv 管环境（推荐）: uv sync")
            print(f"{INFO}2) 补 pip: {sys.executable} -m ensurepip --upgrade")
            return False
        print(f"{INFO}用 pip 安装...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", *packages], cwd=BASE
        )
        if result.returncode != 0:
            print(f"{BAD}安装失败，请手动执行上面那条命令看具体报错")
            return False

    still = [(mod, pkg) for mod, pkg in missing if not _has_module(mod)]
    if still:
        print(f"{BAD}安装后仍缺少: {', '.join(m for m, _ in still)}")
        return False
    print(f"{OK}依赖已就绪")
    return True


def check_config():
    title("4/5  配置检查")
    path = os.path.join(BASE, "config.json")
    if not os.path.isfile(path):
        print(f"{BAD}找不到 config.json")
        return None, False

    try:
        with open(path, "r", encoding="utf-8") as fp:
            config = json.load(fp)
    except ValueError as exc:
        print(f"{BAD}config.json 不是合法 JSON: {exc}")
        return None, False

    isup = config.get("isup", {})
    reg = isup.get("register_port")
    alm = isup.get("alarm_port")

    if reg is None or alm is None:
        print(f"{BAD}config.json 缺少 isup.register_port / isup.alarm_port")
        return config, False
    if reg == alm and not isup.get("reuse_cms_port", False):
        print(f"{BAD}注册端口和报警端口不能相同（都是 {reg}）")
        return config, False

    print(f"{OK}监听地址   : {isup.get('listen_ip', '0.0.0.0')}")
    print(f"{OK}设备注册端口: {reg}")
    print(f"{OK}报警接收端口: {alm}")
    print(f"{OK}协议       : {str(isup.get('protocol', 'tcp')).upper()}")
    print(f"{OK}接入安全模式: {isup.get('access_security', 0)}")
    return config, True


def show_device_hint(config):
    import socket

    isup = config.get("isup", {})
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
    except Exception:
        ip = "本机IP"

    print()
    print("  " + "-" * 62)
    print("  设备侧（盒子 Web 的 ISUP / EHome / 平台接入）需要填：")
    print(f"      平台地址 : {ip}")
    print(f"      端口     : {isup.get('register_port')}")
    print(f"      协议     : {str(isup.get('protocol', 'tcp')).upper()}")
    print("      设备ID   : 自定义，两端一致")
    print("      密钥     : 自定义，两端一致")
    print("  " + "-" * 62)


def main():
    parser = argparse.ArgumentParser(description="ISUP 告警后端一键启动")
    parser.add_argument("--api-only", action="store_true", help="只起接口，不开 ISUP 监听")
    parser.add_argument("--check", action="store_true", help="只做环境检查，不启动")
    parser.add_argument("--install", action="store_true", help="缺依赖时自动安装")
    args = parser.parse_args()

    print()
    print("  海康 ISUP 防护服告警后端 —— 启动检查")
    print(f"  项目目录: {BASE}")

    if not check_python():
        return 1
    if not check_libs(args.install):
        return 1
    if not check_deps(args.install, need_server=not args.check):
        print()
        print("  依赖没齐，先按上面提示补上。")
        return 1

    config, config_ok = check_config()
    if not config_ok:
        return 1

    if args.check:
        title("检查完成")
        print(f"{OK}环境没问题，可以启动：")
        if find_uv() and os.path.isfile(os.path.join(BASE, "pyproject.toml")):
            print(f"{INFO}uv run python start.py" + (" --api-only" if args.api_only else ""))
        print(f"{INFO}python start.py" + (" --api-only" if args.api_only else ""))
        return 0

    if not args.api_only:
        show_device_hint(config)
        print()
        print("  提示：设备还没连上时，/api/devices 会是空的，属正常。")
        print("        想先排查设备接入，另开一个窗口跑：python isup_doctor.py")

    title("5/5  启动服务")
    sys.path.insert(0, BASE)
    os.chdir(BASE)

    if args.api_only:
        sys.argv = [sys.argv[0], "--api-only"]
    else:
        sys.argv = [sys.argv[0]]

    import main as app_main

    app_main.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
