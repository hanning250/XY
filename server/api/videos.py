# -*- coding: utf-8 -*-
"""内部 API：视频会话。★ 「不点就不加载」的接口入口。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.base import Principal
from server.auth.deps import require
from server.auth.scoping import ensure_alarm_visible
from server.crud import alarm as alarm_crud
from server.db import get_session
from server.schemas import CreateVideoSessionIn, VideoSessionOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alarms", tags=["内部-视频"])


def _get_video_service(request: Request):
    svc = getattr(request.app.state, "video_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="视频服务未就绪")
    return svc


@router.post(
    "/{alarm_id}/video-session",
    response_model=VideoSessionOut,
    summary="★ 用户点击「查看视频」时才调用",
)
async def create_video_session(
    alarm_id: str,
    payload: CreateVideoSessionIn | None = None,
    request: Request = None,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require("video:read")),
):
    """告警到达时**不会**创建会话；只有用户点击此接口才拉起同事的解码服务。"""
    payload = payload or CreateVideoSessionIn()

    alarm = await alarm_crud.get_alarm(db, alarm_id)
    if alarm is None:
        raise HTTPException(status_code=404, detail="告警不存在")
    # ★ 对象级隔离（2026-XX 安全审查修复）
    ensure_alarm_visible(alarm, principal)

    svc = _get_video_service(request)
    sess = await svc.create_session(
        alarm,
        pre_seconds=payload.pre_seconds,
        post_seconds=payload.post_seconds,
        force_refresh=payload.force_refresh,
        created_by=principal.subject,
    )
    return VideoSessionOut.model_validate(sess)


@router.post(
    "/{alarm_id}/playback",
    summary="★ 从设备抓取该告警时段的真实录像（PS→MP4 转码）",
)
async def request_playback(
    alarm_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require("video:read")),
):
    """向 SMS SDK 申请按时间回放，抓取告警时刻前 1 分钟的录像。

    与 video-session 的区别：
      · video-session 走 VideoProvider（mock/file/http），是「取视频」的抽象接口
      · playback 是**直连设备**抓真实录像，目前唯一能拿到真实画面的路径

    ★ 立即返回，抓取在后台线程进行；前端通过 WebSocket 或轮询拿最终状态。
    """
    alarm = await alarm_crud.get_alarm(db, alarm_id)
    if alarm is None:
        raise HTTPException(status_code=404, detail="告警不存在")
    # ★ 对象级隔离：B 车间账号不能对 A 车间的告警发起回放/建会话
    #   （2026-XX 安全审查修复，与 alarms API 的口径对齐）
    ensure_alarm_visible(alarm, principal)

    if getattr(alarm, "media_expired", False):
        raise HTTPException(status_code=409, detail="该告警的媒体已过期，无法抓取回放")

    svc = getattr(request.app.state, "playback_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="回放服务未就绪")

    ok = svc.submit(alarm_id)
    if not ok:
        # 可能是未注入 SMS，也可能是队列积压被硬上限拒绝
        if getattr(svc, "_sms", None) is None:
            raise HTTPException(
                status_code=503,
                detail="回放服务未注入 SMS（ISUP SDK 未启动），无法抓取设备录像",
            )
        raise HTTPException(
            status_code=429,
            detail="回放队列积压已满（设备回放为独占资源，串行处理），请稍后重试",
        )

    # ★ 立刻把状态置为 starting 并落库（2026-XX）：
    #   用户点完马上能在界面上看到「抓取中…」，而不是等 worker 开跑
    #   （队列有积压时可能等几十秒，界面看起来像"点了没反应"）。
    from server.services import playback_registry

    playback_registry.set_playback_starting(alarm_id)

    logger.info("告警 %s 已提交回放抓取（by %s）", alarm_id, principal.subject)
    return {
        "code": 0,
        "message": "已开始抓取",
        "data": {
            "id": alarm_id,
            "video_status": "starting",
            "video_url": None,
        },
    }


@router.get(
    "/video-sessions/{session_id}",
    response_model=VideoSessionOut,
    summary="轮询会话进度 starting → ready / failed",
)
async def poll_video_session(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require("video:read")),
):
    svc = _get_video_service(request)
    sess = await svc.poll_session(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    # ★ 会话也可能被越权枚举：校验其归属告警对当前身份可见
    alarm = await alarm_crud.get_alarm(db, sess.alarm_id)
    if alarm is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    ensure_alarm_visible(alarm, principal)
    return VideoSessionOut.model_validate(sess)


@router.delete(
    "/video-sessions/{session_id}",
    summary="关闭弹窗时释放会话",
)
async def close_video_session(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require("video:read")),
):
    svc = _get_video_service(request)
    sess = await svc.poll_session(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    alarm = await alarm_crud.get_alarm(db, sess.alarm_id)
    if alarm is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    ensure_alarm_visible(alarm, principal)
    ok = await svc.close_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"code": 0, "message": "已释放"}
