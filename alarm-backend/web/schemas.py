# -*- coding: utf-8 -*-
"""接口响应模型 + 数据库行转响应模型的辅助函数。"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from common.alarm_view import serialize_alarm


class HealthResponse(BaseModel):
    status: str
    time: str


class IsupDevice(BaseModel):
    """通过 ISUP 注册上来的设备。"""

    login_id: Optional[int] = None
    device_id: Optional[str] = None
    serial: Optional[str] = None
    device_name: Optional[str] = None
    device_ip: Optional[str] = None
    device_port: Optional[int] = None
    protocol_version: Optional[str] = None
    firmware: Optional[str] = None
    full_serial: Optional[str] = None
    state: Optional[str] = None  # online / offline
    online_at: Optional[str] = None
    offline_at: Optional[str] = None
    last_event: Optional[str] = None
    last_event_type: Optional[str] = None
    parse_error: Optional[str] = None


class IsupAlarmServiceStatus(BaseModel):
    state: str
    last_error: Optional[str] = None
    last_connected_at: Optional[str] = None
    last_alarm_at: Optional[str] = None
    reconnect_count: int = 0
    alarm_mode: Optional[str] = None
    listen_ip: Optional[str] = None
    register_port: Optional[int] = None
    alarm_port: Optional[int] = None
    protocol: Optional[str] = None
    devices_online: int = 0
    devices: List[IsupDevice] = Field(default_factory=list)
    received_alarms: int = 0
    dropped_alarms: int = 0


class StatusResponse(BaseModel):
    sdk_enabled: bool
    alarm_mode: str
    api_port: int
    alarm_service: IsupAlarmServiceStatus


class AlarmRecord(BaseModel):
    id: int
    created_at: str
    device_ip: Optional[str] = None
    device_serial: Optional[str] = None
    command_type: Optional[str] = None
    event_type: Optional[str] = None
    channel_no: Optional[int] = None
    event_time: Optional[str] = None
    raw_payload: Optional[str] = None
    picture_paths: List[str] = Field(default_factory=list)
    picture_urls: List[str] = Field(default_factory=list)
    is_ppe_related: bool = False
    # 解析结果（AIOP targets/rect/置信度，或 ISAPI 字段）
    analysis: Optional[Dict[str, Any]] = None
    event_detail: Optional[Dict[str, Any]] = None
    confidence: Optional[int] = None
    target_count: Optional[int] = None
    duration_ms: Optional[int] = None


class AlarmStatsResponse(BaseModel):
    total: int
    ppe_related: int


class EventPushResponse(BaseModel):
    accepted: bool
    alarm_id: int
    content_type: str
    event_type: str
    is_ppe_related: bool


class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]


def to_alarm_record(alarm: dict) -> AlarmRecord:
    """数据库行 → 接口响应模型。"""
    return AlarmRecord(**serialize_alarm(alarm))
