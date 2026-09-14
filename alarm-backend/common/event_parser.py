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


def _pick_field(fields, *names, prefixes=("", "EventNotificationAlert.")):
    """在扁平化后的字段里按候选键名取值。

    海康 ISAPI 推送常见两种形态：扁平结构，以及外面包一层
    EventNotificationAlert 的嵌套结构；这里两种都能命中。
    """
    for name in names:
        for prefix in prefixes:
            value = fields.get(f"{prefix}{name}")
            if value not in (None, ""):
                return value
    return None


def _parse_json_payload(text):
    data = json.loads(text)
    fields = _flatten_json(data)
    event_type = _pick_event_type(fields, data)
    event_description = _pick_field(fields, "eventDescription", "description", "alarmDescription")
    rule_name = _pick_field(fields, "ruleName", "rule_name", "AIOPData.ruleName")
    channel_no = _to_int(
        _pick_field(
            fields, "channelID", "channelNo", "channel", "dynChannelID", "srcInputPort"
        )
    )
    event_time = _pick_field(fields, "dateTime", "eventTime", "time", "activePost.time")
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
        _pick_field(fields, "eventType"),
        _pick_field(fields, "eventDescription"),
        _pick_field(fields, "subEventType"),
        _pick_field(fields, "type"),
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


# ---------------------------------------------------------------------------
# AI 开放平台（AIOP）解析
# ---------------------------------------------------------------------------
# 海康 AI 开放平台把算法结果以 JSON 透传，结构见
#   https://open.hikvision.com/hardware/v2/JSON文件/AIOPData示例Json数据.html
#
# {
#   "width": "512", "height": "288",
#   "targets": [
#     { "obj": { "modelID": "...", "id": 1, "type": 0, "confidence": 1000,
#                "valid": 1, "visible": 1,
#                "rect": { "x": "0.21", "y": "0.58", "w": "0.14", "h": "0.40" } },
#       "properties": [ { "classify": { "attrType": 1, "attrValue": 1, "attrConf": 1000 } } ] }
#   ],
#   "events": { "alertInfo": [ { "target": {...}, "ruleInfo": { "ruleID": 1, ... } } ] }
# }
#
# 注意：obj.type 是算法自定义的整数类别号，含义由设备的模型包决定，
# 需要通过 ISAPI 读取模型包描述，或在 config.json 的 "aiop_type_labels" 里手工映射。

_AIOP_JSON_KEYS = ("targets", "events", "width", "height")


def _decode_text(raw):
    for encoding in ("utf-8", "gbk", "latin-1"):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, AttributeError):
            continue
    return ""


def looks_like_aiop_json(raw_bytes):
    """判断一段字节是否是 AIOP 的 JSON（用于定位变长缓冲区里的 JSON 起点）。"""
    if not raw_bytes:
        return False
    head = raw_bytes[:200].lstrip(b"\xef\xbb\xbf \t\r\n\x00")
    if not head.startswith(b"{"):
        return False
    return any(key.encode() in raw_bytes[:4096] for key in _AIOP_JSON_KEYS)


def parse_aiop_data(raw_bytes, type_labels=None):
    """解析 AIOP 透传的 JSON，抽出目标框、置信度和事件信息。

    type_labels: 可选的 {类别号: 名称} 映射，来自 config.json 的 aiop_type_labels。
    """
    text = _decode_text(raw_bytes).strip().strip("\x00").strip()
    if not text:
        return _empty_aiop_result()

    # 兼容个别固件在 JSON 后面拼接了额外内容的情况
    try:
        data = json.loads(text)
    except ValueError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return {
                "aiop": {
                    "parsed": False,
                    "error": "AIOPData 不是合法 JSON",
                    "confidence": None,
                    "targets": [],
                    "target_count": 0,
                    "rect": None,
                    "event": None,
                },
                "raw_text": text,
            }
        try:
            data = json.loads(text[start : end + 1])
        except ValueError as exc:
            return {
                "aiop": {
                    "parsed": False,
                    "error": f"AIOPData JSON 解析失败: {exc}",
                    "confidence": None,
                    "targets": [],
                    "target_count": 0,
                    "rect": None,
                    "event": None,
                },
                "raw_text": text,
            }

    if not isinstance(data, dict):
        data = {}

    labels = type_labels or {}
    targets = []
    for index, item in enumerate(data.get("targets") or []):
        if not isinstance(item, dict):
            continue
        obj = item.get("obj") if isinstance(item.get("obj"), dict) else {}
        properties = item.get("properties")
        classify = None
        if isinstance(properties, list) and properties:
            first = properties[0]
            if isinstance(first, dict) and isinstance(first.get("classify"), dict):
                classify = first["classify"]

        type_code = _to_int(obj.get("type"))
        targets.append(
            {
                "index": index,
                "id": _to_int(obj.get("id")),
                "type": type_code,
                "label": labels.get(str(type_code), labels.get(type_code)),
                "model_id": obj.get("modelID"),
                "confidence": _to_int(obj.get("confidence")),
                "valid": _to_int(obj.get("valid")),
                "visible": _to_int(obj.get("visible")),
                "rect": _normalize_rect(obj.get("rect")),
                "classify": classify,
            }
        )

    # 取置信度最高（且有效）的目标作为主报警目标
    best = None
    for target in targets:
        if target.get("visible") == 0 and len(targets) > 1:
            continue
        if best is None or (target.get("confidence") or 0) > (best.get("confidence") or 0):
            best = target
    if best is None and targets:
        best = targets[0]

    return {
        "aiop": {
            "parsed": True,
            "error": None,
            "width": _to_int(data.get("width")),
            "height": _to_int(data.get("height")),
            "targets": targets,
            "target_count": len(targets),
            "confidence": best.get("confidence") if best else None,
            "type": best.get("type") if best else None,
            "label": best.get("label") if best else None,
            "rect": best.get("rect") if best else None,
            "event": _extract_aiop_event(data),
        },
        "raw_text": text,
    }


def _empty_aiop_result():
    return {
        "aiop": {
            "parsed": False,
            "error": None,
            "confidence": None,
            "targets": [],
            "target_count": 0,
            "rect": None,
            "event": None,
        },
        "raw_text": "",
    }


def _normalize_rect(rect):
    """矩形框统一转成 float 的 0~1 相对坐标。"""
    if not isinstance(rect, dict):
        return None
    result = {}
    for key in ("x", "y", "w", "h"):
        value = rect.get(key)
        if value is None:
            return None
        try:
            result[key] = float(value)
        except (TypeError, ValueError):
            return None
    return result


def _extract_aiop_event(data):
    """从 events.alertInfo[0] 中抽取规则信息。"""
    events = data.get("events")
    if not isinstance(events, dict):
        return None
    alerts = events.get("alertInfo")
    if not isinstance(alerts, list) or not alerts:
        return None
    first = alerts[0]
    if not isinstance(first, dict):
        return None

    rule = first.get("ruleInfo") if isinstance(first.get("ruleInfo"), dict) else {}
    target = first.get("target") if isinstance(first.get("target"), dict) else {}
    return {
        "rule_id": _to_int(rule.get("ruleID")),
        "trigger_type": _to_int(rule.get("triggerType")),
        "move_direction": _to_int(rule.get("movDir")),
        "target_id": _to_int(target.get("id")),
        "target_type": _to_int(target.get("type")),
        "confidence": _to_int(target.get("confidence")),
        "region": _normalize_rect(
            (target.get("region") or {}).get("rect")
            if isinstance(target.get("region"), dict)
            else None
        ),
    }


def aiop_event_type(aiop, mpid=None):
    """根据 AIOP 解析结果推导一个可读的 event_type 字符串。"""
    if aiop.get("label"):
        return str(aiop["label"])
    if aiop.get("type") is not None:
        return f"aiop_type_{aiop['type']}"
    event = aiop.get("event") or {}
    if event.get("rule_id") is not None:
        return f"aiop_rule_{event['rule_id']}"
    if mpid:
        return f"aiop_{str(mpid).strip().strip(chr(0))}"
    return "aiop_polling_snap"


def is_aiop_ppe_related(aiop, label_hints):
    """用配置里的标签/关键字判断 AIOP 目标是否属于防护服类告警。"""
    parts = [
        aiop.get("label"),
        aiop.get("type"),
        json.dumps(aiop.get("event"), ensure_ascii=False) if aiop.get("event") else None,
    ]
    haystack = " ".join(str(part) for part in parts if part).lower()
    for hint in label_hints or []:
        if str(hint).lower() in haystack:
            return True
    return False
