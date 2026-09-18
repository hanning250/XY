# -*- coding: utf-8 -*-
"""Extract customer-facing alarm fields from raw SDK payloads."""
import hashlib
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

from src.Backend.config import STORAGE_DIR
from src.Backend.image_registry import find_unclaimed_recent, mark_image_used, match_storage_by_url
from src.Backend.schemas import AlarmEventIn


def _tag(text: str, name: str) -> str:
    if not text:
        return ""
    match = re.search(rf"<{name}>([^<]*)</{name}>", text, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _to_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _derive_attr_label(rule_name: str, attr_value: int) -> str:
    if not rule_name:
        return str(attr_value)

    base = rule_name[:-2] if rule_name.endswith("报警") else rule_name
    if attr_value == 0:
        return base
    if attr_value == 1 and base.startswith("未"):
        return "已" + base[1:]
    return base


def _extract_aiop_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Parse Hikvision AIOP_Polling_Snap style JSON payloads."""
    result: dict[str, Any] = {}

    result["device_id"] = payload.get("deviceID") or payload.get("deviceId")
    result["date_time"] = payload.get("dateTime")
    result["event_type"] = payload.get("eventType")

    aiop_data = payload.get("AIOPData") or {}
    alert_info = (aiop_data.get("events") or {}).get("alertInfo") or []
    if not alert_info:
        return result

    alert = alert_info[0]
    rule_info = alert.get("ruleInfo") or {}
    rule_name = rule_info.get("ruleName") or ""
    target_id = (alert.get("target") or {}).get("id")

    attr_value = 0
    attr_conf = 0
    for target in aiop_data.get("targets") or []:
        obj = target.get("obj") or {}
        if obj.get("id") != target_id:
            continue
        properties = target.get("properties") or []
        if not properties:
            break
        classify = properties[0].get("classify") or {}
        attr_value = _to_int(classify.get("attrValue"))
        attr_conf = _to_int(classify.get("attrConf"))
        break

    result["rule_name"] = rule_name
    result["attr_value"] = attr_value
    result["attr_conf"] = attr_conf
    result["attr_label"] = _derive_attr_label(rule_name, attr_value)

    pic_url = payload.get("url")
    if pic_url:
        result["image_url_remote"] = str(pic_url)

    return result


def _extract_generic_json(payload: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key in ("deviceID", "deviceId", "dateTime", "eventType"):
        if payload.get(key):
            normalized = {
                "deviceID": "device_id",
                "deviceId": "device_id",
                "dateTime": "date_time",
                "eventType": "event_type",
            }[key]
            result[normalized] = payload[key]

    rule_name = _find_json_value(payload, "ruleName", "rule_name")
    attr_label = _find_json_value(payload, "attrLabel", "attr_label")
    attr_value = _find_json_value(payload, "attrValue", "attr_value")
    attr_conf = _find_json_value(payload, "attrConf", "attr_conf", "confidence")
    pic_url = payload.get("url") or _find_json_value(payload, "imageUrl", "imageURL", "pictureURL")

    if rule_name:
        result["rule_name"] = str(rule_name)
    if attr_label:
        result["attr_label"] = str(attr_label)
    if attr_value is not None:
        result["attr_value"] = _to_int(attr_value)
    if attr_conf is not None:
        result["attr_conf"] = _to_int(attr_conf)
    if pic_url:
        result["image_url_remote"] = str(pic_url)

    return result


def _find_json_value(data: Any, *keys: str) -> Optional[Any]:
    key_set = {key.lower() for key in keys}
    if isinstance(data, dict):
        for key, value in data.items():
            if key.lower() in key_set:
                return value
        for value in data.values():
            found = _find_json_value(value, *keys)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _find_json_value(item, *keys)
            if found is not None:
                return found
    return None


def _set_text_field(result: dict[str, Any], key: str, value: str) -> None:
    if value and not result.get(key):
        result[key] = value


def _extract_from_texts(raw_xml: Optional[str], raw_json: Optional[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for text in (raw_xml, raw_json):
        if not text:
            continue

        _set_text_field(result, "rule_name", _tag(text, "ruleName") or _tag(text, "rule_name"))
        _set_text_field(result, "attr_label", _tag(text, "attrLabel") or _tag(text, "attr_label"))
        if "attr_value" not in result:
            attr_value = _tag(text, "attrValue") or _tag(text, "attr_value")
            if attr_value != "":
                result["attr_value"] = _to_int(attr_value)
        if "attr_conf" not in result:
            attr_conf = _tag(text, "attrConf") or _tag(text, "attr_conf")
            if attr_conf != "":
                result["attr_conf"] = _to_int(attr_conf)

    if raw_json:
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            if payload.get("AIOPData"):
                aiop_fields = _extract_aiop_fields(payload)
                for key, value in aiop_fields.items():
                    if value is not None and value != "":
                        result[key] = value
            else:
                generic_fields = _extract_generic_json(payload)
                for key, value in generic_fields.items():
                    if value is not None and value != "" and key not in result:
                        result[key] = value

    return result


def _resolve_storage_path(name_or_path: str) -> Optional[str]:
    candidate = Path(name_or_path)
    if candidate.is_file():
        return str(candidate.resolve())

    storage_candidate = STORAGE_DIR / candidate.name
    if storage_candidate.is_file():
        return str(storage_candidate.resolve())
    return None


def _download_alarm_image(url: str, device_id: str) -> Optional[str]:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.md5(url.encode("utf-8")).hexdigest()[:16]
    safe_device = re.sub(r"[^\w.-]", "_", device_id or "unknown")
    file_path = STORAGE_DIR / f"{safe_device}_{digest}.jpg"

    if file_path.is_file():
        return str(file_path.resolve())

    request = urllib.request.Request(url, headers={"User-Agent": "XY-Alarm-Platform/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            file_path.write_bytes(response.read())
        return str(file_path.resolve())
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def _find_recent_storage_image(within_seconds: int = 60) -> Optional[str]:
    if not STORAGE_DIR.exists():
        return None

    import time

    now = time.time()
    latest: Optional[Path] = None
    latest_mtime = 0.0

    for path in STORAGE_DIR.glob("*"):
        if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        mtime = path.stat().st_mtime
        if now - mtime <= within_seconds and mtime >= latest_mtime:
            latest = path
            latest_mtime = mtime

    return str(latest.resolve()) if latest else None


def enrich_alarm_event(event: AlarmEventIn) -> AlarmEventIn:
    extracted = _extract_from_texts(event.raw_xml, event.raw_json)

    rule_name = extracted.get("rule_name") or event.event_type or "未知告警"
    attr_value = extracted.get("attr_value", 0)
    attr_conf = extracted.get("attr_conf", 0)
    attr_label = extracted.get("attr_label") or _derive_attr_label(rule_name, attr_value)

    image_path = extracted.get("image_path")
    remote_url = extracted.get("image_url_remote")
    device_id = extracted.get("device_id") or event.device_id or ""

    if remote_url:
        image_path = _download_alarm_image(remote_url, device_id)
        if not image_path:
            image_path = match_storage_by_url(remote_url)

    if not image_path:
        image_path = _find_recent_storage_image()

    if not image_path:
        image_path = find_unclaimed_recent()

    if image_path:
        mark_image_used(image_path)

    updates = {
        "rule_name": rule_name,
        "attr_value": attr_value,
        "attr_label": attr_label,
        "attr_conf": attr_conf,
        "image_path": image_path,
    }

    if extracted.get("device_id"):
        updates["device_id"] = extracted["device_id"]
    if extracted.get("date_time"):
        updates["date_time"] = extracted["date_time"]
    if extracted.get("event_type"):
        updates["event_type"] = extracted["event_type"]

    return event.model_copy(update=updates)
