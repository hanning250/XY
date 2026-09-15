# -*- coding: utf-8 -*-
import base64
import json
import os

from labels_zh import enrich_alarm
from schemas import AlarmRecord

# 测试注入用最小 JPEG（>128B，满足 picture_fetcher 保存阈值）
TEST_ALARM_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRof"
    "Hh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwh"
    "MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAAR"
    "CAAQABADASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAb/xAAUEAEAAAAAAAAAAAAAAAAA"
    "AAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMB"
    "AAIRAxEAPwCfAAH/2Q=="
)


def serialize_alarm(alarm: dict) -> dict:
    item = dict(alarm)
    paths = json.loads(item.get("picture_paths") or "[]")
    item["picture_paths"] = paths
    item["picture_urls"] = [f"/api/pictures/{os.path.basename(p)}" for p in paths]
    item["is_ppe_related"] = bool(item.get("is_ppe_related"))
    return enrich_alarm(item)


def to_alarm_record(alarm: dict) -> AlarmRecord:
    return AlarmRecord(**serialize_alarm(alarm))


def notify_alarm(notifier, storage, alarm_id):
    if notifier is None or not alarm_id:
        return
    alarm = storage.get_alarm(alarm_id)
    if alarm:
        notifier.publish_sync(serialize_alarm(alarm))
