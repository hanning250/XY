# -*- coding: utf-8 -*-
"""设备 ISAPI 诊断：事件上传、NVR 事件、摄像头 AI、触发器搜索。"""
import argparse
import re

from isapi_client import request

UPLOAD_PATHS = [
    "/ISAPI/Event/notification/httpHosts",
    "/ISAPI/Event/notification/httpHosts/capabilities",
    "/ISAPI/System/Network/Ehome",
    "/ISAPI/ContentMgmt/InputProxy/channels",
]

NVR_PATHS = [
    "/ISAPI/Event/triggers",
    "/ISAPI/Event/triggersCap",
    "/ISAPI/Event/notification/httpHosts/1",
    "/ISAPI/Event/notification/httpHosts/1/test",
    "/ISAPI/Intelligent/channels/1/capabilities",
]

CAMERA_PATHS = [
    "/ISAPI/Event/triggers",
    "/ISAPI/Intelligent/channels/1/capabilities",
    "/ISAPI/System/Network/Ehome",
    "/ISAPI/Event/notification/httpHosts",
]

TRIGGER_KEYWORDS = (
    "AI", "capture", "polling", "snap", "VMD", "behavior",
    "rule", "helmet", "vest", "IO", "center", "face",
)

MODES = {
    "upload": UPLOAD_PATHS,
    "nvr": NVR_PATHS,
    "camera": CAMERA_PATHS,
}


def default_targets(mode: str) -> list[str]:
    if mode == "camera":
        return ["192.168.1.10"]
    return ["192.168.1.64"]


def probe(ip: str, paths: list[str], preview: int = 1200):
    print(f"\n========== {ip} ==========")
    for path in paths:
        try:
            code, body = request(ip, path, timeout=10)
            print(f"\n[{code}] {path}")
            if body.strip():
                print(body[:preview])
        except Exception as exc:
            print(f"\n[ERR] {path}: {exc}")


def search_triggers(ip: str, keywords=TRIGGER_KEYWORDS):
    print(f"\n========== {ip} 触发器搜索 ==========")
    _, body = request(ip, "/ISAPI/Event/triggers", timeout=15)
    blocks = re.findall(r"<EventTrigger>.*?</EventTrigger>", body, flags=re.S)
    print(f"total triggers: {len(blocks)}")
    for block in blocks:
        if any(k.lower() in block.lower() for k in keywords):
            et = re.search(r"<eventType>([^<]+)</eventType>", block)
            print(f"\n--- {et.group(1) if et else '?'} ---")
            print(block[:1500])


def main():
    parser = argparse.ArgumentParser(description="海康设备 ISAPI 诊断")
    parser.add_argument(
        "--mode",
        choices=["upload", "nvr", "camera", "triggers", "all"],
        default="all",
        help="upload=上传中心, nvr=NVR, camera=摄像头, triggers=触发器搜索, all=全部",
    )
    parser.add_argument("--ip", action="append", help="指定设备 IP，可重复")
    args = parser.parse_args()

    if args.mode == "triggers":
        for ip in args.ip or ["192.168.1.64"]:
            search_triggers(ip)
        return

    if args.mode == "all":
        probe("192.168.1.64", UPLOAD_PATHS + NVR_PATHS, preview=1200)
        probe("192.168.1.10", UPLOAD_PATHS + CAMERA_PATHS, preview=1200)
        search_triggers("192.168.1.64")
        return

    paths = MODES[args.mode]
    for ip in args.ip or default_targets(args.mode):
        probe(ip, paths, preview=2000 if args.mode != "upload" else 1200)


if __name__ == "__main__":
    main()
