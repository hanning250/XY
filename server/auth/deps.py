# -*- coding: utf-8 -*-
"""鉴权依赖注入 —— 业务代码只依赖 require(scope)。"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from server.auth.apikey import ApiKeyProvider
from server.auth.base import Principal
from server.auth.jwt_auth import JwtProvider
from server.config import get_settings

_jwt = JwtProvider()
_apikey = ApiKeyProvider()
_open_api = ApiKeyProvider()


async def current_principal(request: Request) -> Principal:
    """内部 API 的当前身份。

    · jwt    : Authorization: Bearer <jwt>（含账号停用校验）
    · apikey : X-API-Key 头
    """
    settings = get_settings()
    mode = settings.auth_mode.lower()

    if mode == "apikey":
        principal = await _apikey.authenticate(request)
    else:
        # 默认 / 非法值一律按 jwt（不再支持 anonymous）
        if mode != "jwt":
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"不支持的鉴权模式: {mode!r}（仅支持 jwt / apikey）",
            )
        principal = await _jwt.authenticate(request)

    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    request.state.principal = principal
    return principal


async def open_api_principal(request: Request) -> Principal:
    """开放 API 的当前身份（甲方 IT 部门）—— 必须带有效 X-API-Key。"""
    principal = await _open_api.authenticate(request)
    if principal is not None:
        request.state.principal = principal
        return principal

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
