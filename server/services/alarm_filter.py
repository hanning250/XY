# -*- coding: utf-8 -*-
"""★ 设备黑名单：忽略指定设备上报的告警。

背景（实测）：
  · HaiKang-1（海康摄像头）每秒重复上报 IO 告警，**没有业务含义**，
    且它不上传图片（图片由 box001 上传），只会淹没真实告警。
  · box001（AI 盒子）上报的是 AIOP 智能分析告警（未穿防护服），**才是业务要的**。

因此需要能按设备/事件类型过滤掉噪音告警。
"""

from __future__ import annotations

import logging

from server.config import get_settings

logger = logging.getLogger(__name__)


class AlarmFilter:
    """告警过滤器。支持按 device_id 和 eventType 屏蔽。"""

    def __init__(self) -> None:
        s = get_settings()
        # 逗号分隔的设备黑名单
        self.ignore_devices: set[str] = {
            x.strip() for x in (s.ignore_devices or "").split(",") if x.strip()
        }
        # 逗号分隔的事件类型黑名单
        self.ignore_event_types: set[str] = {
            x.strip() for x in (s.ignore_event_types or "").split(",") if x.strip()
        }
        # 白名单：非空时只接受这些设备
        self.allow_devices: set[str] = {
            x.strip() for x in (s.allow_devices or "").split(",") if x.strip()
        }
        self._logged: set[str] = set()

    @property
    def enabled(self) -> bool:
        return bool(self.ignore_devices or self.ignore_event_types or self.allow_devices)

    def should_ignore(self, device_id: str, event_type: str) -> tuple[bool, str]:
        """返回 (是否忽略, 原因)。"""
        if self.allow_devices and device_id and device_id not in self.allow_devices:
            return True, f"设备 {device_id} 不在白名单"
        if device_id and device_id in self.ignore_devices:
            return True, f"设备 {device_id} 在黑名单"
        if event_type and event_type in self.ignore_event_types:
            return True, f"事件类型 {event_type} 在黑名单"
        return False, ""

    def log_once(self, key: str, message: str) -> None:
        """同一原因只打一次日志，避免刷屏。"""
        if key not in self._logged:
            self._logged.add(key)
            logger.info(message)

    def describe(self) -> str:
        parts = []
        if self.allow_devices:
            parts.append(f"白名单={sorted(self.allow_devices)}")
        if self.ignore_devices:
            parts.append(f"设备黑名单={sorted(self.ignore_devices)}")
        if self.ignore_event_types:
            parts.append(f"事件黑名单={sorted(self.ignore_event_types)}")
        return " | ".join(parts) if parts else "未启用"


_filter: AlarmFilter | None = None


def get_filter() -> AlarmFilter:
    global _filter
    if _filter is None:
        _filter = AlarmFilter()
    return _filter


def reset_filter() -> None:
    """配置变更后重置（测试用）。"""
    global _filter
    _filter = None
