# -*- coding: utf-8 -*-
"""Platform launcher: ISUP SDK services + FastAPI alarm backend."""
import sys
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.Backend.alarm_bridge import register_sdk_handler, unregister_sdk_handler
from src.Backend.main import app, run_server
from src.Common import glo
from src.Common.ConfRead import getConfJson, loadJsonConfToGlobal
from src.Common.DemoRuntime import start_all_services, stop_all_services


def main():
    loadJsonConfToGlobal(getConfJson())
    ams, ss, cms, sms = start_all_services(run_cleanup=False)
    register_sdk_handler()

    server_thread = threading.Thread(
        target=run_server,
        kwargs={"app_instance": app},
        name="FastAPI-Server",
        daemon=True,
    )
    server_thread.start()
    print("告警平台已启动: http://127.0.0.1:8080")
    print("WebSocket: ws://127.0.0.1:8080/ws/alarms")

    glo.wait_for_device()

    try:
        while True:
            command = input("输入 yes 退出平台: ").strip().lower()
            if command == "yes":
                break
    except KeyboardInterrupt:
        pass
    finally:
        unregister_sdk_handler()
        stop_all_services(sms, cms, ams, ss)
        print("平台已停止")


if __name__ == "__main__":
    main()
