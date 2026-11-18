# -*- coding: utf-8 -*-
"""★ 车间隔离的统一口径（唯一实现）。

为什么单独成一个模块：

过去「车间可见范围」这个事实散在 10 个函数里各写一遍：

    if workshops is not None:
        if not workshops:
            return <该函数自己的空值>      ← 10 个函数 10 种返回类型
        conds.append(Alarm.workshop.in_(workshops))

后果：
  ① 任何一处写漏 / 写反都是**串数据**（A 车间看到 B 车间）；
  ② 口径要改（比如「未指派车间归到默认车间」）得改 10 个地方；
  ③ 新人看不出 `None` / `[]` / `[...]` 三种语义的区别。

现在收敛到这里，其余地方一律 `conds = workshop_scope(Alarm, workshops)`
并配合 `is_denied(workshops)` 提前返回空值。
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import ColumnElement

__all__ = ["is_denied", "workshop_scope", "visible_in"]


def is_denied(workshops: Sequence[str] | None) -> bool:
    """★ 是否「默认拒绝」：传了车间列表、但列表是空的。

    三态语义（全项目统一，别再自己判断）：
      · None  → 不做车间过滤（admin / 开发模式 / 已上游校验）
      · []    → **什么都看不到**（账号没有分配任何车间）
      · [...] → 只看这些车间

    ★ [] 必须返回空集而不是「不过滤」—— 这是数据隔离的最后一道闸门。
      把空列表当「不过滤」是这一类漏洞最常见的成因。
    """
    return workshops is not None and len(workshops) == 0


def workshop_scope(
    model_column: ColumnElement,
    workshops: Sequence[str] | None,
) -> list[ColumnElement]:
    """车间过滤条件。返回可直接 `where(*conds)` 的列表。

    `workshops is None` 时不产生任何条件（不过滤）。
    传 [] 时应**先**用 is_denied() 短路返回空值，不要指望这里帮你兜底 ——
    因为「空集」的返回值各接口不同，只有调用方知道该返回什么。
    """
    if workshops is None:
        return []
    return [model_column.in_(list(workshops))]


def visible_in(item_workshop: str | None, workshops: Sequence[str] | None) -> bool:
    """对象级隔离：单条记录是否对当前可见范围可见。

    用在「已拿到对象、要判断能不能操作」的地方（改/删/标记处理）。
    与 workshop_scope() 的口径**必须一致**，否则会出现
    「列表里看得到、点进去 404」或更糟的「列表看不到、但能猜 ID 删掉」。
    """
    if workshops is None:
        return True
    return item_workshop in workshops
