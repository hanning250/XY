# -*- coding: utf-8 -*-
"""★ AIOP（AI Open Platform）告警解析。

海康「AI 开放平台」设备（如 box001）上报的智能分析告警，
报文是 **JSON**，结构比普通 IO 报警复杂得多，携带完整的算法结果。

实测报文（box001，「未穿防护服」场景）：

    {
      "deviceID": "box001",
      "eventType": "AIOP_Polling_Snap",
      "MPName": "德阳三环净化室防护服检测",     ← 算法模型名
      "MPID": "e70c82eb352e4a3c91b9c0f2e82",
      "taskID": "8cg2ab248489fag2gb9fea38ge342376",
      "AIOPData": {
        "width": "1920", "height": "1088",
        "targets": [
          { "obj": {"id":1,"type":1,"confidence":999,
                    "rect":{"x":"0.660937","y":"0.358696",...}},
            "properties": [{"classify":{"attrType":0,"attrValue":1,"attrConf":1000}}] },
          { "obj": {"id":2,"type":1,"confidence":999,
                    "rect":{"x":"0.106250","y":"0.005435",...}},
            "properties": [{"classify":{"attrType":0,"attrValue":0,"attrConf":998}}] }
        ],
        "events": { "alertInfo": [ {
            "target": {"id": 2, "confidence": 998, ...},
            "ruleInfo": {"ruleID":1, "ruleName":"未穿防护服报警",
                         "triggerType":1073758209, "region":{"polygon":[...]}}
        } ] },
        "algoVerifyInfo": {...}
      }
    }

★★ 关键语义（实测推导，已与数据交叉验证）：

    alertInfo[].target.id  = 2
    targets[1].obj.id      = 2  → 它的 attrValue = 0

    → **attrValue=0 表示「未穿」，attrValue=1 表示「已穿」**
      （告警命中的目标，其 attrValue 就是 0）

    验证方法：告警命中的 target.id，去 targets 里找到同一个 obj.id，
             看它的 attrValue 即可确认语义。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# obj.type 取值
OBJ_TYPE_TEXT = {
    0: "未知",
    1: "人",
    2: "车",
    3: "非机动车",
}

# 已知的 AIOP 事件类型
AIOP_EVENT_TEXT = {
    "AIOP_Polling_Snap": "AI 抓拍",
    "AIOP_Snap": "AI 抓拍",
}

# 防护服属性判定（attrType=0）
ATTR_VALUE_TEXT = {
    0: "未穿",
    1: "已穿",
}


@dataclass(slots=True)
class AiopTarget:
    """一个检测目标。"""

    target_id: int = 0
    obj_type: int = 0
    confidence: int = 0          # 千分比
    attr_type: int | None = None
    attr_value: int | None = None
    attr_conf: int | None = None
    rect: dict[str, float] = field(default_factory=dict)
    # 是否被某条规则命中
    is_alarmed: bool = False

    @property
    def obj_type_text(self) -> str:
        return OBJ_TYPE_TEXT.get(self.obj_type, f"类型{self.obj_type}")

    @property
    def attr_text(self) -> str:
        if self.attr_value is None:
            return ""
        return ATTR_VALUE_TEXT.get(self.attr_value, f"attrValue={self.attr_value}")

    @property
    def confidence_pct(self) -> float:
        return round(self.confidence / 10.0, 1)


@dataclass(slots=True)
class AiopAlarm:
    """AIOP 告警的完整业务语义。"""

    is_aiop: bool = False
    device_id: str = ""
    # ★ 0 = 报文未提供通道号（未知）；>0 = 设备明确上报的通道
    channel: int = 0
    event_type: str = ""
    mpid: str = ""
    mp_name: str = ""              # 算法模型名
    task_id: str = ""
    # ★ 业务上的告警类型（命中的规则名）
    rule_name: str = ""
    rule_id: int | None = None
    trigger_type: int | None = None
    frame_width: int = 0
    frame_height: int = 0
    targets: list[AiopTarget] = field(default_factory=list)
    # 命中的告警目标（通常是未穿防护服的那些人）
    alarmed_targets: list[AiopTarget] = field(default_factory=list)
    polygon: list[dict[str, float]] = field(default_factory=list)
    errorcode: int | None = None
    time_stamp: int = 0

    @property
    def person_count(self) -> int:
        return sum(1 for t in self.targets if t.obj_type == 1)

    @property
    def alarmed_count(self) -> int:
        return len(self.alarmed_targets)

    @property
    def summary(self) -> str:
        """给前端/IT 部门看的一句话摘要。"""
        if not self.is_aiop:
            return ""
        parts = []
        if self.rule_name:
            parts.append(self.rule_name)
        parts.append(f"检出 {self.person_count} 人")
        if self.alarmed_count:
            parts.append(f"其中 {self.alarmed_count} 人违规")
        return "，".join(parts)


def _to_float(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _to_int(v: Any) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def parse_aiop(obj: dict) -> AiopAlarm:
    """从告警 JSON 里解析 AIOP 结构。非 AIOP 报文返回 is_aiop=False。"""
    result = AiopAlarm()

    if not isinstance(obj, dict):
        return result

    event_type = str(obj.get("eventType") or "")
    aiop_data = obj.get("AIOPData")

    # 判定是不是 AIOP：有 AIOPData 或 eventType 以 AIOP 开头
    if not isinstance(aiop_data, dict) and not event_type.startswith("AIOP"):
        return result

    result.is_aiop = True
    result.device_id = str(obj.get("deviceID") or "")
    # ★ 与 alarm_parser 保持一致：区分「解析到」与「默认值」。
    #   解析不到时置 0，由调用方决定兜底，避免把「未知」伪装成「通道 1」。
    _ch = obj.get("channelID")
    result.channel = _to_int(_ch) if _ch not in (None, "") else 0
    result.event_type = event_type
    result.mpid = str(obj.get("MPID") or "")
    result.mp_name = str(obj.get("MPName") or "")
    result.task_id = str(obj.get("taskID") or "")

    if not isinstance(aiop_data, dict):
        return result

    result.errorcode = _to_int(aiop_data.get("errorcode"))
    result.frame_width = _to_int(aiop_data.get("width"))
    result.frame_height = _to_int(aiop_data.get("height"))
    result.time_stamp = _to_int(aiop_data.get("timeStamp"))

    # ---- targets ----
    by_id: dict[int, AiopTarget] = {}
    for raw_t in aiop_data.get("targets") or []:
        if not isinstance(raw_t, dict):
            continue
        o = raw_t.get("obj") or {}
        rect_raw = o.get("rect") or {}
        t = AiopTarget(
            target_id=_to_int(o.get("id")),
            obj_type=_to_int(o.get("type")),
            confidence=_to_int(o.get("confidence")),
            rect={
                "x": _to_float(rect_raw.get("x")),
                "y": _to_float(rect_raw.get("y")),
                "w": _to_float(rect_raw.get("w")),
                "h": _to_float(rect_raw.get("h")),
            },
        )
        # 取第一个 classify 属性
        for prop in raw_t.get("properties") or []:
            if not isinstance(prop, dict):
                continue
            cl = prop.get("classify")
            if isinstance(cl, dict):
                t.attr_type = _to_int(cl.get("attrType"))
                t.attr_value = _to_int(cl.get("attrValue"))
                t.attr_conf = _to_int(cl.get("attrConf"))
                break
        result.targets.append(t)
        by_id[t.target_id] = t

    # ---- events.alertInfo：命中的规则 ----
    events = aiop_data.get("events") or {}
    for alert in (events.get("alertInfo") or []) if isinstance(events, dict) else []:
        if not isinstance(alert, dict):
            continue
        ri = alert.get("ruleInfo") or {}
        if not result.rule_name and ri.get("ruleName"):
            result.rule_name = str(ri["ruleName"])
        if result.rule_id is None and ri.get("ruleID") is not None:
            result.rule_id = _to_int(ri.get("ruleID"))
        if result.trigger_type is None and ri.get("triggerType") is not None:
            result.trigger_type = _to_int(ri.get("triggerType"))
        if not result.polygon:
            poly = (ri.get("region") or {}).get("polygon") or []
            result.polygon = [
                {"x": _to_float(p.get("x")), "y": _to_float(p.get("y"))}
                for p in poly
                if isinstance(p, dict)
            ]

        # ★ 命中的目标：用 target.id 回查，标记 is_alarmed
        tgt = alert.get("target") or {}
        tid = _to_int(tgt.get("id"))
        hit = by_id.get(tid)
        if hit is not None:
            hit.is_alarmed = True
            if hit not in result.alarmed_targets:
                result.alarmed_targets.append(hit)

    # 兜底：没有 alertInfo 时，把所有 attrValue=0 的当异常
    if not result.alarmed_targets:
        for t in result.targets:
            if t.attr_value == 0:
                result.alarmed_targets.append(t)

    return result
