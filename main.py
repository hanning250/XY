# -*- coding: utf-8 -*-
import argparse
import json
import os
import signal
import sys
import threading

import uvicorn

from api import create_app
from isup_service import IsupAlarmService
from notifier import AlarmNotifier
from port_guard import collect_required_ports, ensure_ports_available
from storage import AlarmStorage


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    example_path = os.path.join(os.path.dirname(__file__), "config.example.json")
    if not os.path.isfile(config_path):
        raise FileNotFoundError(
            f"未找到 config.json，请先复制 {example_path} 并修改 ISUP 平台参数。"
        )
    with open(config_path, "r", encoding="utf-8") as fp:
        return json.load(fp)


def parse_args():
    parser = argparse.ArgumentParser(description="海康 ISUP 告警后端")
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="仅启动 REST API，不启动 ISUP CMS/AMS 监听",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="端口被占用时自动结束旧进程后再启动（慎用）",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config()
    isup_enabled = config.get("isup", {}).get("enabled", True) and not args.api_only

    required_ports = collect_required_ports(config, args.api_only)
    if not ensure_ports_available(required_ports, force=args.force):
        sys.exit(1)

    storage_cfg = config["storage"]
    storage = AlarmStorage(
        db_path=os.path.join(os.path.dirname(__file__), storage_cfg["db_path"]),
        picture_dir=os.path.join(os.path.dirname(__file__), storage_cfg["picture_dir"]),
    )
    notifier = AlarmNotifier()

    alarm_service = None
    if isup_enabled:
        alarm_service = IsupAlarmService(config, storage, notifier=notifier)
        alarm_thread = threading.Thread(target=alarm_service.start, daemon=True)
        alarm_thread.start()
        if not alarm_service.wait_until_ready(timeout=30):
            print("[main] ISUP 服务尚未就绪，API 仍会启动；请检查 lib DLL 与端口占用。")
    else:
        print("[main] 以 API-only 模式启动，不监听 ISUP 告警。")

    app = create_app(storage, config, alarm_service=alarm_service, notifier=notifier)
    api_cfg = config.get("api", {})
    host = api_cfg.get("host", "0.0.0.0")
    port = int(api_cfg.get("port", 8080))

    def handle_exit(signum, frame):
        print("\n正在停止服务...")
        if alarm_service is not None:
            alarm_service.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_exit)

    isup = config.get("isup", {})
    print(f"[main] FastAPI: http://{host}:{port}")
    print(f"[main] 监控页面: http://{host}:{port}/")
    print(f"[main] Swagger 文档: http://{host}:{port}/docs")
    print(f"[main] SSE 实时推送: http://{host}:{port}/api/alarms/stream")
    print("[main] 状态接口: GET /api/status")
    print("[main] 告警列表: GET /api/alarms?ppe_only=true")
    if isup_enabled:
        print(
            f"[main] ISUP CMS: {isup.get('platform_ip')}:{isup.get('cms', {}).get('port', 7660)}"
        )
        print(
            f"[main] ISUP AMS: {isup.get('platform_ip')}:{isup.get('ams', {}).get('port', 7200)}"
        )

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
