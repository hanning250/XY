# -*- coding: utf-8 -*-
"""向本地数据库注入一条带测试图片的告警，用于验证 API / SSE / 前端链路。"""
import base64
import json
import os
import sys
import urllib.request

from event_parser import make_picture_name
from storage import AlarmStorage

# 1x1 像素 JPEG
TINY_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxAQEBAQEBAVFhUVFxUYFxYYGBcYFxgX"
    "FxgXGBgVFRgXHSggGBolGxUVITEhJSkrLi4uFx8zODMsNygtLisBCgoKDg0OGxAQGy0l"
    "ICUtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLf/AABEI"
    "AAEAAQMBIgACEQEDEQH/xAAbAAACAwEBAQAAAAAAAAAAAAADBAECBQYAB//EADoQAAIB"
    "AgQDBQUGBQUAAAECAwQRAAUSITFBEyJRYQYUcYGRobEyQsHR8BVS4fEjJGLCBzNDU7L/"
    "xAAZAQADAQEBAAAAAAAAAAAAAAABAgMABAX/xAAjEQACAgMBBwUBAAAAAAAAAAABAgMR"
    "AAQhEjFBUWFxgaH/2gAMAwEAAhEDEQA/AJ7Z3pSlKUpSlKUpSlP6UpSlKUpSlKf0pSl"
    "KUpSlKUpT+lKUpSlKUpSlKf0pSlKUpSlKUpT+lKUpSlKUpSlKf0pSlKUpSlKUpT+lKUp"
    "SlKUpSlKf0pSlKUpSlKUpT+lKUpSlKUpSlKf0pSlKUpSlKUpT+lKUpSlKUpSlKf0pSl"
    "KUpSlKUpT+lKUpSlKUpSlKf0pSlKUpSlKUpT+lKUpSlKUpSlKf0pSlKUpSlKUpT+lKUp"
    "SlKUpSlKf/Z"
)


def main():
    base = os.path.dirname(__file__)
    with open(os.path.join(base, "config.json"), "r", encoding="utf-8") as fp:
        config = json.load(fp)

    storage_cfg = config.get("storage", {})
    picture_dir = os.path.join(base, storage_cfg.get("picture_dir", "data/pictures"))
    os.makedirs(picture_dir, exist_ok=True)
    storage = AlarmStorage(
        db_path=os.path.join(base, storage_cfg.get("db_path", "data/alarms.db")),
        picture_dir=picture_dir,
    )

    pic_name = make_picture_name("test", 0)
    pic_path = os.path.join(picture_dir, pic_name)
    with open(pic_path, "wb") as fp:
        fp.write(TINY_JPEG)

    raw_payload = """<?xml version="1.0" encoding="UTF-8"?>
<EventNotificationAlert version="2.0">
<eventType>AIOP_Polling_Snap</eventType>
<channelID>1</channelID>
<dateTime>2026-09-14T15:30:00+08:00</dateTime>
<eventDescription>测试告警-未穿防护服</eventDescription>
</EventNotificationAlert>"""

    alarm_id = storage.save_alarm(
        device_ip="192.168.1.64",
        device_serial="GU0986479",
        command_type="TEST_INJECT",
        event_type="AIOP_Polling_Snap",
        channel_no=1,
        event_time="2026-09-14T15:30:00",
        raw_payload=raw_payload,
        picture_paths=[pic_path],
        is_ppe_related=1,
    )
    print(f"已注入测试告警 id={alarm_id}，图片={pic_name}")

    api_port = config.get("api", {}).get("port", 8080)
    url = f"http://127.0.0.1:{api_port}/api/alarms?limit=1"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
        print(f"API 最新告警: {body[:400]}")
    except Exception as exc:
        print(f"API 查询失败（服务可能未启动）: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
