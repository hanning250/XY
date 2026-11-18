# -*- coding: utf-8 -*-
"""★ 内部统计接口（按登录账号的车间权限过滤）。

## 为什么单独一个模块

需求：**每个车间报警频率统计要按账号来统计不同车间**。

这件事的口径必须是：
    · 车间子账号 → 只看到自己那几个车间的频率
    · admin      → 看到全部
    · 未分配车间的账号 → 什么都看不到（默认拒绝）

过滤统一走 `principal.visible_workshops()`，聚合逻辑在
`crud/alarm.count_workshop_frequency()` —— 与看板、告警列表同一套
车间隔离口径，不会出现「列表看不到但统计里有」这种自相矛盾。

## 和 dashboard 的区别

    /api/alarms/dashboard  看板用：今日/昨日/待处理 + 各车间分布（固定口径）
    /api/stats/workshops   频率分析：任意时间区间 + 按小时/按天分桶
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.base import Principal
from server.auth.deps import require
from server.crud import alarm as alarm_crud
from server.db import get_session
from server.services import timeutil

router = APIRouter(prefix="/stats", tags=["内部-统计"])


@router.get(
    "/workshops",
    summary="★ 各车间的报警频率（按当前账号可见车间过滤）",
)
async def workshop_frequency(
    start: datetime | None = Query(
        None, description="起始时间（含）。默认 = 当前时间往前 24 小时"
    ),
    end: datetime | None = Query(
        None, description="结束时间（不含）。默认 = 当前时间"
    ),
    bucket: str = Query("hour", pattern="^(hour|day)$", description="分桶粒度"),
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require("alarm:read")),
):
    """按车间统计报警**频率**。

    频率 = 区间内条数 ÷ 区间小时数，单位「次/小时」。
    多车间横向对比时用它 —— 不同车间、不同区间长度下，
    裸条数没法直接比。

    ★ 只返回当前账号有权查看的车间：
        · 车间子账号 → 只有自己那几个
        · admin      → 全部
        · 未分配车间 → 空列表（默认拒绝）

    返回每个车间还带 `channels` / `channels_online`，
    用来区分「这个车间没报警」是**真没违规**还是**设备掉线了**。
    """
    now = timeutil.now_local()
    t_end = end or now
    t_start = start or (t_end - timedelta(hours=24))
    if t_start >= t_end:
        t_start, t_end = t_end, t_start

    items = await alarm_crud.count_workshop_frequency(
        db,
        start=t_start,
        end=t_end,
        workshops=principal.visible_workshops(),
        bucket=bucket,
    )

    total = sum(i["total"] for i in items)
    hours = max((t_end - t_start).total_seconds() / 3600.0, 1e-9)
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "range_start": timeutil.to_iso_local(t_start),
            "range_end": timeutil.to_iso_local(t_end),
            "bucket": bucket,
            "span_hours": round(hours, 3),
            "total": total,
            "per_hour": round(total / hours, 3),
            "items": items,
        },
    }
