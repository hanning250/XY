# -*- coding: utf-8 -*-
"""Map persisted alarms to frontend-facing payloads."""
from src.Backend.schemas import AlarmClientView, AlarmEventOut


def to_client_view(alarm: AlarmEventOut) -> AlarmClientView:
    alarm_time = alarm.date_time or alarm.created_at.replace(" ", "T") + "+08:00"
    return AlarmClientView(
        id=alarm.id,
        alarm_time=alarm_time,
        device_id=alarm.device_id or "",
        rule_name=alarm.rule_name or alarm.event_type or "未知告警",
        attr_value=alarm.attr_value if alarm.attr_value is not None else 0,
        attr_label=alarm.attr_label or "",
        attr_conf=alarm.attr_conf if alarm.attr_conf is not None else 0,
        image_url=f"/api/alarms/{alarm.id}/image",
    )
