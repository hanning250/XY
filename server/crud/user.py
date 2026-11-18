# -*- coding: utf-8 -*-
"""用户与车间权限 CRUD。"""

from __future__ import annotations

import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.tokens import hash_password, verify_password
from server.models import User, UserWorkshop

logger = logging.getLogger(__name__)


async def get_by_username(db: AsyncSession, username: str) -> User | None:
    stmt = select(User).where(User.username == username)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
    return await db.get(User, user_id)


async def authenticate(
    db: AsyncSession, *, username: str, password: str
) -> User | None:
    """校验用户名密码。失败返回 None（不区分用户不存在/密码错，避免枚举）。"""
    user = await get_by_username(db, username)
    if user is None or not user.enabled:
        # 仍然跑一次哈希，避免通过响应时间判断用户是否存在
        verify_password(password, "pbkdf2_sha256$1$00$00")
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def list_user_workshops(db: AsyncSession, user_id: int) -> list[str]:
    stmt = select(UserWorkshop.workshop_code).where(UserWorkshop.user_id == user_id)
    return [r[0] for r in (await db.execute(stmt)).all()]


async def set_user_workshops(
    db: AsyncSession, *, user_id: int, workshops: list[str]
) -> None:
    """覆盖式设置用户的车间权限。"""
    await db.execute(delete(UserWorkshop).where(UserWorkshop.user_id == user_id))
    for code in dict.fromkeys(workshops):  # 去重保序
        db.add(UserWorkshop(user_id=user_id, workshop_code=code))
    await db.commit()


async def create_user(
    db: AsyncSession,
    *,
    username: str,
    password: str,
    display_name: str = "",
    role: str = "viewer",
    superuser: bool = False,
    workshops: list[str] | None = None,
) -> User:
    user = User(
        username=username,
        password_hash=hash_password(password),
        display_name=display_name or username,
        role=role,
        is_superuser=superuser,
        enabled=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    if workshops:
        await set_user_workshops(db, user_id=user.id, workshops=workshops)
    return user


async def list_users(db: AsyncSession) -> list[User]:
    stmt = select(User).order_by(User.id.asc())
    return list((await db.execute(stmt)).scalars().all())


async def set_password(db: AsyncSession, *, user: User, password: str) -> None:
    """设置新密码。

    ★ 同时把 password_version +1（2026-XX）：该用户已签发的 JWT 里
      记着旧版本号，比对失败 → 旧 token 立即失效（改密即吊销）。
    """
    user.password_hash = hash_password(password)
    current = int(getattr(user, "password_version", 0) or 0)
    user.password_version = current + 1
    await db.commit()


async def set_enabled(db: AsyncSession, *, user: User, enabled: bool) -> None:
    user.enabled = enabled
    await db.commit()


async def ensure_admin(
    db: AsyncSession, *, username: str = "admin", password: str | None = None
):
    """确保存在一个可登录的 admin。

    · 已存在 → 不动（不覆盖现场改过的密码）
    · 不存在 → 用给定密码（或随机生成并返回）创建

    返回 (user, 明文密码 or None)。
    """
    import secrets

    user = await get_by_username(db, username)
    if user is not None:
        return user, None

    pwd = password or secrets.token_urlsafe(12)
    user = await create_user(
        db,
        username=username,
        password=pwd,
        display_name="系统管理员",
        role="admin",
        superuser=True,
        workshops=[],
    )
    return user, pwd
