# -*- coding: utf-8 -*-
"""告警记录序列化：把数据库行整理成对外的结构。

放在 common 而不是 web，是为了避免 core → web 的反向依赖：
core/alarm_service.py 落库后要推送 WebSocket，需要这里的 serialize_alarm。
"""

import json
import os


def _loads(value, default=None):
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _picture_urls(paths):
    urls = []
    for path in paths:
        name = os.path.basename(path)
        if name.endswith(".json"):
            urls.append(f"/api/aiop-json/{name}")
        else:
            urls.append(f"/api/pictures/{name}")
    return urls


def serialize_alarm(alarm: dict) -> dict:
    item = dict(alarm)
    paths = _loads(item.get("picture_paths"), []) or []
    item["picture_paths"] = paths
    item["picture_urls"] = _picture_urls(paths)

    analysis = _loads(item.get("analysis"), None)
    item["analysis"] = analysis
    detail = _loads(item.get("event_detail"), None)
    item["event_detail"] = detail

    # 把常用字段提到顶层，甲方 IT 侧取结果时不用再解嵌套
    item["confidence"] = (analysis or {}).get("confidence")
    item["target_count"] = (analysis or {}).get("target_count")
    item["duration_ms"] = (detail or {}).get("duration_ms")

    if not item.get("event_time"):
        item["event_time"] = (detail or {}).get("event_time") or item.get("created_at")

    item["is_ppe_related"] = bool(item.get("is_ppe_related"))
    return item


def notify_alarm(notifier, storage, alarm_id):
    """落库后推给 WebSocket 订阅者。notifier 为 None 时静默跳过。"""
    if notifier is None or not alarm_id:
        return
    alarm = storage.get_alarm(alarm_id)
    if alarm:
        notifier.publish_sync(serialize_alarm(alarm))
