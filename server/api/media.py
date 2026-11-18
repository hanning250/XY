# -*- coding: utf-8 -*-
"""内部 API：媒体清理。

★ 用户指定时段来删除媒体文件：
    - POST /api/media/cleanup/preview  → 先看这个时段有多少告警/图片
    - POST /api/media/cleanup          → 执行删除（默认 dry_run=true，只预演）

★ 语义：只删文件，数据库记录保留并标记 media_expired。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.base import Principal
from server.auth.deps import require
from server.config import get_settings
from server.db import get_session
from server.schemas import MediaCleanupIn, MediaCleanupOut
from server.services import cleanup as cleanup_svc

router = APIRouter(prefix="/media", tags=["内部-媒体清理"])


@router.post(
    "/cleanup/preview",
    summary="★ 预演：统计指定时段有多少告警与图片（不删任何东西）",
)
async def preview_cleanup(
    payload: MediaCleanupIn,
    db: AsyncSession = Depends(get_session),
    _: Principal = Depends(require("media:write")),
):
    stats = await cleanup_svc.preview_media_range(
        db, start=payload.start, end=payload.end
    )
    return {"code": 0, "message": "ok", "data": stats}


@router.post(
    "/cleanup",
    response_model=MediaCleanupOut,
    summary="★ 按指定时段删除媒体文件（默认 dry_run 只预演）",
)
async def cleanup_media(
    payload: MediaCleanupIn,
    db: AsyncSession = Depends(get_session),
    _: Principal = Depends(require("media:write")),
):
    """删除 [start, end] 时段内的媒体文件。

    ★ 默认 dry_run=true —— 先预演看要删多少，确认后再传 false 真删。
    ★ 只删文件；对应告警保留并标记为 media_expired，前端显示占位。
    """
    res = await cleanup_svc.delete_media_in_range(
        db,
        start=payload.start,
        end=payload.end,
        categories=payload.categories,
        dry_run=payload.dry_run,
    )
    # ★ 2026-10-27：补语义明确的字段（dry_run 时是"会删多少"而非"已删"）
    res.setdefault("would_delete", res.get("deleted", 0))
    res.setdefault("would_keep", res.get("kept", 0))
    res.setdefault("would_free_bytes", res.get("bytes_freed", 0))
    res.setdefault(
        "action_taken", "preview" if res.get("dry_run") else "deleted"
    )
    return MediaCleanupOut(**res)


@router.get(
    "/cleanup/stats",
    summary="媒体占用概览（各目录文件数与体积）",
)
async def media_stats(_: Principal = Depends(require("media:read"))):
    from src.Common.CleanupExpiredFiles import RETENTION_RULES, _iter_files

    from server.config import PROJECT_ROOT

    settings = get_settings()
    out = []
    for dirname in RETENTION_RULES:
        d = PROJECT_ROOT / dirname
        count = 0
        size = 0
        if d.is_dir():
            for f in _iter_files(d):
                try:
                    count += 1
                    size += f.stat().st_size
                except OSError:
                    pass
        out.append(
            {
                "dir": dirname,
                "files": count,
                "bytes": size,
                "retention_days": (
                    settings.log_retention_days
                    if dirname == "IsupSDKLog"
                    else settings.media_retention_days
                ),
            }
        )
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "dirs": out,
            "media_retention_days": settings.media_retention_days,
            "log_retention_days": settings.log_retention_days,
        },
    }


@router.post(
    "/cleanup/retention",
    summary="按配置的保留天数清理（默认 30 天）",
)
async def cleanup_retention(
    dry_run: bool = Query(True, description="只预演不真删"),
    db: AsyncSession = Depends(get_session),
    _: Principal = Depends(require("media:write")),
):
    return await cleanup_svc.cleanup_by_retention(db, dry_run=dry_run)
