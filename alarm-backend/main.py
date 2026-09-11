# -*- coding: utf-8 -*-
import argparse
import json
import os
import signal
import sys
import threading

import uvicorn

from api import create_app
from alarm_service import HikAlarmService
from notifier import AlarmNotifier
from storage import AlarmStorage


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    example_path = os.path.join(os.path.dirname(__file__), "config.example.json")
    if not os.path.isfile(config_path):
        raise FileNotFoundError(
            f"未找到 config.json，请先复制 {example_path} 并修改 NVR 连接参数。"
        )
    with open(config_path, "r", encoding="utf-8") as fp:
        return json.load(fp)


def parse_args():
    parser = argparse.ArgumentParser(description="海康 NVR 防护服告警后端")
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="仅启动 REST API，不连接 NVR（用于联调 HTTP 推送）",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config()
    sdk_enabled = config.get("sdk", {}).get("enabled", True) and not args.api_only

    storage_cfg = config["storage"]
    storage = AlarmStorage(
        db_path=os.path.join(os.path.dirname(__file__), storage_cfg["db_path"]),
        picture_dir=os.path.join(os.path.dirname(__file__), storage_cfg["picture_dir"]),
    )
    notifier = AlarmNotifier()

    alarm_service = None
    if sdk_enabled:
        alarm_service = HikAlarmService(config, storage, notifier=notifier)
        alarm_thread = threading.Thread(target=alarm_service.start, daemon=True)
        alarm_thread.start()
        if not alarm_service.wait_until_ready(timeout=30):
            print("[main] SDK 尚未连上 NVR，API 仍会启动；后台会继续自动重连。")
    else:
        print("[main] 以 API-only 模式启动，不连接 NVR SDK。")

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

    print(f"[main] FastAPI: http://{host}:{port}")
    print(f"[main] 监控页面: http://{host}:{port}/")
    print(f"[main] Swagger 文档: http://{host}:{port}/docs")
    print(f"[main] WebSocket: ws://{host}:{port}/ws/alarms")
    print("[main] 状态接口: GET /api/status")
    print("[main] 告警列表: GET /api/alarms?ppe_only=true")
    print("[main] HTTP推送: POST /api/hikvision/event")

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
