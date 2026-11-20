# -*- coding: utf-8 -*-
"""媒体清理服务。

职责：
  · 按保留天数自动清理（启动 / 定时）
  · 按用户指定时段删除（HTTP 接口）

★ 核心语义（用户确认）：
    "只删文件，数据库标记为已过期"
  —— 文件从磁盘移除，Alarm 记录保留并置 media_expired=True，
     前端详情页显示占位而不是裂图，历史告警仍可检索。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from server.config import (
    PROJECT_ROOT,
    get_settings,
    resolve_image_retention_days,
    resolve_video_retention_days,
)
from server.crud import alarm as alarm_crud
from server.models import Alarm, AlarmStatus, VideoStatus

logger = logging.getLogger(__name__)

# 接口用的目录名 -> 清理模块用的目录名
_CATEGORY_MAP = {
    "storage": "storage",
    "outputfiles": "outputFiles",
    "outputFiles": "outputFiles",
    "media-video": "media/video",
    "media/video": "media/video",
    "media_video": "media/video",
    "isupsdklog": "IsupSDKLog",
    "IsupSDKLog": "IsupSDKLog",
}


def _norm_categories(categories: list[str] | None) -> set[str] | None:
    if not categories:
        return None
    out: set[str] = set()
    for c in categories:
        key = _CATEGORY_MAP.get(c) or _CATEGORY_MAP.get(c.lower())
        if key:
            out.add(key)
    return out or None


# ---------------------------------------------------------------------------
# 按时间区间删除
# ---------------------------------------------------------------------------
async def delete_media_in_range(
    db: AsyncSession,
    *,
    start: datetime,
    end: datetime,
    categories: list[str] | None = None,
    dry_run: bool = True,
) -> dict:
    """删除指定时段的媒体文件，并把受影响的告警标记为媒体已过期。

    dry_run=True 时只统计、不删文件、不改数据库。
    """
    from src.Common.CleanupExpiredFiles import delete_media_in_range as _delete_files

    # 统一成 naive（数据库里存的是 naive UTC）
    s = _as_naive(start)
    e = _as_naive(end)
    if e < s:
        s, e = e, s

    cats = _norm_categories(categories)

    # 1) 找出时间区间内、且还有媒体的告警（用于标记过期）
    stmt = select(Alarm).where(
        Alarm.alarm_time >= s,
        Alarm.alarm_time <= e,
        Alarm.media_expired.is_(False),
    )
    alarms = list((await db.execute(stmt)).scalars().all())

    # 2) 真正删文件（清理模块按 mtime 比对；mtime 是本地时间，这里用同样口径）
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: _delete_files(
            _as_local(s),
            _as_local(e),
            categories=cats,
            dry_run=dry_run,
            project_root=str(PROJECT_ROOT),
        ),
    )

    marked = 0
    if not dry_run and alarms:
        # 3) 标记这些告警为媒体已过期
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.execute(
            update(Alarm)
            .where(Alarm.id.in_([a.id for a in alarms]))
            .values(
                media_expired=True,
                media_expired_at=now,
                status=AlarmStatus.MEDIA_EXPIRED.value,
                video_status=VideoStatus.UNAVAILABLE.value,
                video_url=None,
            )
        )
        # 4) 清掉图片记录指向的文件已不存在 —— 保留行但前端靠 media_expired 判断
        await db.commit()
        marked = len(alarms)

    return {
        "deleted": result.deleted,
        "kept": result.kept,
        "bytes_freed": result.bytes_freed,
        "dry_run": dry_run,
        "alarms_marked": marked,
        "errors": [f"{p}: {msg}" for p, msg in result.errors],
        "files": result.details[:200],  # 防止响应体过大
    }


def _as_naive(dt: datetime) -> datetime:
    """转成 naive datetime（数据库存的是 naive UTC）。"""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _as_local(dt: datetime) -> datetime:
    """转成本地时区的 naive datetime，用于和文件 mtime 比对。"""
    if dt.tzinfo is None:
        # 接口传来的无时区时间按本地时间理解
        return dt
    from server.services.timeutil import to_local_naive

    return to_local_naive(dt) or dt.replace(tzinfo=None)


# ---------------------------------------------------------------------------
# 按保留天数清理
# ---------------------------------------------------------------------------
async def cleanup_by_retention(db: AsyncSession, *, dry_run: bool = False) -> dict:
    """按配置的保留天数清理，并把过期告警标记出来。

    ⚠️ 2026-10-22 重写（现场启动日志每次报错的真因）：

        原顺序是「先删磁盘文件 → 再写库标记过期」。实测在 Windows + SQLite
        WAL 下，删完几十个文件后紧接的 `UPDATE` 会抛：

            sqlite3.OperationalError: unable to open database file

        重试 5 次（累计 7.5 秒）仍失败 —— 不是锁竞争，是那个时刻库的写句柄
        已不可用。后果比报错本身严重：**文件删了、标记没写**，
        `media_expired` 永远为 0，前端按"文件应该存在"去请求 → 大面积裂图，
        而不是我们承诺的"媒体已过期"占位。

    ★ 新顺序（先标记、后删文件）：
        ① 先算出「超期且尚未标记」的告警，**先写库**标记 media_expired
        ② 再跑文件清理（此时数据库已是正确状态）
        ③ 即使 ② 失败，前端也只会看到"已过期"占位，不会裂图

    代价：先标记会让「文件还没删、但已标为过期」的窗口存在几秒。
        这是**安全方向**的偏差（显示过期 > 显示裂图），可以接受。
    """
    from src.Common.CleanupExpiredFiles import cleanup_expired_files as _cleanup

    settings = get_settings()
    # ★★ 2026-10-29：图片与视频分开保留（甲方要求）
    #     · 视频：3 / 7 / 30 天（按套餐，磁盘大头）
    #     · 图片：固定 30 天（体积小，多留没压力）
    video_days = resolve_video_retention_days()
    image_days = resolve_image_retention_days()
    # 「整体过期」的判定用**较长**的那个 —— 图片和视频都没了才算媒体过期。
    # 否则视频先到期（3 天）时会把整条告警标成 media_expired，
    # 连带图片也被前端当成"已过期"不显示，而甲方要求图片留 30 天。
    days = max(video_days, image_days)

    # ---- ① 先写过期标记（在动磁盘之前，库是健康的）----
    marked = 0
    if not dry_run:
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc).replace(tzinfo=None)
        cutoff = cutoff.replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff = cutoff - timedelta(days=days)

        stmt = select(Alarm.id).where(
            Alarm.alarm_time < cutoff, Alarm.media_expired.is_(False)
        )
        ids = [r[0] for r in (await db.execute(stmt)).all()]
        if ids:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.execute(
                update(Alarm)
                .where(Alarm.id.in_(ids))
                .values(
                    media_expired=True,
                    media_expired_at=now,
                    status=AlarmStatus.MEDIA_EXPIRED.value,
                    video_status=VideoStatus.UNAVAILABLE.value,
                    video_url=None,
                )
            )
            await db.commit()
            marked = len(ids)
        # ★ 提交后释放连接，避免下面长耗时文件操作期间占着池
        await db.close()

    # ---- ② 再删磁盘文件（长耗时，放线程池）----
    # ★ 图片与视频用各自的保留天数（见上）
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: _cleanup(
            project_root=str(PROJECT_ROOT),
            rules={
                "outputFiles": video_days,     # SDK 原始落盘，跟视频同寿命
                "storage": image_days,         # ★ 图片：固定 30 天
                "media/video": video_days,     # ★ 视频：3/7/30 天
                "IsupSDKLog": settings.log_retention_days,
            },
            dry_run=dry_run,
            verbose=False,
        ),
    )

    # ★ 告警**记录**保留期清理（与媒体清理分开配置）
    #   背景：box001 轮询抓拍每 6 秒重复上报，关去重后每天约 1.4 万条，
    #   不清理会撑爆数据库。
    purged = 0
    files_removed = 0
    if settings.alarm_retention_days > 0:
        if dry_run:
            # 预演：只统计有多少条会超期（不写库，用调用方 session 无妨）
            col = (
                Alarm.created_at
                if settings.alarm_retention_by == "created_at"
                else Alarm.alarm_time
            )
            from datetime import timedelta as _td

            cutoff2 = datetime.now(timezone.utc).replace(tzinfo=None) - _td(
                days=settings.alarm_retention_days
            )
            cnt_stmt = select(func.count(Alarm.id)).where(col < cutoff2)
            purged = int((await db.execute(cnt_stmt)).scalar() or 0)
        else:
            # ★ 这里也要用新 session（原因同上：文件清理可能已跑很久）
            from server.db import SessionLocal

            async with SessionLocal() as fresh:
                total, paths_by_alarm = await alarm_crud.purge_old_alarms(
                    fresh,
                    retention_days=settings.alarm_retention_days,
                    by=settings.alarm_retention_by,
                )
            purged = total
            if paths_by_alarm:
                from server.services import playback_registry

                for aid, paths in paths_by_alarm.items():
                    r, _ = playback_registry.delete_alarm_files(aid, file_paths=paths)
                    files_removed += r

    # ★ 审计日志保留期清理（2026-XX 新增：api_audit_log 原先只增不删）
    audit_purged = 0
    audit_days = settings.audit_retention_days
    if audit_days > 0:
        from datetime import timedelta as _td

        audit_cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - _td(
            days=audit_days
        )
        from server.models import ApiAuditLog

        from server.db import SessionLocal

        async with SessionLocal() as fresh:
            res = await fresh.execute(
                delete(ApiAuditLog).where(ApiAuditLog.created_at < audit_cutoff)
            )
            await fresh.commit()
            audit_purged = int(res.rowcount or 0)

    return {
        "deleted": result.deleted,
        "kept": result.kept,
        "skipped_in_use": result.skipped_in_use,
        "bytes_freed": result.bytes_freed,
        "alarms_marked": marked,
        "alarms_purged": purged,
        "alarm_files_removed": files_removed,
        "audit_purged": audit_purged,
        "dry_run": dry_run,
    }


# ---------------------------------------------------------------------------
# 清理结果预览（给前端确认用）
# ---------------------------------------------------------------------------
async def preview_media_range(
    db: AsyncSession, *, start: datetime, end: datetime
) -> dict:
    """统计指定时段内各目录的媒体文件数量与体积，供前端确认后再删。"""
    s = _as_naive(start)
    e = _as_naive(end)
    if e < s:
        s, e = e, s

    stmt = select(Alarm).where(Alarm.alarm_time >= s, Alarm.alarm_time <= e)
    alarms = list((await db.execute(stmt)).scalars().all())

    total_images = 0
    total_bytes = 0
    for a in alarms:
        for img in a.images:
            total_images += 1
            if img.file_size:
                total_bytes += img.file_size

    return {
        "start": s,
        "end": e,
        "alarm_count": len(alarms),
        "image_count": total_images,
        "image_bytes": total_bytes,
    }
