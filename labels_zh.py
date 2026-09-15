# -*- coding: utf-8 -*-
import json
import re
from typing import Optional


COMMAND_TYPE_LABELS = {
    "EHOME_ISAPI_ALARM": "ISUP ISAPI 智能告警",
    "EHOME_ALARM": "ISUP 基础告警",
    "HTTP_ISAPI": "HTTP 事件上报",
    "TEST_INJECT": "测试告警",
}

EVENT_TYPE_LABELS = {
    "reflectivevestdetection": "反光衣检测",
    "safetyhelmetdetection": "安全帽检测",
    "safetyvestdetection": "安全背心检测",
    "workwear detection": "工服检测",
    "ppe detection": "PPE 检测",
    "behavioranalysis": "行为分析",
    "aievent": "AI 事件",
    "aiop_video": "AI 视频分析",
    "fielddetection": "区域入侵",
    "unsupported_event": "未解析事件",
    "unknown": "未知事件",
}

SERVICE_STATE_LABELS = {
    "running": "运行中",
    "starting": "启动中",
    "error": "异常",
    "stopped": "已停止",
    "disabled": "已禁用",
}

HEALTH_STATUS_LABELS = {
    "ok": "正常",
    "error": "异常",
}


def _normalize_key(value: Optional[str]) -> str:
    return str(value or "").strip().lower().replace(" ", "").replace("_", "")


def _extract_from_json(data: dict, *keys: str) -> Optional[str]:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    alert = data.get("EventNotificationAlert")
    if isinstance(alert, dict):
        for key in keys:
            value = alert.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def extract_alarm_fields(raw_payload: Optional[str]) -> dict:
    result = {
        "event_description": None,
        "rule_name": None,
        "target_type": None,
        "region_name": None,
    }
    if not raw_payload:
        return result

    text = raw_payload.strip()
    if not text:
        return result

    if text.startswith("{") or text.startswith("["):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            result["event_description"] = _extract_from_json(
                data, "eventDescription", "description", "alarmDescription", "subEventType"
            )
            result["rule_name"] = _extract_from_json(data, "ruleName", "rule_name")
            result["target_type"] = _extract_from_json(data, "targetType", "target_type")
            result["region_name"] = _extract_from_json(data, "regionName", "region_name")
            flat = _flatten_payload(data)
            if not result["rule_name"]:
                result["rule_name"] = flat.get("ruleName") or flat.get("AIOPData.ruleName")
            if not result["target_type"]:
                result["target_type"] = flat.get("targetType") or flat.get("target.type")
            if not result["region_name"]:
                result["region_name"] = flat.get("regionName")
            if not result["event_description"]:
                result["event_description"] = flat.get("eventDescription")
        return result

    for tag, field in (
        ("eventDescription", "event_description"),
        ("ruleName", "rule_name"),
        ("targetType", "target_type"),
        ("regionName", "region_name"),
    ):
        match = re.search(rf"<{tag}>([^<]+)</{tag}>", text, flags=re.IGNORECASE)
        if match:
            result[field] = match.group(1).strip()
    return result


def _flatten_payload(data, prefix=""):
    result = {}
    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, (dict, list)):
                result.update(_flatten_payload(value, new_key))
            elif isinstance(value, str):
                result[new_key] = value
    elif isinstance(data, list):
        for index, value in enumerate(data):
            result.update(_flatten_payload(value, f"{prefix}[{index}]"))
    return result


def _extract_description_from_payload(raw_payload: Optional[str]) -> Optional[str]:
    fields = extract_alarm_fields(raw_payload)
    return fields.get("event_description")


def label_command_type(command_type: Optional[str]) -> str:
    if not command_type:
        return "未知来源"
    return COMMAND_TYPE_LABELS.get(command_type, command_type)


def label_event_type(
    event_type: Optional[str],
    raw_payload: Optional[str] = None,
) -> str:
    if not event_type:
        return "未知事件"

    normalized = _normalize_key(event_type)
    if normalized in EVENT_TYPE_LABELS:
        return EVENT_TYPE_LABELS[normalized]

    if re.search(r"[\u4e00-\u9fff]", event_type):
        return event_type.strip()

    description = _extract_description_from_payload(raw_payload)
    if description and re.search(r"[\u4e00-\u9fff]", description):
        return description

    if description:
        return description

    return event_type


def label_ppe_related(is_ppe_related: bool) -> str:
    return "防护服相关" if is_ppe_related else "其他告警"


def label_service_state(state: Optional[str]) -> str:
    if not state:
        return "未知状态"
    return SERVICE_STATE_LABELS.get(state, state)


def label_health_status(status: Optional[str]) -> str:
    if not status:
        return "未知"
    return HEALTH_STATUS_LABELS.get(status, status)


def label_isup_enabled(enabled: bool) -> str:
    return "ISUP 已启用" if enabled else "ISUP 已禁用"


def build_alarm_title(alarm: dict) -> str:
    event_label = label_event_type(alarm.get("event_type"), alarm.get("raw_payload"))
    fields = extract_alarm_fields(alarm.get("raw_payload"))
    if fields.get("event_description") and re.search(r"[\u4e00-\u9fff]", fields["event_description"]):
        return fields["event_description"]
    if fields.get("rule_name"):
        return f"{event_label} · {fields['rule_name']}"
    return event_label


def build_alarm_detail(alarm: dict) -> str:
    fields = extract_alarm_fields(alarm.get("raw_payload"))
    lines = []

    event_label = label_event_type(alarm.get("event_type"), alarm.get("raw_payload"))
    lines.append(f"事件类型：{event_label}")

    if fields.get("event_description"):
        lines.append(f"事件描述：{fields['event_description']}")
    if fields.get("rule_name"):
        lines.append(f"规则名称：{fields['rule_name']}")
    if fields.get("target_type"):
        lines.append(f"目标类型：{fields['target_type']}")
    if fields.get("region_name"):
        lines.append(f"区域名称：{fields['region_name']}")

    channel_no = alarm.get("channel_no")
    if channel_no is not None:
        lines.append(f"通道号：{channel_no}")

    device_serial = alarm.get("device_serial")
    if device_serial:
        lines.append(f"设备序列号：{device_serial}")

    device_ip = alarm.get("device_ip")
    if device_ip:
        lines.append(f"平台 IP：{device_ip}")

    event_time = alarm.get("event_time") or alarm.get("created_at")
    if event_time:
        lines.append(f"发生时间：{event_time}")

    lines.append(f"告警分类：{label_ppe_related(bool(alarm.get('is_ppe_related')))}")
    return "\n".join(lines)


def build_alarm_summary(alarm: dict) -> str:
    parts = []
    channel_no = alarm.get("channel_no")
    if channel_no is not None:
        parts.append(f"通道 {channel_no}")

    parts.append(build_alarm_title(alarm))
    parts.append(label_ppe_related(bool(alarm.get("is_ppe_related"))))

    device_serial = alarm.get("device_serial")
    if device_serial:
        parts.append(device_serial)

    return " · ".join(parts)


def enrich_alarm(alarm: dict) -> dict:
    item = dict(alarm)
    fields = extract_alarm_fields(item.get("raw_payload"))
    item["command_type_label"] = label_command_type(item.get("command_type"))
    item["event_type_label"] = label_event_type(
        item.get("event_type"),
        item.get("raw_payload"),
    )
    item["ppe_label"] = label_ppe_related(bool(item.get("is_ppe_related")))
    item["event_description"] = fields.get("event_description")
    item["rule_name"] = fields.get("rule_name")
    item["target_type"] = fields.get("target_type")
    item["region_name"] = fields.get("region_name")
    item["title"] = build_alarm_title(item)
    item["detail_text"] = build_alarm_detail(item)
    item["summary"] = build_alarm_summary(item)
    return item


def enrich_service_status(status: dict) -> dict:
    item = dict(status)
    item["state_label"] = label_service_state(item.get("state"))
    item.setdefault("device_ids", [])
    item.setdefault("registered_devices", 0)
    return item
