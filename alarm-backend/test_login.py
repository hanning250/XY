# -*- coding: utf-8 -*-
"""快速测试 NVR SDK 登录。"""
import json
import os
import sys

from alarm_service import HikAlarmService
from storage import AlarmStorage


def main():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, "r", encoding="utf-8") as fp:
        config = json.load(fp)

    storage = AlarmStorage(
        db_path=os.path.join(os.path.dirname(__file__), "data", "alarms.db"),
        picture_dir=os.path.join(os.path.dirname(__file__), "data", "pictures"),
    )
    service = HikAlarmService(config, storage)
    nvr = config["nvr"]
    print(f"测试登录: {nvr['ip']}:{nvr.get('port', 8000)} user={nvr['username']}")

    try:
        service.hik_sdk = service._load_sdk()
        service._set_sdk_init_cfg()
        if not service.hik_sdk.NET_DVR_Init():
            print("NET_DVR_Init 失败")
            sys.exit(1)
        service._login(
            ip=nvr["ip"].encode("utf-8"),
            username=nvr["username"].encode("utf-8"),
            pwd=nvr["password"].encode("utf-8"),
            port=int(nvr.get("port", 8000)),
            login_mode=int(nvr.get("login_mode", 2)),
        )
        print("登录成功!")
    except Exception as exc:
        print(f"登录失败: {exc}")
        sys.exit(1)
    finally:
        service.stop()


if __name__ == "__main__":
    main()
