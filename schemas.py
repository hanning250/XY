# -*- coding: utf-8 -*-
from typing import List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    time: str


class StatusResponse(BaseModel):
    platform_ip: Optional[str] = None
    api_port: int
    event_path: str


class AlarmRecord(BaseModel):
    id: int
    created_at: str
    device_ip: Optional[str] = None
    device_serial: Optional[str] = None
    event_type: Optional[str] = None
    event_type_label: Optional[str] = None
    channel_no: Optional[int] = None
    event_time: Optional[str] = None
    raw_payload: Optional[str] = None
    picture_urls: List[str] = Field(default_factory=list)
    is_ppe_related: bool = False
    ppe_label: str = "其他告警"
    summary: Optional[str] = None


class AlarmStatsResponse(BaseModel):
    total: int
    ppe_related: int
