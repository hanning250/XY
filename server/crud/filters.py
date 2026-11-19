# -*- coding: utf-8 -*-
"""★ 告警查询条件对象（替代「一堆平铺参数」）。

改造前的样子：

    async def list_alarms_offset(
        db, *, page=1, size=20,
        device_id=None, channel=None, alarm_type=None,
        start=None, end=None, status=None,
        handled=None, has_image=None, workshops=None,
    ) -> ...:

12 个参数，其中 8 个只是「原样转发给 SQL 拼条件」，函数体一行都没用到
它们的业务含义。同一个条件集合在 list_alarms_cursor 里又抄了一遍 ——
加一个筛选条件的成本是「改两处签名 + 两处转发 + 两个调用点」。

现在：**条件归条件，分页归分页**。

    AlarmFilter(device_id=..., has_image=True, workshops=["A"])
    list_alarms_offset(db, f=flt, page=1, size=20)

好处：
  ① 加筛选条件只动这个 dataclass + to_conditions() 一处；
  ② offset / cursor 两种分页**共用同一份条件**，不可能再漂移；
  ③ 车间隔离的三态语义在这里收口（见 crud/scoping.py）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, select

from server.crud.scoping import is_denied, workshop_scope
from server.models import Alarm, AlarmImage

__all__ = ["AlarmFilter"]


@dataclass(slots=True)
class AlarmFilter:
    """告警列表的筛选条件。所有字段都是「不传即不过滤」。

    三态字段（None / True / False）语义必须保持，前端 UI 依赖它们：
      · handled   —— None=全部, True=已处理, False=未处理
      · has_image —— None=全部, True=有抓拍图, False=无图（排查用）
      · workshops —— None=不过滤, []=什么都看不到, [...]=只这些车间
    """

    device_id: str | None = None
    channel: int | None = None
    alarm_type: int | None = None
    start: datetime | None = None
    end: datetime | None = None
    # ★ 内部接口用左闭右闭 [start, end]；开放 API 用左闭右开 [start, end)
    #   —— 相邻两天不能重复，这是甲方按天拉取的硬要求。
    end_exclusive: bool = False
    status: str | None = None
    handled: bool | None = None
    has_image: bool | None = None
    workshops: list[str] | None = None
    # ★ 甲方筛选：区域（单车间 code）+ 报警类型（AIOP 规则名）
    workshop: str | None = None
    rule_name: str | None = None

    # ------------------------------------------------------------------
    def _effective_workshops(self) -> list[str] | None:
        """可见车间与单车间筛选求交后的最终列表。"""
        scoped = self.workshops
        if self.workshop:
            code = self.workshop.strip()
            if scoped is None:
                return [code]
            return [w for w in scoped if w == code]
        return list(scoped) if scoped is not None else None

    def is_denied(self) -> bool:
        """该条件是否必然返回空集（没有分配车间 / 筛选越权）。"""
        return is_denied(self._effective_workshops())

    def to_conditions(self) -> list[ColumnElement]:
        """翻译成 SQLAlchemy 条件列表。

        调用前请先判断 is_denied()：空车间列表在这里只会变成
        `IN ()`（SQLite 上恒假），但**上层需要返回自己的空值形态**，
        不能指望这里兜底。
        """
        conds: list[ColumnElement] = []

        # ---- 来源 ----
        if self.device_id:
            conds.append(Alarm.device_id == self.device_id)
        if self.channel is not None:
            conds.append(Alarm.channel == self.channel)
        if self.alarm_type is not None:
            conds.append(Alarm.alarm_type == self.alarm_type)

        # ---- 时间区间 ----
        #   内部接口：左闭右闭（历史行为，前端筛选器就是这么传的）
        #   开放 API：左闭右开（相邻两天不重复）
        if self.start:
            conds.append(Alarm.alarm_time >= self.start)
        if self.end:
            if self.end_exclusive:
                conds.append(Alarm.alarm_time < self.end)
            else:
                conds.append(Alarm.alarm_time <= self.end)

        # ---- 状态 / 处置 ----
        if self.status:
            conds.append(Alarm.status == self.status)
        if self.handled is not None:
            conds.append(Alarm.handled.is_(bool(self.handled)))

        # ---- 抓拍图：EXISTS 半连接，避免 JOIN 产生重复行 ----
        if self.has_image is not None:
            img_exists = select(AlarmImage.id).where(
                AlarmImage.alarm_id == Alarm.id
            ).exists()
            conds.append(img_exists if self.has_image else ~img_exists)

        # ---- 报警类型（规则名，精确匹配）----
        if self.rule_name:
            conds.append(Alarm.rule_name == self.rule_name)

        # ---- 车间隔离（数据不串的核心）----
        conds.extend(workshop_scope(Alarm.workshop, self._effective_workshops()))
        return conds
