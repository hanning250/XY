# -*- coding: utf-8 -*-
import json
import re
from typing import Optional


# 键名为 eventType 经 _normalize_key 后的值（小写、去空格和下划线）
EVENT_TYPE_LABELS = {
    # AI 开放平台
    "aioppollingsnap": "AI 轮询抓拍",
    "aiopvideo": "AI 视频分析",
    "aioppollingvideo": "AI 轮询视频",
    "aioppicture": "AI 图片分析",
    "aievent": "AI 事件",
    # 人脸
    "facesnap": "人脸抓拍",
    "facecontrast": "人脸比对",
    "facecontrastsuccess": "人脸比对成功",
    "facecontrastfailure": "人脸比对失败",
    "facesnapmodeling": "人脸建模",
    "whitelistfacecontrast": "白名单人脸比对",
    # PPE / 行为
    "reflectivevestdetection": "反光衣检测",
    "safetyhelmetdetection": "安全帽检测",
    "safetyvestdetection": "安全背心检测",
    "workweardetection": "工服检测",
    "ppedetection": "PPE 检测",
    "behavioranalysis": "行为分析",
    # 常规智能事件
    "fielddetection": "区域入侵",
    "linedetection": "越界侦测",
    "regionentrance": "进入区域",
    "regionexiting": "离开区域",
    "loitering": "徘徊侦测",
    "vmd": "移动侦测",
    "io": "报警输入",
    "recordingfailure": "录像异常",
    "diskfull": "硬盘满",
    "diskerror": "硬盘错误",
    "unsupportedevent": "未解析事件",
    "unknown": "未知事件",
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
    result = {"event_description": None, "rule_name": None}
    if not raw_payload:
        return result

    text = raw_payload.strip()
    if not text:
        return result

    if text.startswith("{") or text.startswith("["):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return result
        if isinstance(data, dict):
            result["event_description"] = _extract_from_json(
                data, "eventDescription", "description", "alarmDescription", "subEventType"
            )
            result["rule_name"] = _extract_from_json(data, "ruleName", "rule_name")
        return result

    for tag, field in (("eventDescription", "event_description"), ("ruleName", "rule_name")):
        match = re.search(rf"<{tag}>([^<]+)</{tag}>", text, flags=re.IGNORECASE)
        if match:
            result[field] = match.group(1).strip()
    return result


def label_event_type(event_type: Optional[str], raw_payload: Optional[str] = None) -> str:
    if not event_type:
        return "未知事件"

    normalized = _normalize_key(event_type)
    if normalized in EVENT_TYPE_LABELS:
        return EVENT_TYPE_LABELS[normalized]

    if re.search(r"[\u4e00-\u9fff]", event_type):
        return event_type.strip()

    fields = extract_alarm_fields(raw_payload)
    description = fields.get("event_description")
    if description:
        return description

    return event_type


def label_ppe_related(is_ppe_related: bool) -> str:
    return "防护服相关" if is_ppe_related else "其他告警"


def build_alarm_summary(alarm: dict) -> str:
    fields = extract_alarm_fields(alarm.get("raw_payload"))
    event_label = label_event_type(alarm.get("event_type"), alarm.get("raw_payload"))

    if fields.get("event_description") and re.search(r"[\u4e00-\u9fff]", fields["event_description"]):
        title = fields["event_description"]
    elif fields.get("rule_name"):
        title = f"{event_label} · {fields['rule_name']}"
    else:
        title = event_label

    parts = []
    channel_no = alarm.get("channel_no")
    if channel_no is not None:
        parts.append(f"通道 {channel_no}")
    parts.append(title)
    parts.append(label_ppe_related(bool(alarm.get("is_ppe_related"))))
    if alarm.get("device_serial"):
        parts.append(alarm["device_serial"])
    return " · ".join(parts)


def enrich_alarm(alarm: dict) -> dict:
    item = dict(alarm)
    item["event_type_label"] = label_event_type(item.get("event_type"), item.get("raw_payload"))
    item["ppe_label"] = label_ppe_related(bool(item.get("is_ppe_related")))
    item["summary"] = build_alarm_summary(item)
    return item
