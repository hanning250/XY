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

# ★ 2026-10-27：普通账号的只读权限集。
#   给车间子账号/巡检员用的默认权限：能看不能改。
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

    ★ 将来要细分角色（如"只能看某车间"、"能导出"），在这里加分支。
    """
    return set(ALL_SCOPES) if superuser else set(READONLY_SCOPES)



@dataclass(slots=True)
class Principal:
    """统一的调用者身份。

    前端用户 / 开放 API 调用方 / 匿名请求，全部归一到这一个模型。

    ★ 车间隔离相关字段：
        tenants    —— 该身份可访问的车间列表（admin 为空，但 superuser=True）
        superuser  —— True 表示可访问全部车间
        tenant     —— 保留为「主车间」，兼容既有代码

    隔离判定统一走 `visible_workshops()`，业务代码不要自己拼条件。
    """

    kind: str = PrincipalKind.ANONYMOUS.value
    subject: str = "anonymous"
    # ★★ 2026-10-27 安全修复：默认**空集**（安全默认）。
    #
    #   原来默认是 ALL_SCOPES，导致任何未显式传 scopes 的 Principal
    #   （包括登录签发的 token）都拿到全部权限，含 admin。
    #   越权拦截实际只靠 superuser 标记，scope 机制形同虚设。
    #
    #   现在必须显式授予；登录/API Key 两条路径都按角色裁剪。
    scopes: set[str] = field(default_factory=set)
    # 主车间（兼容旧代码；新代码用 tenants）
    tenant: str | None = None
    # ★ 可访问的车间列表
    tenants: list[str] = field(default_factory=list)
    # ★ 跨车间账号（admin）
    superuser: bool = False
    user_id: int | None = None

    def has(self, scope: str) -> bool:
        return "admin" in self.scopes or scope in self.scopes

    def visible_workshops(self) -> list[str] | None:
        """返回该身份可见的车间列表。

        · None      → 可看**全部**（admin / 匿名开发模式）
        · []        → **什么都看不到**（默认拒绝）
        · ["A","B"] → 只看这两个车间
        """
        if self.superuser:
            return None
        if self.tenants:
            return list(self.tenants)
        if self.tenant:
            return [self.tenant]
        # 匿名开发模式（auth_mode=anonymous）沿用旧行为：看全部，
        # 便于未启登录时前端先跑通；一旦切 jwt，普通账号即受限于 tenants。
        if self.kind == PrincipalKind.ANONYMOUS.value:
            return None
        return []


class AuthProvider(Protocol):
    """鉴权提供者协议。"""

    name: str

    async def authenticate(self, request: Request) -> Principal | None:
        """返回 Principal，或 None 表示认证失败。"""
        ...


class AnonymousProvider:
    """开发期 / 内网初期：全部放行，但**仍然走完整的 Principal 流程**。

    这样前端的调用方式、后端的依赖注入签名，从第一天就是最终形态。
    """

    name = "anonymous"

    async def authenticate(self, request: Request) -> Principal | None:
        return Principal(
            kind=PrincipalKind.ANONYMOUS.value,
            subject="anonymous",
            scopes=set(ALL_SCOPES),
        )
