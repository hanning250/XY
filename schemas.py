# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    status_label: str
    time: str


class AlarmServiceStatus(BaseModel):
    state: str
    state_label: str
    protocol: Optional[str] = None
    last_error: Optional[str] = None
    started_at: Optional[str] = None
    last_alarm_at: Optional[str] = None
    registered_devices: int = 0
    device_ids: List[str] = Field(default_factory=list)


class StatusResponse(BaseModel):
    isup_enabled: bool
    isup_enabled_label: str
    platform_ip: Optional[str] = None
    cms_port: int
    ams_port: int
    api_port: int
    alarm_service: AlarmServiceStatus


class AlarmRecord(BaseModel):
    id: int
    created_at: str
    device_ip: Optional[str] = None
    device_serial: Optional[str] = None
    command_type: Optional[str] = None
    command_type_label: Optional[str] = None
    event_type: Optional[str] = None
    event_type_label: Optional[str] = None
    event_description: Optional[str] = None
    rule_name: Optional[str] = None
    target_type: Optional[str] = None
    region_name: Optional[str] = None
    channel_no: Optional[int] = None
    event_time: Optional[str] = None
    raw_payload: Optional[str] = None
    picture_paths: List[str] = Field(default_factory=list)
    picture_urls: List[str] = Field(default_factory=list)
    is_ppe_related: bool = False
    ppe_label: str = "其他告警"
    title: Optional[str] = None
    detail_text: Optional[str] = None
    summary: Optional[str] = None


class AlarmStatsResponse(BaseModel):
    total: int
    ppe_related: int
    total_label: str
    ppe_related_label: str
    summary: str


class SseEventMessage(BaseModel):
    type: str
    data: Dict[str, Any]
