# -*- coding: utf-8 -*-
"""API Key 鉴权 —— 甲方 IT 部门（开放 API）使用。"""

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
