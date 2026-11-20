# -*- coding: utf-8 -*-
"""★ 车间隔离的对象级校验。

列表查询的车间过滤收口在 ``server.crud.scoping``；
本模块负责单条告警可见性检查与管理员权限校验。
"""

from __future__ import annotations

from fastapi import HTTPException, status

from server.auth.base import Principal


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
