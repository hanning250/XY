# -*- coding: utf-8 -*-
"""★ 视频会话服务 —— 「不点就不加载」的服务端实现（docs §3.3）。

核心原则：
  告警到达时，绝不创建任何视频会话、绝不触碰 SMS SDK、绝不占设备连接。
  只写一个 video_status='not_requested' 字段。
  用户点击「查看视频」时才 request。
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import timedelta

from server.config import get_settings
from server.crud import alarm as alarm_crud
from server.crud import video as video_crud
from server.db import SessionLocal
from server.models import Alarm, VideoSession, VideoStatus
from server.services.video_provider import VideoRequest, get_provider

logger = logging.getLogger(__name__)


class VideoService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._provider = get_provider()
        self._reaper: asyncio.Task | None = None
        self._running = False

    # ---------------------------------------------------------------- 生命周期
    async def start(self) -> None:
        self._running = True
        self._reaper = asyncio.create_task(self._reap_loop(), name="video-session-reaper")
        logger.info("视频服务已启动, provider=%s", self._provider.name)

    async def stop(self) -> None:
        self._running = False
        if self._reaper is not None:
            self._reaper.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reaper

    # ---------------------------------------------------------------- 申请
    async def create_session(
        self,
        alarm: Alarm,
        *,
        pre_seconds: int = 10,
        post_seconds: int = 30,
        force_refresh: bool = False,
        created_by: str | None = None,
    ) -> VideoSession:
        """用户点击「查看视频」→ 创建会话并请求 Provider。"""
        async with SessionLocal() as db:
            # ① 已缓存且不需要刷新 → 直接复用，秒开
            if alarm.video_status == VideoStatus.READY.value and alarm.video_url and not force_refresh:
                existing = await video_crud.find_live_session_for_alarm(db, alarm.id)
                if existing is not None and existing.url:
                    return existing
                sess = await video_crud.create_session(
                    db,
                    alarm_id=alarm.id,
                    provider=alarm.video_provider or self._provider.name,
                    ttl_seconds=self._settings.video_session_ttl_seconds,
                    created_by=created_by,
                )
                return await video_crud.update_session(
                    db, sess, status=VideoStatus.READY, url=alarm.video_url
                )

            # ② 已有进行中的会话 → 幂等返回，防止连点产生多个会话
            existing = await video_crud.find_live_session_for_alarm(db, alarm.id)
            if existing is not None and not force_refresh:
                return existing

            sess = await video_crud.create_session(
                db,
                alarm_id=alarm.id,
                provider=self._provider.name,
                ttl_seconds=self._settings.video_session_ttl_seconds,
                created_by=created_by,
            )

            # ③ 标记告警为 starting
            alarm_db = await alarm_crud.get_alarm(db, alarm.id)
            if alarm_db is None:
                return sess
            await alarm_crud.set_video_state(
                db, alarm_db, status=VideoStatus.STARTING, provider=self._provider.name
            )

        # ④ 向 Provider 申请（★ 唯一的对外依赖点）
        req = VideoRequest(
            alarm_id=alarm.id,
            device_id=alarm.device_id,
            channel=alarm.channel,
            start_time=alarm.alarm_time - timedelta(seconds=pre_seconds),
            end_time=alarm.alarm_time + timedelta(seconds=post_seconds),
        )
        try:
            handle = await self._provider.request(req)
        except Exception as exc:
            logger.exception("视频 Provider 申请失败")
            async with SessionLocal() as db:
                sess = await video_crud.get_session(db, sess.id)
                if sess is not None:
                    sess = await video_crud.update_session(
                        db, sess, status=VideoStatus.FAILED, error=str(exc)
                    )
                alarm_db = await alarm_crud.get_alarm(db, alarm.id)
                if alarm_db is not None:
                    await alarm_crud.set_video_state(
                        db, alarm_db, status=VideoStatus.FAILED
                    )
                return sess

        async with SessionLocal() as db:
            sess = await video_crud.get_session(db, sess.id)
            status = VideoStatus(handle.status) if handle.status in {
                s.value for s in VideoStatus
            } else VideoStatus.STARTING

            if sess is not None:
                sess = await video_crud.update_session(
                    db,
                    sess,
                    status=status,
                    url=handle.url,
                    handle=handle.handle,
                    error=handle.error,
                )

            alarm_db = await alarm_crud.get_alarm(db, alarm.id)
            if alarm_db is not None:
                await alarm_crud.set_video_state(
                    db,
                    alarm_db,
                    status=status,
                    url=handle.url,
                    duration=handle.duration,
                    provider=self._provider.name,
                )
            return sess

    # ---------------------------------------------------------------- 轮询
    async def poll_session(self, session_id: str) -> VideoSession | None:
        """前端轮询会话进度：starting → ready / failed。"""
        async with SessionLocal() as db:
            sess = await video_crud.get_session(db, session_id)
            if sess is None:
                return None
            if sess.status != VideoStatus.STARTING.value:
                return sess

            alarm = await alarm_crud.get_alarm(db, sess.alarm_id)
            if alarm is None:
                return sess

            from server.services.video_provider import VideoHandle

            handle = VideoHandle(
                ready=False,
                status=sess.status,
                url=sess.url,
                handle=sess.handle,
            )
            try:
                handle = await self._provider.poll(handle)
            except Exception as exc:
                logger.exception("轮询 Provider 失败")
                return await video_crud.update_session(
                    db, sess, status=VideoStatus.FAILED, error=str(exc)
                )

            status = VideoStatus(handle.status) if handle.status in {
                s.value for s in VideoStatus
            } else VideoStatus.STARTING

            sess = await video_crud.update_session(
                db, sess, status=status, url=handle.url, handle=handle.handle, error=handle.error
            )
            await alarm_crud.set_video_state(
                db,
                alarm,
                status=status,
                url=handle.url,
                duration=handle.duration,
                provider=self._provider.name,
            )
            return sess

    # ---------------------------------------------------------------- 释放
    async def close_session(self, session_id: str) -> bool:
        """前端关闭弹窗 → 主动释放。"""
        async with SessionLocal() as db:
            sess = await video_crud.get_session(db, session_id)
            if sess is None:
                return False
            await self._release(db, sess)
            return True

    async def _release(self, db, sess: VideoSession) -> None:
        from server.services.video_provider import VideoHandle

        with contextlib.suppress(Exception):
            await self._provider.release(
                VideoHandle(ready=True, url=sess.url, handle=sess.handle)
            )
        await video_crud.delete_session(db, sess)

    async def _reap_loop(self) -> None:
        """TTL 巡检：防止句柄/文件泄漏。"""
        while self._running:
            await asyncio.sleep(10)
            try:
                async with SessionLocal() as db:
                    expired = await video_crud.list_expired_sessions(db)
                    for sess in expired:
                        logger.info("视频会话 %s 已过期，回收", sess.id)
                        await self._release(db, sess)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("视频会话巡检失败")
