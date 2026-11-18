# -*- coding: utf-8 -*-
"""API 调用方（甲方 IT 部门）与审计日志 CRUD。"""

from __future__ import annotations

import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models import ApiAuditLog, ApiClient


def hash_api_key(raw: str) -> str:
    """API Key 只存哈希，不存明文。"""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_api_key(prefix: str = "isup") -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


async def create_client(
    db: AsyncSession, *, name: str, scopes: str = "alarm:read,media:read"
) -> tuple[ApiClient, str]:
    """创建调用方并返回 (记录, 明文Key)。明文只在此刻返回一次。"""
    raw = generate_api_key()
    client = ApiClient(name=name, api_key_hash=hash_api_key(raw), scopes=scopes)
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client, raw


async def get_client_by_key(db: AsyncSession, raw_key: str) -> ApiClient | None:
    stmt = select(ApiClient).where(ApiClient.api_key_hash == hash_api_key(raw_key))
    client = (await db.execute(stmt)).scalar_one_or_none()
    if client is None or not client.enabled:
        return None
    return client


async def list_clients(db: AsyncSession) -> list[ApiClient]:
    stmt = select(ApiClient).order_by(ApiClient.id.asc())
    return list((await db.execute(stmt)).scalars().all())


def build_audit_row(
    *,
    principal_kind: str | None,
    subject: str | None,
    method: str,
    path: str,
    status_code: int,
    latency_ms: float,
    client_ip: str | None,
) -> ApiAuditLog:
    """★ 构造一条审计记录（**纯函数，不碰 db**）。

    为什么单独抽出来：审计行有 7 个字段，过去在
    middleware.AuditMiddleware 与 write_audit() 里各写了一遍 ——
    加字段时漏一处就是「有的请求记不全」。

    不在这里 commit：中间件是**攒批**落库的（一次事务写 N 条），
    逐条 commit 会把来之不易的批量写优化毁掉。
    """
    return ApiAuditLog(
        principal_kind=principal_kind,
        subject=subject,
        method=method,
        path=path,
        status_code=status_code,
        latency_ms=latency_ms,
        client_ip=client_ip,
    )


async def write_audit(
    db: AsyncSession,
    *,
    principal_kind: str | None,
    subject: str | None,
    method: str,
    path: str,
    status_code: int,
    latency_ms: float,
    client_ip: str | None,
) -> None:
    """单条写入（同步调用的简单场景）。

    ★ 高并发路径请用 build_audit_row() + 批量提交，
      否则每个请求多一次事务（见 middleware 的说明）。
    """
    db.add(
        build_audit_row(
            principal_kind=principal_kind,
            subject=subject,
            method=method,
            path=path,
            status_code=status_code,
            latency_ms=latency_ms,
            client_ip=client_ip,
        )
    )
    await db.commit()
