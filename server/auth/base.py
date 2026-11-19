# -*- coding: utf-8 -*-
"""Principal 抽象与鉴权 Provider 协议。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from fastapi import Request

from server.models import PrincipalKind

# 全部权限集合。将来细分角色时按需裁剪。
ALL_SCOPES: set[str] = {
    "alarm:read",
    "alarm:write",
    "media:read",
    "media:write",
    "video:read",
    "device:read",
    "admin",
}

# ★ 普通账号的只读权限集（车间子账号 / 巡检员）。
READONLY_SCOPES: set[str] = {
    "alarm:read",
    "media:read",
    "video:read",
    "device:read",
}


def scopes_for_role(*, superuser: bool) -> set[str]:
    """按角色返回该授予的权限集。

    · superuser（admin） → 全部权限
    · 普通账号          → 只读权限
    """
    return set(ALL_SCOPES) if superuser else set(READONLY_SCOPES)


@dataclass(slots=True)
class Principal:
    """统一的调用者身份。

    前端用户 / 开放 API 调用方，全部归一到这一个模型。

    ★ 车间隔离相关字段：
        tenants    —— 该身份可访问的车间列表（admin 为空，但 superuser=True）
        superuser  —— True 表示可访问全部车间
        tenant     —— 保留为「主车间」，兼容既有代码

    隔离判定统一走 `visible_workshops()`，业务代码不要自己拼条件。
    """

    kind: str = PrincipalKind.USER.value
    subject: str = ""
    # ★★ 安全默认：空集，必须显式授予。
    scopes: set[str] = field(default_factory=set)
    tenant: str | None = None
    tenants: list[str] = field(default_factory=list)
    superuser: bool = False
    user_id: int | None = None

    def has(self, scope: str) -> bool:
        return "admin" in self.scopes or scope in self.scopes

    def visible_workshops(self) -> list[str] | None:
        """返回该身份可见的车间列表。

        · None      → 可看**全部**（admin / superuser）
        · []        → **什么都看不到**（默认拒绝）
        · ["A","B"] → 只看这两个车间
        """
        if self.superuser:
            return None
        if self.tenants:
            return list(self.tenants)
        if self.tenant:
            return [self.tenant]
        return []


class AuthProvider(Protocol):
    """鉴权提供者协议。"""

    name: str

    async def authenticate(self, request: Request) -> Principal | None:
        """返回 Principal，或 None 表示认证失败。"""
        ...
