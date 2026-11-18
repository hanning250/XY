# -*- coding: utf-8 -*-
"""★ 告警报文解析。

海康 ISUP 上报的告警是 **XML**（`EventNotificationAlert`），不是 JSON。
实测报文样例（box001 / HaiKang-1 摄像头）：

    <?xml version="1.0" encoding="UTF-8"?>
    <EventNotificationAlert version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
      <ipAddress>192.168.1.10</ipAddress>
      <portNo>7663</portNo>
      <protocol>EHome</protocol>
      <macAddress>bc:9b:5e:66:ae:c3</macAddress>
      <dynChannelID>1</dynChannelID>
      <channelID>1</channelID>
      <dateTime>2026-09-17T14:39:36+08:00</dateTime>
      <eventType>IO</eventType>
      <eventState>active</eventState>
      <eventDescription>IO alarm</eventDescription>
      <inputIOPortID>1</inputIOPortID>
      <channelName>测试</channelName>
      <deviceID>HaiKang-1</deviceID>
    </EventNotificationAlert>

注意命名空间是 http://www.hikvision.com/ver20/XMLSchema，
解析时必须做**无命名空间匹配**，否则所有字段都取不到。
"""

from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime

from server.services.aiop_parser import parse_aiop

logger = logging.getLogger(__name__)

# 告警类型映射：ISUP 的 dwAlarmType → 可读文本
ALARM_TYPE_TEXT: dict[int, str] = {
    0: "未知",
    1: "移动侦测",
    2: "视频遮挡",
    3: "视频丢失",
    5: "区域入侵",
    6: "越界侦测",
    7: "进入区域",
    8: "离开区域",
    9: "徘徊侦测",
    10: "人员聚集",
    11: "快速移动",
    12: "停车侦测",
    13: "ISAPI 事件上报",
    15: "物品遗留",
    16: "物品拿取",
    17: "人脸抓拍",
}

# XML 里的 eventType → 中文
EVENT_TYPE_TEXT: dict[str, str] = {
    "IO": "IO 报警",
    "VMD": "移动侦测",
    "linedetection": "越界侦测",
    "fielddetection": "区域入侵",
    "regionEntrance": "进入区域",
    "regionExiting": "离开区域",
    "facedetection": "人脸侦测",
    "faceSnap": "人脸抓拍",
    "motion": "移动侦测",
    "tamperdetection": "视频遮挡",
    "videoloss": "视频丢失",
    "alarmResult": "报警结果",
    # AIOP（AI 开放平台）
    "AIOP_Polling_Snap": "AI 智能抓拍",
    "AIOP_Snap": "AI 智能抓拍",
}


@dataclass(slots=True)
class ParsedAlarm:
    """解析后的告警。所有字段都可能为空（报文格式随设备而异）。"""

    device_id: str = ""
    channel: int = 1
    # ★ 通道号是否真的从报文里解析到了。
    #   为 False 时 channel 只是「默认值 1」，不代表设备真的报的是通道 1。
    #   调用方应据此决定是否用其它来源（SDK 事件）覆盖，绝不能把默认值当成事实。
    channel_known: bool = False
    alarm_type: int = 0
    event_type: str = ""
    event_state: str = ""
    event_description: str = ""
    alarm_time: datetime | None = None
    ip_address: str = ""
    channel_name: str = ""
    mac_address: str = ""
    # ★ 多通道/多租户归属识别用（不硬编码任何具体设备，全部来自报文）
    child_dev_id: str = ""       # 子设备 ID：每个通道唯一
    task_id: str = ""            # 算法任务 ID：每个任务唯一
    raw_kind: str = ""  # xml / json / unknown
    extra: dict = field(default_factory=dict)
    # ★ AIOP（AI 开放平台智能分析）专用字段
    is_aiop: bool = False
    rule_name: str = ""          # 命中的规则名，如「未穿防护服报警」
    mp_name: str = ""            # 算法模型名
    person_count: int = 0
    alarmed_count: int = 0
    summary: str = ""            # 一句话摘要
    aiop: dict = field(default_factory=dict)  # AIOP 结构化成 dict

    @property
    def type_text(self) -> str:
        # ★ AIOP 告警优先用命中的规则名（这才是业务语义）
        if self.rule_name:
            return self.rule_name
        if self.event_type:
            return EVENT_TYPE_TEXT.get(
                self.event_type, f"{self.event_type}"
            )
        return ALARM_TYPE_TEXT.get(self.alarm_type, f"告警({self.alarm_type})")


def _strip_ns(tag: str) -> str:
    """去掉 XML 命名空间前缀：{http://...}deviceID -> deviceID"""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _flatten(elem: ET.Element) -> dict[str, str]:
    """把 XML 拍平成 {标签名: 文本}。

    同名标签后者覆盖前者（告警报文一般不会重复关键字段）。
    """
    out: dict[str, str] = {}
    for child in elem.iter():
        name = _strip_ns(child.tag)
        text = (child.text or "").strip()
        if text:
            out[name] = text
    return out


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    # 2026-09-17T14:39:36+08:00
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(value, fmt)
            # 统一转成 naive 本地时间，与 DB 里的口径一致
            if dt.tzinfo is not None:
                dt = dt.astimezone().replace(tzinfo=None)
            return dt
        except ValueError:
            continue
    return None


def _int(value: str | None, default: int = 1) -> int:
    if value is None:
        return default
    m = re.search(r"-?\d+", str(value))
    return int(m.group()) if m else default


# ★ 通道号候选键，按可信度排序。
#   不同设备/固件用的键名不一样（实测见过 channelID / dynChannelID，
#   有的 JSON 报文用 channel / channelNo）。这里集中定义，避免各处硬编码。
_CHANNEL_KEYS = ("channelID", "dynChannelID", "channelNo", "channel")

# ★ 身份字段候选键：用于「哪路视频 / 哪个算法任务」，是做多车间(多租户)
#   归属判断的依据。全部来自报文本身，不依赖任何具体设备型号。
_CHILD_DEV_KEYS = ("childDevID", "ChildDevID", "childDeviceID", "subDevID")
_TASK_KEYS = ("taskID", "TaskID", "taskId")


def _pick(data: dict, keys: tuple[str, ...]) -> str:
    """按候选键顺序取第一个非空值（统一转成 str）。"""
    for k in keys:
        v = data.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return ""


def _resolve_channel(data: dict) -> tuple[int, bool]:
    """从报文里解出通道号。

    返回 (通道号, 是否真的解析到了)。

    ★ 关键：必须区分「设备明确上报通道 2」和「报文里没这个字段」。
      旧实现把两者都变成 1，导致通道 2 的告警被静默记成通道 1。
    """
    raw = _pick(data, _CHANNEL_KEYS)
    if not raw:
        return 1, False
    m = re.search(r"-?\d+", raw)
    if not m:
        return 1, False
    n = int(m.group())
    return (n if n > 0 else 1), True


def _resolve_identity(data: dict) -> tuple[str, str]:
    """解出子设备 ID 与任务 ID（用于区分视频通道 / 算法任务）。"""
    return _pick(data, _CHILD_DEV_KEYS), _pick(data, _TASK_KEYS)


def parse_alarm_payload(
    text: str | None,
    *,
    alarm_type: int = 0,
    device_id_hint: str = "",
) -> ParsedAlarm:
    """解析告警报文。自动识别 XML / JSON，返回结构化结果。"""
    result = ParsedAlarm(alarm_type=alarm_type)

    if not text:
        result.device_id = device_id_hint
        return result

    stripped = text.strip()

    # ---------------- XML（海康实际格式）----------------
    if stripped.startswith("<"):
        result.raw_kind = "xml"
        try:
            root = ET.fromstring(stripped)
            flat = _flatten(root)

            result.device_id = flat.get("deviceID") or flat.get("DeviceID") or device_id_hint
            # ★ 通道号：区分「解析到」与「默认值」
            result.channel, result.channel_known = _resolve_channel(flat)
            result.event_type = flat.get("eventType", "")
            result.event_state = flat.get("eventState", "")
            result.event_description = flat.get("eventDescription", "")
            result.ip_address = flat.get("ipAddress", "")
            result.channel_name = flat.get("channelName", "")
            result.mac_address = flat.get("macAddress", "")
            result.alarm_time = _parse_datetime(flat.get("dateTime", ""))
            result.child_dev_id, result.task_id = _resolve_identity(flat)
            result.extra = flat

            if not result.device_id:
                # 退化：用 IP 当设备标识，至少能区分不同设备
                result.device_id = result.ip_address or device_id_hint
            return result
        except ET.ParseError as e:
            logger.warning("XML 解析失败: %s", e)
            # 兜底：正则抠关键字段
            # ★ 注意：这里也要走 _resolve_channel，否则「正则兜底路径」会把
            #   通道号静默退化成 1，与正常路径行为不一致。
            grabbed: dict[str, str] = {}
            for key in (
                "deviceID", "eventType", "ipAddress", "channelName",
                "macAddress", "childDevID", "taskID",
                *_CHANNEL_KEYS,
            ):
                m = re.search(rf"<{key}>([^<]*)</{key}>", stripped)
                if m:
                    grabbed[key] = m.group(1).strip()

            result.device_id = grabbed.get("deviceID", "")
            result.channel, result.channel_known = _resolve_channel(grabbed)
            result.event_type = grabbed.get("eventType", "")
            result.ip_address = grabbed.get("ipAddress", "")
            result.channel_name = grabbed.get("channelName", "")
            result.mac_address = grabbed.get("macAddress", "")
            result.child_dev_id, result.task_id = _resolve_identity(grabbed)
            result.raw_kind = "xml-regex"
            if not result.device_id:
                result.device_id = result.ip_address or device_id_hint
            return result

    # ---------------- JSON ----------------
    if stripped.startswith("{") or stripped.startswith("["):
        result.raw_kind = "json"
        try:
            obj = json.loads(stripped)
            if isinstance(obj, list):
                obj = obj[0] if obj else {}
            if isinstance(obj, dict):
                result.extra = obj
                result.device_id = str(
                    obj.get("deviceID") or obj.get("DeviceID") or device_id_hint or ""
                )
                # ★ 通道号：区分「解析到」与「默认值」（与 XML 分支同一套逻辑）
                result.channel, result.channel_known = _resolve_channel(obj)
                result.event_type = str(obj.get("eventType") or "")
                result.event_description = str(obj.get("eventDescription") or "")
                result.ip_address = str(obj.get("ipAddress") or "")
                result.channel_name = str(obj.get("channelName") or "")
                result.mac_address = str(obj.get("macAddress") or "")
                result.alarm_time = _parse_datetime(str(obj.get("dateTime") or ""))
                result.child_dev_id, result.task_id = _resolve_identity(obj)
                # JSON 里也可能有嵌套的 ANPR/人脸信息
                for nested in ("ANPR", "FaceInfo", "HumanInfo", "EventInfo"):
                    if nested in obj and isinstance(obj[nested], dict):
                        result.extra[nested] = obj[nested]

                # ★ AIOP（AI 开放平台智能分析）—— 「未穿防护服」等业务告警
                aiop = parse_aiop(obj)
                if aiop.is_aiop:
                    result.is_aiop = True
                    result.rule_name = aiop.rule_name
                    result.mp_name = aiop.mp_name
                    result.person_count = aiop.person_count
                    result.alarmed_count = aiop.alarmed_count
                    result.summary = aiop.summary
                    # ★ 仅当顶层报文没给出通道号时，才用 AIOP 里的。
                    #   否则会覆盖掉顶层更权威的 channelID（实测 AIOP 报文
                    #   顶层 channelID=2，而 AIOPData 内可能没有该字段）。
                    if not result.channel_known and aiop.channel:
                        result.channel = aiop.channel
                        result.channel_known = True
                    # ★ taskID 兜底：顶层没有时用 AIOP 解析结果
                    if not result.task_id and aiop.task_id:
                        result.task_id = aiop.task_id
                    result.aiop = {
                        "mpid": aiop.mpid,
                        "mpName": aiop.mp_name,
                        "taskID": aiop.task_id,
                        "ruleName": aiop.rule_name,
                        "ruleID": aiop.rule_id,
                        "graphWidth": aiop.frame_width,
                        "graphHeight": aiop.frame_height,
                        "personCount": aiop.person_count,
                        "alarmedCount": aiop.alarmed_count,
                        "errorcode": aiop.errorcode,
                        "polygon": aiop.polygon,
                        "targets": [
                            {
                                "id": t.target_id,
                                "objType": t.obj_type,
                                "objTypeText": t.obj_type_text,
                                "confidence": t.confidence,
                                "confidencePct": t.confidence_pct,
                                "attrType": t.attr_type,
                                "attrValue": t.attr_value,
                                "attrText": t.attr_text,
                                "attrConf": t.attr_conf,
                                "alarmed": t.is_alarmed,
                                "rect": t.rect,
                            }
                            for t in aiop.targets
                        ],
                    }

                if not result.device_id:
                    result.device_id = result.ip_address or device_id_hint
            return result
        except ValueError:
            logger.warning("JSON 解析失败: %s", stripped[:120])

    # ---------------- 未知格式 ----------------
    result.raw_kind = "unknown"
    result.device_id = device_id_hint
    logger.warning("未知告警报文格式: %s", stripped[:160])
    return result
