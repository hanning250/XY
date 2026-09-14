# -*- coding: utf-8 -*-
"""现场自检：确认设备能不能通过 ISUP 连上来、报警和图片能不能收到。

在**部署服务器的这台机器**上运行（要和设备网络互通）：

    python isup_doctor.py              # 环境自检 + 开启监听等设备上线（默认120秒）
    python isup_doctor.py --wait 300   # 多等一会儿
    python isup_doctor.py --check-only # 只做本地环境自检，不开端口

自检输出会逐项告诉你卡在哪一步：
    1. Python 位数 / 运行库是否齐全
    2. SDK 能否初始化
    3. 注册端口和报警端口能否绑定
    4. 设备有没有连上来（关键）
    5. 报警和图片有没有收到
"""

import argparse
import json
import os
import socket
import sys
import time
from datetime import datetime
from ctypes import POINTER, addressof, cast, c_void_p, sizeof

# 项目根目录（tools/ 的上一层）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

OUT_DIR = os.path.join(BASE_DIR, "isup_doctor_out")


def load_config():
    with open(
        os.path.join(BASE_DIR, "config.json"),
        "r",
        encoding="utf-8",
    ) as fp:
        return json.load(fp)


def local_ip():
    """取本机在局域网的 IP（用于告诉现场设备该填哪个地址）。"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "127.0.0.1"


def check_env(config):
    """第 1 步：环境与运行库。"""
    print("=" * 70)
    print("步骤 1/5  环境自检")
    print("=" * 70)
    ok = True

    import platform

    bits = platform.architecture()[0]
    print(f"  Python  : {sys.version.split()[0]}  ({bits})")
    if "64" not in bits:
        print("  ✗ ISUP SDK 只有 Win64 库，必须用 64 位 Python")
        ok = False
    else:
        print("  ✓ 64 位")

    lib_dir = os.path.join(BASE_DIR, "lib_isup")
    if not os.path.isdir(lib_dir):
        print(f"  ✗ 找不到 {lib_dir}，请先运行: python setup_libs.py")
        return False

    critical = ["HCISUPCMS.dll", "HCISUPAlarm.dll", "libeay32.dll", "ssleay32.dll"]
    missing = [n for n in critical if not os.path.isfile(os.path.join(lib_dir, n))]
    if missing:
        print(f"  ✗ lib_isup 缺少关键库: {', '.join(missing)}")
        print("    请运行: python setup_libs.py --force")
        ok = False
    else:
        print(f"  ✓ lib_isup 关键库齐全 ({len(os.listdir(lib_dir))} 项)")

    isup = config.get("isup", {})
    print(f"  监听地址: {isup.get('listen_ip', '0.0.0.0')}")
    print(f"  注册端口: {isup.get('register_port', 7660)}")
    print(f"  报警端口: {isup.get('alarm_port', 7661)}")
    print(f"  协议    : {str(isup.get('protocol', 'tcp')).upper()}")
    return ok


def check_sdk(config):
    """第 2 步：SDK 初始化。"""
    print()
    print("=" * 70)
    print("步骤 2/5  SDK 初始化")
    print("=" * 70)
    from core.hcisup import ISUPSDK, pick_ssl_dll_names

    lib_dir = os.path.join(BASE_DIR, "lib_isup")
    try:
        sdk = ISUPSDK()
        print("  ✓ DLL 加载成功")
    except Exception as exc:
        print(f"  ✗ DLL 加载失败: {exc}")
        return None

    try:
        libeay, ssleay = pick_ssl_dll_names(lib_dir)
        sdk.set_openssl_paths(libeay, ssleay)
        print(f"  ✓ OpenSSL 路径已设置 ({os.path.basename(libeay)})")
    except Exception as exc:
        print(f"  ✗ 设置 OpenSSL 路径失败: {exc}")
        return None

    try:
        sdk.init()
        print("  ✓ SDK 初始化成功")
    except Exception as exc:
        print(f"  ✗ SDK 初始化失败: {exc}")
        return None

    try:
        versions = sdk.get_versions()
        print(f"  SDK 版本: CMS={versions['cms']}  Alarm={versions['alarm']}")
    except Exception:
        pass
    return sdk


def check_ports(config):
    """第 3 步：端口能否绑定。"""
    print()
    print("=" * 70)
    print("步骤 3/5  端口绑定检查")
    print("=" * 70)
    isup = config.get("isup", {})
    listen_ip = isup.get("listen_ip", "0.0.0.0")
    register_port = int(isup.get("register_port", 7660))
    alarm_port = int(isup.get("alarm_port", 7661))

    if register_port == alarm_port:
        print(f"  ✗ 注册端口和报警端口不能相同 ({register_port})")
        return False

    ok = True
    for name, port in (("注册端口", register_port), ("报警端口", alarm_port)):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((listen_ip, port))
            print(f"  ✓ {name} {port} 可绑定")
        except OSError as exc:
            print(f"  ✗ {name} {port} 被占用或权限不足: {exc}")
            ok = False
        finally:
            sock.close()
    return ok


def run_listen(config, wait_seconds):
    """第 4/5 步：真正开监听，等设备上线并收报警。"""
    print()
    print("=" * 70)
    print("步骤 4/5  开启 ISUP 监听")
    print("=" * 70)

    from core.alarm_service import ISUPAlarmService
    from common.storage import AlarmStorage

    os.makedirs(OUT_DIR, exist_ok=True)
    storage = AlarmStorage(
        os.path.join(OUT_DIR, "doctor.db"), os.path.join(OUT_DIR, "pictures")
    )

    # 用薄包装，把回调事件打印出来，便于现场观察
    def on_register_log(login_id, data_type, p_out, out_len, p_in, in_len, user):
        stamp = datetime.now().strftime("%H:%M:%S")
        print(f"  [{stamp}] ← 设备注册事件 type={data_type} loginID={login_id}")
        return True

    service = ISUPAlarmService(
        config, storage, register_callback=on_register_log
    )

    import threading

    thread = threading.Thread(target=service.start, daemon=True)
    thread.start()

    if not service.wait_until_ready(timeout=30):
        print("  ✗ 30 秒内监听未就绪")
        service.stop()
        return service

    status = service.status
    print(
        f"  ✓ 监听已开启: {status.get('listen_ip')}:{status.get('register_port')} "
        f"(注册) / {status.get('alarm_port')} (报警)"
    )

    print()
    print("=" * 70)
    print("步骤 4/5  等待设备上线")
    print("=" * 70)
    ip = local_ip()
    isup = config.get("isup", {})
    print("  请确认设备侧的 ISUP / EHome 配置填的是：")
    print(f"      平台地址(服务器IP) : {ip}")
    print(f"      端口               : {isup.get('register_port', 7660)}")
    print(f"      协议               : {str(isup.get('protocol', 'tcp')).upper()}")
    print("      设备ID / 密钥       : 和设备侧保持一致")
    print()
    print(f"  最多等待 {wait_seconds} 秒...")

    deadline = time.time() + wait_seconds
    online_seen = False
    alarm_seen = False
    last_report = 0

    try:
        while time.time() < deadline:
            time.sleep(1)
            status = service.status
            if status.get("devices_online", 0) > 0 and not online_seen:
                online_seen = True
                device = status["devices"][0]
                print()
                print(f"  ✓✓ 设备已上线！")
                print(f"      设备ID   : {device.get('device_id')}")
                print(f"      序列号   : {device.get('serial')}")
                print(f"      设备IP   : {device.get('device_ip')}")
                print(f"      协议版本 : {device.get('protocol_version')}")
                print(f"      固件     : {device.get('firmware')}")
                print()
                print("  现在去触发一次告警（比如让人不穿反光衣走过画面）...")

            if status.get("received_alarms", 0) > 0 and not alarm_seen:
                alarm_seen = True
                print(f"  ✓✓ 已收到报警 {status['received_alarms']} 条！")

            # 每 20 秒报一次进度
            if time.time() - last_report >= 20:
                last_report = time.time()
                left = int(deadline - time.time())
                print(
                    f"  [{datetime.now().strftime('%H:%M:%S')}] 剩余 {left}s | "
                    f"在线设备 {status.get('devices_online', 0)} | "
                    f"已收报警 {status.get('received_alarms', 0)}"
                )
    except KeyboardInterrupt:
        print("\n  手动中断")

    # 第 5 步：结果
    print()
    print("=" * 70)
    print("步骤 5/5  结果")
    print("=" * 70)
    status = service.status
    print(f"  设备上线   : {'✓ 是' if online_seen else '✗ 否'}")
    print(f"  收到报警   : {'✓ 是' if alarm_seen else '✗ 否'}")
    print(f"  监听状态   : {status.get('state')}")
    if status.get("last_error"):
        print(f"  最后错误   : {status['last_error']}")

    rows = storage.list_alarms(limit=5)
    if rows:
        print(f"  已入库告警 : {len(rows)} 条（下面是最新一条）")
        row = rows[-1] if len(rows) > 1 else rows[0]
        paths = json.loads(row["picture_paths"])
        print(f"      event_type : {row['event_type']}")
        print(f"      channel    : {row['channel_no']}")
        print(f"      event_time : {row['event_time']}")
        print(f"      图片数量   : {len(paths)}")
        for path in paths:
            size = os.path.getsize(path) if os.path.isfile(path) else 0
            print(f"          {os.path.basename(path)}  {size} 字节")
        detail = json.loads(row["event_detail"] or "{}")
        if detail.get("picture_notes"):
            print(f"      图片提示   : {detail['picture_notes']}")
    else:
        print("  已入库告警 : 0 条")

    print()
    if not online_seen:
        print("  【设备没连上来，按顺序排查】")
        print(f"   1) 设备侧平台地址填的是不是本机 IP: {ip}（不是 127.0.0.1）")
        print(f"   2) 设备侧端口是不是 {isup.get('register_port', 7660)}")
        print("   3) 两边网络通不通：从设备 ping 服务器，或看服务器防火墙")
        print(f"      需要在防火墙放行 TCP {isup.get('register_port', 7660)} 和 "
              f"{isup.get('alarm_port', 7661)}")
        print("   4) 设备侧 ISUP 协议版本：4.0/5.0 时把 config.json 的")
        print("      isup.protocol 改成 mqtt，access_security 改成 2")
        print("   5) 设备密钥是否和平台侧约定的一致（日志会出现 EHOMEKEY 校验失败）")
    elif not alarm_seen:
        print("  【设备在线但没报警】")
        print("   1) 确认设备上 AI 规则已启用，且勾选了「上传中心/报警上传」")
        print("   2) 确认报警上报走的是 ISUP 通道而不是仅本地录像")
        print("   3) 触发一次明显的违规动作再等几秒")

    service.stop()
    print()
    print(f"  原始数据与图片在: {OUT_DIR}")
    print("  把 report 里的信息发我，可以继续定位。")

    with open(os.path.join(OUT_DIR, "doctor_report.json"), "w", encoding="utf-8") as fp:
        json.dump(
            {
                "time": datetime.now().isoformat(timespec="seconds"),
                "local_ip": ip,
                "online_seen": online_seen,
                "alarm_seen": alarm_seen,
                "status": service.status,
            },
            fp,
            ensure_ascii=False,
            indent=2,
        )
    return service


def main():
    parser = argparse.ArgumentParser(description="ISUP 现场自检")
    parser.add_argument("--wait", type=int, default=120, help="等设备上线的秒数")
    parser.add_argument("--check-only", action="store_true", help="只做环境自检，不开端口")
    args = parser.parse_args()

    config = load_config()
    print()
    print(f"ISUP 现场自检  {datetime.now().isoformat(timespec='seconds')}")
    print(f"本机局域网 IP: {local_ip()}")
    print()

    if not check_env(config):
        print("\n环境自检未通过，先解决上面标 ✗ 的问题。")
        return 1

    if args.check_only:
        print("\n(--check-only：跳过监听测试)")
        return 0

    if not check_ports(config):
        print("\n端口检查未通过，先释放端口或改 config.json。")
        return 1

    run_listen(config, args.wait)
    return 0


if __name__ == "__main__":
    sys.exit(main())
