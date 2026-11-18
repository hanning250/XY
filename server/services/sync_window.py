# -*- coding: utf-8 -*-
"""★ 开放 API 的「取数窗口」计算（纯函数，便于单测）。

甲方的用法是**每 10 分钟拉一次，每次都要成功**。这要求服务端替对方
把"该拉哪一段"算准，而不是让对方用本地时钟自己算 —— 两边时钟差几秒，
就可能在窗口边界漏掉或重复数据。

## 三个概念

① **全钟点对齐窗口**（`resolve_window`）
       window=10m，现在 10:23 → 最近一个"已结束"的窗口是 [10:10, 10:20)

② **保护期**（`grace_seconds`）
       只吐「已经过去 N 秒」的数据。因为视频是异步转码的（实测 2~10 秒），
       窗口刚结束就立刻拉，最后几条的 video_url 还是 null。
       留 60 秒保护期，对方拿到的每条记录视频都已就绪。

③ **水位**（由 sync_token 承载，见 crud/pagination.py）
       兜底「同一秒产生多条告警」的情况：只用时间戳当水位会漏掉同秒的其它记录，
       所以水位必须是 (alarm_time, id) 二元组。

## 为什么窗口从固定纪元对齐

    以 2000-01-01 为锚点按分钟取整 → 跨天、跨月都连续，
    不会出现"每天 00:00 的窗口和前一天对不上"的缝隙。
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

__all__ = [
    "parse_window",
    "floor_to_window",
    "resolve_window",
    "settled_before",
]

# 对齐锚点：固定纪元，保证任意时刻的窗口边界都可复现
_EPOCH = datetime(2000, 1, 1)

_WINDOW_RE = re.compile(r"^\s*(\d+)\s*([mh])\s*$", re.IGNORECASE)


def parse_window(text: str) -> timedelta:
    """解析窗口表达式：`10m` / `30m` / `1h`。

    只支持分钟与小时 —— 秒级窗口对这个场景没有意义，
    而天级窗口甲方用 `date` 参数更直观。
    """
    m = _WINDOW_RE.match(text or "")
    if not m:
        raise ValueError(
            f"window 格式无效: {text!r}（支持 10m / 30m / 1h 这种写法）"
        )
    n, unit = int(m.group(1)), m.group(2).lower()
    if n <= 0:
        raise ValueError("window 必须大于 0")
    return timedelta(minutes=n) if unit == "m" else timedelta(hours=n)


def floor_to_window(dt: datetime, window: timedelta) -> datetime:
    """把时刻向下取整到窗口边界（秒与微秒归零）。"""
    total_minutes = int((dt - _EPOCH).total_seconds() // 60)
    step = max(1, int(window.total_seconds() // 60))
    return _EPOCH + timedelta(minutes=(total_minutes // step) * step)


def resolve_window(
    now: datetime,
    window: timedelta,
    grace_seconds: int = 0,
) -> tuple[datetime, datetime]:
    """返回**最近一个已结束**的对齐窗口 `[start, end)`。

    例：now=10:23，window=10 分钟，grace=60 秒
        → 10:23-60s = 10:22 → 向下取整 10:20 → end=10:20, start=10:10
        → 返回 (10:10, 10:20)

    ★ end 一定是「现在 - 保护期」之前，所以窗口内的数据都已落库、
      视频也有足够时间转码完成。
    """
    effective = now - timedelta(seconds=max(0, int(grace_seconds)))
    end = floor_to_window(effective, window)
    return end - window, end


def settled_before(now: datetime, grace_seconds: int = 0) -> datetime:
    """增量模式（sync_token）的上界：只取「已经稳定」的数据。"""
    return now - timedelta(seconds=max(0, int(grace_seconds)))
