# -*- coding: utf-8 -*-
import argparse
import json
import os
import signal
import sys
import threading

import uvicorn

from core.alarm_service import ISUPAlarmService
from common.storage import AlarmStorage
from web.api import create_app
from web.notifier import AlarmNotifier


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if not os.path.isfile(config_path):
        raise FileNotFoundError(
            f"未找到 config.json，请先按现场参数填写 ISUP 监听配置：{config_path}"
        )
    with open(config_path, "r", encoding="utf-8") as fp:
        return json.load(fp)


def parse_args():
    parser = argparse.ArgumentParser(description="海康 ISUP 防护服告警后端")
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="仅启动 REST API，不开启 ISUP 监听（用于联调前端/接口）",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config()
    isup_enabled = not args.api_only

    storage_cfg = config["storage"]
    storage = AlarmStorage(
        db_path=os.path.join(os.path.dirname(__file__), storage_cfg["db_path"]),
        picture_dir=os.path.join(os.path.dirname(__file__), storage_cfg["picture_dir"]),
    )
    notifier = AlarmNotifier()

    alarm_service = None
    if isup_enabled:
        alarm_service = ISUPAlarmService(config, storage, notifier=notifier)
        alarm_thread = threading.Thread(target=alarm_service.start, daemon=True)
        alarm_thread.start()
        if not alarm_service.wait_until_ready(timeout=30):
            print("[main] ISUP 监听尚未就绪，API 仍会启动；后台会继续重试。")
    else:
        print("[main] 以 API-only 模式启动，不开启 ISUP 监听。")

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

    isup_cfg = config.get("isup", {})
    print("=" * 68)
    print("[main] 海康 ISUP（EHome）防护服告警后端")
    if isup_enabled:
        print(
            f"[main] 设备注册监听 : {isup_cfg.get('listen_ip', '0.0.0.0')}:"
            f"{isup_cfg.get('register_port', 7660)}"
        )
        print(
            f"[main] 报警接收监听 : {isup_cfg.get('listen_ip', '0.0.0.0')}:"
            f"{isup_cfg.get('alarm_port', 7661)}  "
            f"({str(isup_cfg.get('protocol', 'tcp')).upper()})"
        )
        print(
            "[main] 设备侧要配   : 平台IP=本机IP, 注册端口="
            f"{isup_cfg.get('register_port', 7660)}, 设备ID+密钥按现场填写"
        )
    print(f"[main] FastAPI      : http://{host}:{port}")
    print(f"[main] 监控页面     : http://{host}:{port}/")
    print(f"[main] Swagger 文档 : http://{host}:{port}/docs")
    print(f"[main] WebSocket    : ws://{host}:{port}/ws/alarms")
    print(f"[main] 监听状态     : GET /api/status")
    print(f"[main] 设备列表     : GET /api/devices")
    print(f"[main] 告警列表     : GET /api/alarms?ppe_only=true")
    print("=" * 68)

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
