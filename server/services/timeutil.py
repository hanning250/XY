# -*- coding: utf-8 -*-
"""★ 时间口径统一 —— 全项目唯一的时间转换入口。

## 背景（这是一个真实存在过的 Bug）

数据库里同一条记录的两个时间字段曾经**差 8 小时**：

    alarm_time  = 17:29:48   ← 本地时间（设备上报 +08:00，代码转成了 naive 本地）
    created_at  = 09:29:37   ← UTC（models.utcnow() 存的是 UTC naive）

两者其实是**同一个瞬间**。混用会导致：
  · 按时间过滤/统计错 8 小时
  · 图片与告警的时间差算错（配对出错）
  · **对外 API 返回裸时间戳，对方不知道时区 → 显示错 8 小时**

## 统一约定（本项目从此遵守）

    ① **数据库内统一存 naive 本地时间**（东八区）
       —— 因为设备上报的就是本地时间，而现场就一个时区，
          存本地时间最直观、排查最方便。

    ② **对外 API 一律返回带时区的 ISO8601**
       —— `2026-09-28T17:29:48+08:00`
          对方拿到就知道时区，不会误解。

    ③ **接收外部时间参数时**，带时区的按其偏移转换，不带的按本地时间理解。

改造时的兼容性：历史数据里 created_at 是 UTC naive，读出来会比 alarm_time
小 8 小时。用 `utc_naive_to_local()` 可做一次性纠正。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

# 本项目部署在中国，固定东八区。
# 不用 time.localtime 是因为服务器时区可能是 UTC（容器里很常见），
# 那样会让结果随部署环境变化 —— 显式固定更可靠。
LOCAL_TZ = timezone(timedelta(hours=8))
LOCAL_TZ_NAME = "+08:00"


def now_local() -> datetime:
    """当前本地时间（naive，东八区）。**替代 datetime.now()**。"""
    return datetime.now(LOCAL_TZ).replace(tzinfo=None)


def utcnow_naive() -> datetime:
    """当前 UTC 时间（naive）。仅用于确实需要 UTC 的场景。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_naive_to_local(dt: datetime | None) -> datetime | None:
    """把「UTC naive」转成「本地 naive」。

    用于纠正历史遗留数据（created_at 等字段曾以 UTC 存储）。
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(LOCAL_TZ).replace(tzinfo=None)
    # naive 视为 UTC，加 8 小时
    return (dt.replace(tzinfo=timezone.utc)).astimezone(LOCAL_TZ).replace(tzinfo=None)


def to_local_naive(dt: datetime | None) -> datetime | None:
    """把任意 datetime（带或不带时区）统一成本地 naive。

    · 带时区 → 按其偏移换算到东八区
    · 不带时区 → **视为已经是本地时间**，原样返回
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(LOCAL_TZ).replace(tzinfo=None)


def to_iso_local(dt: datetime | None) -> str | None:
    """★ 对外 API 输出：带 +08:00 的 ISO8601 字符串。

    这是给 IT 部门的时间格式 —— 带时区，对方不会误解。
    """
    if dt is None:
        return None
    local = to_local_naive(dt)
    if local is None:
        return None
    return local.replace(tzinfo=LOCAL_TZ).isoformat()


def parse_any(value: str | None) -> datetime | None:
    """★ 对外 API 入参：解析时间字符串为本地 naive。

    兼容：
      · 2026-09-28T17:29:48+08:00   （带时区，推荐）
      · 2026-09-28T17:29:48Z        （UTC）
      · 2026-09-28T17:29:48         （视为本地）
      · 2026-09-28 17:29:48
      · 2026-09-28                  （当天 00:00:00）
    """
    text = (value or "").strip()
    if not text:
        return None

    # 纯日期 → 当天 00:00:00
    if len(text) == 10 and text.count("-") == 2:
        try:
            return datetime.strptime(text, "%Y-%m-%d")
        except ValueError:
            return None

    normalized = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
            try:
                dt = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            return None

    return to_local_naive(dt)


def day_bounds(date_text: str) -> tuple[datetime, datetime]:
    """给定 YYYY-MM-DD，返回 [当天00:00, 次日00:00) 左闭右开区间。

    ★ 左闭右开是刻意的：相邻两天拉取不会在边界重复。
    """
    start = datetime.strptime(date_text, "%Y-%m-%d")
    return start, start + timedelta(days=1)
