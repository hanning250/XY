# -*- coding: utf-8 -*-
"""游标分页工具。

★ 为什么不用 offset 分页（docs §8.2）：
   告警数据在**持续写入**。用 OFFSET 翻页时，新数据插入会导致
   后一页重复或漏掉记录。对外接口必须用游标分页。

游标 = base64(JSON{...})，按 (alarm_time ASC, id ASC) 稳定排序，
用 `id` 作 tiebreaker —— 实测同一秒有多条记录，只按时间会重复/丢数据。

★★ 2026-09-30 修复：游标必须**绑定查询范围**
    原实现只把 `alarm_time` 当裸的下界用，**不校验 workshop / 日期区间**。
    后果：把 A 日期的游标拿去查 B 日期，会静默丢掉 B 日期在游标之前的所有记录，
    而且返回 HTTP 200 + has_more=false —— **看起来像"这天没数据"**。

    实测：用 09-28 的游标查 09-23，返回 0 条（实际有 2 条），无任何报错。

    对甲方（每天定时拉取）这是致命场景：**重试时复用了上次的游标，
    整天的数据会静默消失**。

    所以现在把 workshop 与时间区间一起写进游标，不匹配就报错，
    让调用方立刻发现用错了游标，而不是拿到一份缺数据的"成功"响应。
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Cursor:
    """解析后的游标，含它所属的查询范围。"""

    alarm_time: datetime
    alarm_id: str
    # 绑定范围（可能为空：表示该次查询没有限定）
    workshop: str | None = None
    range_start: str | None = None
    range_end: str | None = None
    # ★ 取数模式（absolute / window / sync / cursor）
    #   翻页时沿用，保证第 1 页与第 N 页的响应结构一致，
    #   否则对方按 mode 判断逻辑会在翻页时突然变样。
    mode: str | None = None


def encode_cursor(
    alarm_time: datetime,
    alarm_id: str,
    *,
    workshop: str | None = None,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
    mode: str | None = None,
) -> str:
    """生成游标。

    ★ 把 workshop 与时间区间一并写入 —— 这样才能在下一次请求时
      校验「你用的游标是不是这次查询的」，避免跨范围复用导致静默丢数据。
    """
    payload: dict = {"t": alarm_time.isoformat(), "i": alarm_id}
    if workshop:
        payload["w"] = workshop
    if range_start is not None:
        payload["s"] = range_start.isoformat()
    if range_end is not None:
        payload["e"] = range_end.isoformat()
    if mode:
        payload["m"] = mode
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(cursor: str) -> Cursor | None:
    """解析游标。非法游标返回 None。

    ★ 向后兼容：旧游标没有 `m` 字段，`payload.get` 得到 None，
      调用方按"沿用当前模式"处理即可。
    """
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
        return Cursor(
            alarm_time=datetime.fromisoformat(payload["t"]),
            alarm_id=str(payload["i"]),
            workshop=payload.get("w"),
            range_start=payload.get("s"),
            range_end=payload.get("e"),
            mode=payload.get("m"),
        )
    except Exception:
        return None


def cursor_matches(
    cur: Cursor,
    *,
    workshop: str | None,
    range_start: datetime | None,
    range_end: datetime | None,
) -> tuple[bool, str]:
    """校验游标是否属于本次查询范围。

    返回 (是否匹配, 不匹配的原因)。

    ★ 这是防「静默丢数据」的关键：范围不一致时必须**报错**，
      而不是照常执行 —— 否则调用方会拿到一份缺数据的 200 响应。
    """
    if cur.workshop and workshop and cur.workshop != workshop:
        return False, (
            f"游标属于车间 {cur.workshop}，但本次请求指定的是 {workshop}。"
            "请勿跨车间复用游标。"
        )

    def _norm(v: str | None) -> str | None:
        if not v:
            return None
        try:
            return datetime.fromisoformat(v).isoformat()
        except ValueError:
            return v

    want_s = range_start.isoformat() if range_start else None
    want_e = range_end.isoformat() if range_end else None
    got_s = _norm(cur.range_start)
    got_e = _norm(cur.range_end)

    if cur.range_start and want_s and got_s != want_s:
        return False, (
            "游标属于其它时间区间，本次请求的区间与其不一致。"
            "翻页时请保持 date/start/end 参数不变。"
        )
    if cur.range_end and want_e and got_e != want_e:
        return False, (
            "游标属于其它时间区间，本次请求的区间与其不一致。"
            "翻页时请保持 date/start/end 参数不变。"
        )

    return True, ""
