# -*- coding: utf-8 -*-
import json
import re
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from xml.etree import ElementTree


def make_picture_name(prefix: str, index: int = 0) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    return f"{prefix}_{stamp}_{index}_{suffix}.jpg"


def _flatten_json(data: Any, prefix: str = "") -> Dict[str, str]:
    result: Dict[str, str] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, (dict, list)):
                result.update(_flatten_json(value, new_key))
            elif value is not None:
                result[new_key] = str(value)
    elif isinstance(data, list):
        for idx, value in enumerate(data):
            result.update(_flatten_json(value, f"{prefix}[{idx}]"))
    return result


def _first_value(fields: Dict[str, str], *keys: str) -> Optional[str]:
    for key in keys:
        if key in fields and fields[key].strip():
            return fields[key].strip()
    return None


def _parse_xml_payload(text: str) -> Dict[str, Any]:
    result = {
        "event_type": "unknown",
        "channel_no": None,
        "event_time": None,
        "raw_text": text,
    }
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return result

    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    result["event_type"] = tag or "unknown"

    for node in root.iter():
        local = node.tag.split("}")[-1] if "}" in node.tag else node.tag
        if local in ("channelID", "channelId", "dynChannelID") and node.text:
            try:
                result["channel_no"] = int(node.text)
            except ValueError:
                pass
        if local in ("dateTime", "eventTime", "time") and node.text:
            result["event_time"] = node.text.strip()
        if local in ("eventType", "subEventType") and node.text:
            result["event_type"] = node.text.strip()

    return result


def _parse_json_payload(text: str) -> Dict[str, Any]:
    result = {
        "event_type": "unknown",
        "channel_no": None,
        "event_time": None,
        "raw_text": text,
    }
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return result

    if not isinstance(data, dict):
        return result

    fields = _flatten_json(data)
    alert = data.get("EventNotificationAlert")
    if isinstance(alert, dict):
        fields.update(_flatten_json(alert, "EventNotificationAlert"))

    event_type = _first_value(
        fields,
        "eventType",
        "EventNotificationAlert.eventType",
        "subEventType",
        "EventNotificationAlert.subEventType",
        "AIOPData.eventType",
        "type",
    )
    if event_type:
        result["event_type"] = event_type

    channel = _first_value(
        fields,
        "channelID",
        "channelId",
        "dynChannelID",
        "EventNotificationAlert.channelID",
        "EventNotificationAlert.channelId",
    )
    if channel:
        try:
            result["channel_no"] = int(channel)
        except ValueError:
            pass

    event_time = _first_value(
        fields,
        "dateTime",
        "eventTime",
        "time",
        "EventNotificationAlert.dateTime",
        "EventNotificationAlert.eventTime",
    )
    if event_time:
        result["event_time"] = event_time

    return result


def parse_isapi_payload(raw_bytes: bytes) -> Dict[str, Any]:
    text = ""
    if raw_bytes:
        text = raw_bytes.decode("utf-8", errors="ignore").strip()

    if not text:
        return {
            "event_type": "unknown",
            "channel_no": None,
            "event_time": None,
            "raw_text": "",
        }

    if text.startswith("{") or text.startswith("["):
        return _parse_json_payload(text)
    if text.startswith("<"):
        return _parse_xml_payload(text)

    return {
        "event_type": "unsupported_event",
        "channel_no": None,
        "event_time": None,
        "raw_text": text,
    }


def is_ppe_related(
    event_type: Optional[str],
    raw_text: str,
    keywords,
    parsed: Optional[Dict[str, Any]] = None,
) -> bool:
    haystack = " ".join(
        filter(
            None,
            [
                event_type or "",
                raw_text or "",
                (parsed or {}).get("raw_text") or "",
            ],
        )
    ).lower()

    normalized_type = (event_type or "").lower().replace(" ", "").replace("_", "")
    ppe_types = {
        "reflectivevestdetection",
        "safetyhelmetdetection",
        "safetyvestdetection",
        "workweardetection",
        "ppedetection",
        "behavioranalysis",
        "aievent",
        "aiop_video",
        "aiopvideo",
    }
    if normalized_type in ppe_types:
        return True

    for keyword in keywords or []:
        if keyword and keyword.lower() in haystack:
            return True

    if re.search(r"防护|反光衣|安全帽|工服|未穿|ppe", haystack, flags=re.IGNORECASE):
        return True

    return False
