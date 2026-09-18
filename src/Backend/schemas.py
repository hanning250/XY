# -*- coding: utf-8 -*-
"""Pydantic schemas for alarm API."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AlarmEventIn(BaseModel):
    handle: Optional[int] = None
    alarm_type: int
    device_id: Optional[str] = None
    event_type: Optional[str] = None
    event_state: Optional[str] = None
    io_port: Optional[str] = None
    date_time: Optional[str] = None
    channel_name: Optional[str] = None
    channel_id: Optional[str] = None
    isapi_data_type: Optional[int] = None
    pictures_number: Optional[int] = None
    raw_xml: Optional[str] = None
    raw_json: Optional[str] = None
    cms_user_id: Optional[int] = None
    rule_name: Optional[str] = None
    attr_value: Optional[int] = None
    attr_label: Optional[str] = None
    attr_conf: Optional[int] = None
    image_path: Optional[str] = None


class AlarmEventOut(AlarmEventIn):
    id: int
    created_at: str


class AlarmClientView(BaseModel):
    """Fields exposed to frontend clients."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    alarm_time: str = Field(serialization_alias="alarmTime")
    device_id: str = Field(serialization_alias="deviceId")
    rule_name: str = Field(serialization_alias="ruleName")
    attr_value: int = Field(serialization_alias="attrValue")
    attr_label: str = Field(serialization_alias="attrLabel")
    attr_conf: int = Field(serialization_alias="attrConf")
    image_url: str = Field(serialization_alias="imageUrl")


class AlarmClientListResponse(BaseModel):
    total: int
    items: list[AlarmClientView]


class AlarmStats(BaseModel):
    total: int
    active: int
    inactive: int
    by_event_type: dict[str, int]
    by_device: dict[str, int]
