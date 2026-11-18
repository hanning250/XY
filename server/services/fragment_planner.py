# -*- coding: utf-8 -*-
"""回放片段数据结构（合并逻辑在 playback_service._register_in_plan）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class CapturePlan:
    """一段要抓取的视频 —— 可能服务多条报警。"""

    device_id: str
    channel: int
    # 抓取区间（含 pre/post 外扩）
    start: datetime
    end: datetime
    # 归属这只片段的报警 ID
    alarm_ids: list[str] = field(default_factory=list)
    # 该片段所属的自然分钟（用于 key 与去重）
    minute: datetime = field(default_factory=datetime.now)

    @property
    def key(self) -> tuple[str, int, datetime]:
        return (self.device_id, self.channel, self.minute)

    @property
    def span_seconds(self) -> float:
        return (self.end - self.start).total_seconds()
