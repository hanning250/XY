# -*- coding: utf-8 -*-
"""鉴权依赖注入 —— 业务代码只依赖 require(scope)。"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from server.auth.apikey import ApiKeyOrAnonymousProvider, ApiKeyProvider
from server.auth.base import AnonymousProvider, Principal
from server.auth.jwt_auth import JwtProvider
from server.config import get_settings

_anonymous = AnonymousProvider()
_jwt = JwtProvider()
# ★ 内部 API 的 Key 校验器（auth_mode=apikey 时使用，2026-XX 安全审查修复）
_apikey = ApiKeyProvider()
_open_api = ApiKeyOrAnonymousProvider(
    require_key=get_settings().open_api_requires_key
)


async def current_principal(request: Request) -> Principal:
    """内部 API 的当前身份。

    · jwt     : Authorization: Bearer <jwt>（含账号停用校验）
    · apikey  : X-API-Key 头（★ 修复：原来这里错用了 anonymous，导致
                apikey 模式下整站匿名放行 —— 复制粘贴错误）
    · anonymous: 全放行（仅开发期）
    """
    settings = get_settings()
    mode = settings.auth_mode.lower()

    if mode == "jwt":
        principal = await _jwt.authenticate(request)
    elif mode == "apikey":
        principal = await _apikey.authenticate(request)
    else:
        principal = await _anonymous.authenticate(request)

    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 供审计中间件复用，避免重复解析
    request.state.principal = principal
    return principal


async def open_api_principal(request: Request) -> Principal:
    """开放 API 的当前身份（甲方 IT 部门）。

    ## ★ 2026-10-27 修正：尊重 ISUP_OPEN_API_REQUIRES_KEY 开关

    现场要求「给甲方的接口不需要鉴权」—— 内网调用，加 Key 反而增加
    对接复杂度，对方明确拒绝。

    但原来这个函数**无条件**要求 Key：即使 `ApiKeyOrAnonymousProvider`
    在 require_key=False 时已经愿意返回匿名身份，这里也只判断 `is None`
    就抛 401 —— 开关形同虚设。

    现在的行为：
      · 开关关闭（默认）→ 无 Key 时降级为匿名 Principal，带只读 scope
      · 开关打开         → 必须带有效 Key，否则 401
    """
    principal = await _open_api.authenticate(request)
    if principal is not None:
        request.state.principal = principal
        return principal

    if not get_settings().open_api_requires_key:
        # 开关关闭：匿名放行，但只给只读权限
        from server.auth.base import READONLY_SCOPES, PrincipalKind

        anon = Principal(
            kind=PrincipalKind.ANONYMOUS.value,
            subject="anonymous",
            scopes=set(READONLY_SCOPES),
        )
        request.state.principal = anon
        return anon

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="缺少或无效的 X-API-Key",
    )


def require(scope: str):
    """生成一个校验 scope 的依赖。

    用法：`async def ep(p: Principal = Depends(require("alarm:read")))`
    """

    async def _dep(principal: Principal = Depends(current_principal)) -> Principal:
        if not principal.has(scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限: {scope}",
            )
        return principal

    return _dep


def require_open(scope: str = "alarm:read"):
    """开放 API 的 scope 校验依赖。"""

    async def _dep(principal: Principal = Depends(open_api_principal)) -> Principal:
        if not principal.has(scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限: {scope}",
            )
        return principal

    return _dep
