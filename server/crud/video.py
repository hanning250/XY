# -*- coding: utf-8 -*-
"""视频会话 CRUD。★ 会话是「用户点击」时才创建的，带 TTL。"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models import VideoSession, VideoStatus, utcnow


async def create_session(
    db: AsyncSession,
    *,
    alarm_id: str,
    provider: str,
    ttl_seconds: int,
    created_by: str | None = None,
) -> VideoSession:
    sess = VideoSession(
        id=str(uuid.uuid4()),
        alarm_id=alarm_id,
        status=VideoStatus.STARTING.value,
        provider=provider,
        created_by=created_by,
        expires_at=utcnow() + timedelta(seconds=ttl_seconds),
    )
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    return sess


async def get_session(db: AsyncSession, session_id: str) -> VideoSession | None:
    return await db.get(VideoSession, session_id)


async def find_live_session_for_alarm(
    db: AsyncSession, alarm_id: str
) -> VideoSession | None:
    """找该告警下仍然有效的会话（避免重复申请）。"""
    stmt = (
        select(VideoSession)
        .where(
            VideoSession.alarm_id == alarm_id,
            VideoSession.status.in_(
                [VideoStatus.STARTING.value, VideoStatus.READY.value]
            ),
        )
        .order_by(VideoSession.created_at.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def update_session(
    db: AsyncSession,
    sess: VideoSession,
    *,
    status: VideoStatus,
    url: str | None = None,
    handle: str | None = None,
    error: str | None = None,
) -> VideoSession:
    sess.status = status.value
    if url is not None:
        sess.url = url
    if handle is not None:
        sess.handle = handle
    if error is not None:
        sess.error = error
    await db.commit()
    await db.refresh(sess)
    return sess


async def delete_session(db: AsyncSession, sess: VideoSession) -> None:
    await db.delete(sess)
    await db.commit()


async def list_expired_sessions(db: AsyncSession, *, now: datetime | None = None) -> list[VideoSession]:
    """TTL 巡检：找出过期的会话，由 service 层释放资源。"""
    now = now or utcnow()
    stmt = select(VideoSession).where(
        VideoSession.expires_at.is_not(None), VideoSession.expires_at < now
    )
    return list((await db.execute(stmt)).scalars().all())
