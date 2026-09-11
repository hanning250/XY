# -*- coding: utf-8 -*-
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime


PPE_EVENT_TYPES = {
    "reflectivevestdetection",
    "safetyhelmetdetection",
    "safetyvestdetection",
    "workwear detection",
    "ppe detection",
    "未穿反光衣",
    "未穿安全帽",
    "未穿防护服",
    "behavioranalysis",
    "aievent",
    "fielddetection",
}

PPE_FIELD_HINTS = (
    "reflectivevest",
    "safetyhelmet",
    "safetyvest",
    "workclothes",
    "protectiveclothing",
    "ppe",
    "反光衣",
    "安全帽",
    "防护服",
    "工服",
)


def _strip_ns(tag):
    return tag.split("}")[-1] if "}" in tag else tag


def _find_text_by_keys(node, keys):
    for elem in node.iter():
        tag = _strip_ns(elem.tag)
        if tag in keys and elem.text and elem.text.strip():
            return elem.text.strip()
    return None


def parse_isapi_payload(raw_bytes):
    text = raw_bytes.decode("utf-8", errors="ignore").strip()
    if not text:
        return _empty_result()

    if text.startswith("{") or text.startswith("["):
        return _parse_json_payload(text)

    if text.startswith("<"):
        return _parse_xml_payload(text)

    return {
        "event_type": "unknown",
        "event_description": None,
        "rule_name": None,
        "channel_no": None,
        "event_time": None,
        "fields": {"raw_text": text[:2000]},
        "raw_text": text,
    }


def _empty_result():
    return {
        "event_type": "unknown",
        "event_description": None,
        "rule_name": None,
        "channel_no": None,
        "event_time": None,
        "fields": {},
        "raw_text": "",
    }


def _parse_json_payload(text):
    data = json.loads(text)
    fields = _flatten_json(data)
    event_type = _pick_event_type(fields, data)
    event_description = (
        fields.get("eventDescription")
        or fields.get("description")
        or fields.get("alarmDescription")
    )
    rule_name = (
        fields.get("ruleName")
        or fields.get("rule_name")
        or fields.get("AIOPData.ruleName")
    )
    channel_no = _to_int(
        fields.get("channelID")
        or fields.get("channelNo")
        or fields.get("channel")
        or fields.get("dynChannelID")
        or fields.get("srcInputPort")
    )
    event_time = (
        fields.get("dateTime")
        or fields.get("eventTime")
        or fields.get("time")
        or fields.get("activePost.time")
    )
    return {
        "event_type": str(event_type),
        "event_description": event_description,
        "rule_name": rule_name,
        "channel_no": channel_no,
        "event_time": event_time,
        "fields": fields,
        "raw_text": text,
    }


def _parse_xml_payload(text):
    root = ET.fromstring(text)
    fields = {}
    for elem in root.iter():
        tag = _strip_ns(elem.tag)
        if elem.text and elem.text.strip():
            fields[tag] = elem.text.strip()

    event_type = (
        _find_text_by_keys(root, {"eventType", "eventDescription", "subEventType", "type"})
        or "unknown"
    )
    return {
        "event_type": event_type,
        "event_description": fields.get("eventDescription"),
        "rule_name": fields.get("ruleName"),
        "channel_no": _to_int(
            fields.get("channelID") or fields.get("channelNo") or fields.get("channel")
        ),
        "event_time": fields.get("dateTime") or fields.get("eventTime") or fields.get("time"),
        "fields": fields,
        "raw_text": text,
    }


def _pick_event_type(fields, data):
    candidates = [
        fields.get("eventType"),
        fields.get("eventDescription"),
        fields.get("subEventType"),
        fields.get("type"),
    ]
    if isinstance(data, dict):
        alert = data.get("EventNotificationAlert")
        if isinstance(alert, dict):
            candidates.extend(
                [
                    alert.get("eventType"),
                    alert.get("eventDescription"),
                    alert.get("subEventType"),
                ]
            )
    for value in candidates:
        if value:
            return value
    return "unknown"


def _flatten_json(data, prefix=""):
    result = {}
    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, (dict, list)):
                result.update(_flatten_json(value, new_key))
            else:
                result[new_key] = value
    elif isinstance(data, list):
        for index, value in enumerate(data):
            new_key = f"{prefix}[{index}]"
            if isinstance(value, (dict, list)):
                result.update(_flatten_json(value, new_key))
            else:
                result[new_key] = value
    return result


def _to_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        match = re.search(r"\d+", str(value))
        return int(match.group()) if match else None


def is_ppe_related(event_type, raw_text, keywords, parsed=None):
    haystack = f"{event_type} {raw_text}".lower()
    if parsed:
        haystack += " " + " ".join(
            str(v)
            for k, v in parsed.get("fields", {}).items()
            if k in ("eventDescription", "ruleName", "description", "targetType")
            or "rule" in k.lower()
            or "alarm" in k.lower()
        ).lower()
        if parsed.get("event_description"):
            haystack += " " + str(parsed["event_description"]).lower()
        if parsed.get("rule_name"):
            haystack += " " + str(parsed["rule_name"]).lower()

    event_key = str(event_type).lower().replace(" ", "")
    if event_key in PPE_EVENT_TYPES:
        return True

    for hint in PPE_FIELD_HINTS:
        if hint.lower() in haystack:
            return True

    for keyword in keywords:
        if keyword.lower() in haystack:
            return True
    return False


def make_picture_name(prefix, index=None):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    if index is None:
        return f"{prefix}_{stamp}.jpg"
    return f"{prefix}_{index}_{stamp}.jpg"
