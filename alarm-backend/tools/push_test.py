# -*- coding: utf-8 -*-
"""模拟 NVR ISAPI HTTP 推送，用于无设备联调。"""
import argparse
import json
import urllib.request


SAMPLE = {
    "EventNotificationAlert": {
        "dateTime": "2026-09-11T14:00:00+08:00",
        "eventType": "AIOP_Video",
        "eventDescription": "未穿反光衣",
        "channelID": 3,
        "ruleName": "防护服检测规则1",
    }
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8080/api/hikvision/event")
    args = parser.parse_args()

    data = json.dumps(SAMPLE, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        args.url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        print(resp.read().decode("utf-8"))


if __name__ == "__main__":
    main()
