# -*- coding: utf-8 -*-
"""告警入库、序列化与 SSE 推送。"""
import json
import os

from event_parser import is_ppe_related, parse_isapi_payload
from labels_zh import enrich_alarm
from picture_fetcher import fetch_alarm_pictures
from schemas import AlarmRecord


def serialize_alarm(alarm: dict) -> dict:
    item = dict(alarm)
    paths = json.loads(item.get("picture_paths") or "[]")
    item["picture_paths"] = paths
    item["picture_urls"] = [f"/api/pictures/{os.path.basename(p)}" for p in paths]
    item["is_ppe_related"] = bool(item.get("is_ppe_related"))
    return enrich_alarm(item)


def to_alarm_record(alarm: dict) -> AlarmRecord:
    return AlarmRecord(**serialize_alarm(alarm))


def _notify_alarm(notifier, storage, alarm_id):
    if notifier is None or not alarm_id:
        return
    alarm = storage.get_alarm(alarm_id)
    if alarm:
        notifier.publish_sync(serialize_alarm(alarm))


def persist_alarm(
    storage,
    notifier,
    config,
    raw_bytes: bytes,
    *,
    command_label: str = "HTTP_ISAPI",
    device_serial: str = "unknown",
    device_ip: str = "",
    embedded_pictures=None,
    remote_urls=None,
    device_auth=None,
):
    parsed = parse_isapi_payload(raw_bytes) if raw_bytes else parse_isapi_payload(b"")
    auth = device_auth or config.get("device_auth", {})
    raw_text = parsed.get("raw_text") or (raw_bytes.decode("utf-8", errors="ignore") if raw_bytes else "")

    picture_paths = fetch_alarm_pictures(
        picture_dir=storage.picture_dir,
        device_ip=device_ip or config.get("http_notify", {}).get("platform_ip", ""),
        embedded_pictures=embedded_pictures or [],
        raw_text=raw_text,
        remote_urls=remote_urls or [],
        auth=auth,
    )

    keywords = config.get("event_filter_keywords", [])
    ppe_flag = is_ppe_related(
        parsed["event_type"],
        raw_text,
        keywords,
        parsed=parsed,
    )

    alarm_id = storage.save_alarm(
        device_ip=device_ip or "unknown",
        device_serial=device_serial,
        command_type=command_label,
        event_type=parsed["event_type"],
        channel_no=parsed["channel_no"],
        event_time=parsed["event_time"],
        raw_payload=raw_text,
        picture_paths=picture_paths,
        is_ppe_related=ppe_flag,
    )
    _notify_alarm(notifier, storage, alarm_id)
    print(
        f"[alarm-ingest] 入库 id={alarm_id}, cmd={command_label}, "
        f"type={parsed['event_type']}, ppe={ppe_flag}, pics={len(picture_paths)}"
    )
    return alarm_id, parsed, picture_paths
