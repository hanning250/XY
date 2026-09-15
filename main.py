# -*- coding: utf-8 -*-
import argparse
import os
import signal
import sys

import uvicorn

from api import create_app
from isapi_client import load_config
from notifier import AlarmNotifier
from port_guard import ensure_ports_available
from storage import AlarmStorage


def parse_args():
    parser = argparse.ArgumentParser(description="海康 HTTP ISAPI 告警后端")
    parser.add_argument(
        "--force",
        action="store_true",
        help="端口被占用时自动结束旧进程后再启动（慎用）",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config(required=True)
    api_port = int(config.get("api", {}).get("port", 8080))

    if not ensure_ports_available([api_port], force=args.force):
        sys.exit(1)

    storage_cfg = config["storage"]
    storage = AlarmStorage(
        db_path=os.path.join(os.path.dirname(__file__), storage_cfg["db_path"]),
        picture_dir=os.path.join(os.path.dirname(__file__), storage_cfg["picture_dir"]),
    )
    notifier = AlarmNotifier()
    app = create_app(storage, config, notifier=notifier)

    api_cfg = config.get("api", {})
    host = api_cfg.get("host", "0.0.0.0")
    event_path = config.get("http_notify", {}).get("path", "/api/hikvision/event")

    def handle_exit(signum, frame):
        print("\n正在停止服务...")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_exit)

    print(f"[main] FastAPI: http://{host}:{api_port}")
    print(f"[main] 监控页面: http://{host}:{api_port}/")
    print(f"[main] HTTP 事件: POST {event_path}")
    print(f"[main] SSE 实时推送: http://{host}:{api_port}/api/alarms/stream")

    uvicorn.run(app, host=host, port=api_port, log_level="info")


if __name__ == "__main__":
    main()
