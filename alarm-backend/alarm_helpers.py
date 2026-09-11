# -*- coding: utf-8 -*-
import json
import os

from schemas import AlarmRecord


def serialize_alarm(alarm: dict) -> dict:
    item = dict(alarm)
    paths = json.loads(item.get("picture_paths") or "[]")
    item["picture_paths"] = paths
    item["picture_urls"] = [f"/api/pictures/{os.path.basename(p)}" for p in paths]
    item["is_ppe_related"] = bool(item.get("is_ppe_related"))
    return item


def to_alarm_record(alarm: dict) -> AlarmRecord:
    return AlarmRecord(**serialize_alarm(alarm))


def notify_alarm(notifier, storage, alarm_id):
    if notifier is None or not alarm_id:
        return
    alarm = storage.get_alarm(alarm_id)
    if alarm:
        notifier.publish_sync(serialize_alarm(alarm))
