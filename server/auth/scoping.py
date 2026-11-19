# -*- coding: utf-8 -*-
"""★ 车间隔离的统一收口 —— 所有查询必须过这里。

设计原则（最重要的一条）：**默认拒绝**

    如果每个接口自己拼 `WHERE workshop = ?`，只要有一个接口忘了加，
    B 车间就能看到 A 车间的数据。而且这种 bug **不报错、不报异常**，
    直到出事才会发现。

    所以这里把过滤收口成一个函数：忘了调用 → 抛 403，
    而不是「忘了加过滤 → 泄露全部数据」。

    ✅ 正确：stmt = scoped_workshops(stmt, Alarm, principal, db)
    ❌ 错误：stmt = stmt.where(Alarm.workshop == principal.tenant)

用法：
    from server.auth.scoping import scoped_workshops

    stmt = select(Alarm)
    stmt = scoped_workshops(stmt, Alarm, principal, db)
    # 之后可以继续 .where(...) 与分页
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.sql import Select
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.base import Principal


async def resolve_visible_workshops(
    principal: Principal, db: AsyncSession
) -> list[str] | None:
    """确定该身份可见的车间列表。

    返回 None 表示「全部可见」（superuser）。
    返回 [] 表示「什么都看不到」—— 这是**默认拒绝**的落点。
    """
    visible = principal.visible_workshops()
    if visible is not None:
        return visible

    # None = 全部可见，仅 superuser
    if principal.superuser:
        return None

    # 普通已登录账号，但 token 里没有车间 → 默认拒绝
    return []


async def scoped_workshops(
    stmt: Select,
    model,
    principal: Principal,
    db: AsyncSession,
) -> Select:
    """给查询加上车间过滤。

    ★ 这是隔离的唯一入口。任何返回告警/媒体数据的查询都必须过这里。
    """
    visible = await resolve_visible_workshops(principal, db)

    if visible is None:
        return stmt

    if not visible:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前账号未分配任何车间，无法查看数据。请联系管理员分配。",
        )

    return stmt.where(model.workshop.in_(visible))


def ensure_alarm_visible(alarm, principal: Principal) -> None:
    """对象级校验：确认这条告警对该身份可见。"""
    visible = principal.visible_workshops()
    if visible is None:
        return  # superuser

    if not visible:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前账号未分配任何车间",
        )

    if getattr(alarm, "workshop", None) not in visible:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="告警不存在",
        )


def require_superuser(principal: Principal) -> None:
    """要求跨车间权限（管理类操作：车间/通道/账号管理）。"""
    if not principal.superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
