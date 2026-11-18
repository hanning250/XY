# -*- coding: utf-8 -*-
"""API Key 鉴权 —— 甲方 IT 部门（开放 API）现在就用的方案。"""

from __future__ import annotations

from fastapi import Request

from server.auth.base import Principal
from server.crud.security import get_client_by_key
from server.db import SessionLocal
from server.models import PrincipalKind

API_KEY_HEADER = "X-API-Key"


class ApiKeyProvider:
    name = "apikey"

    async def authenticate(self, request: Request) -> Principal | None:
        raw = request.headers.get(API_KEY_HEADER, "").strip()
        if not raw:
            return None

        async with SessionLocal() as db:
            client = await get_client_by_key(db, raw)
            if client is None:
                return None
            scopes = {
                s.strip() for s in (client.scopes or "").split(",") if s.strip()
            }
            return Principal(
                kind=PrincipalKind.API_KEY.value,
                subject=client.name,
                scopes=scopes,
            )


class ApiKeyOrAnonymousProvider:
    """开放 API 的鉴权策略：

      · 配置了 open_api_requires_key=True → 必须带有效 Key
      · 否则（默认，开发期）→ 无 Key 时降级为匿名，方便前端和联调
                               但有 Key 时仍然识别身份并记录审计
    """

    name = "apikey_or_anonymous"

    def __init__(self, require_key: bool) -> None:
        self._require_key = require_key
        self._apikey = ApiKeyProvider()

    async def authenticate(self, request: Request) -> Principal | None:
        principal = await self._apikey.authenticate(request)
        if principal is not None:
            return principal
        if self._require_key:
            return None
        # ★ 2026-10-27：匿名降级时必须给**只读 scope**。
        #
        #   原来返回的 Principal scopes 是空集（base.py 的安全默认），
        #   下游 `require_open("alarm:read")` 一检查就 403 ——
        #   于是「不需要鉴权」的接口实际上谁都访问不了。
        #
        #   语义应当是：匿名可以**读**，但没有任何写权限。
        from server.auth.base import READONLY_SCOPES

        return Principal(
            kind=PrincipalKind.ANONYMOUS.value,
            subject="anonymous",
            scopes=set(READONLY_SCOPES),
        )
