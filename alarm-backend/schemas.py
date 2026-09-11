# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    time: str


class AlarmServiceStatus(BaseModel):
    state: str
    last_error: Optional[str] = None
    last_connected_at: Optional[str] = None
    last_alarm_at: Optional[str] = None
    reconnect_count: int = 0
    alarm_mode: Optional[str] = None


class StatusResponse(BaseModel):
    sdk_enabled: bool
    nvr_ip: Optional[str] = None
    alarm_mode: str
    api_port: int
    alarm_service: AlarmServiceStatus


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
