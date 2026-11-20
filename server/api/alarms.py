# -*- coding: utf-8 -*-
"""内部 API：告警（前端看板用）。"""

from __future__ import annotations

import contextlib
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.base import Principal
from server.auth.deps import require
from server.auth.scoping import ensure_alarm_visible
from server.crud import alarm as alarm_crud
from server.crud.filters import AlarmFilter
from server.db import get_session
from server.schemas import (
    AlarmBrief,
    AlarmOut,
    AlarmStatsOut,
    BatchDeleteIn,
    BatchHandledIn,
    DashboardOut,
    DataQualityOut,
    HandleIn,
    HotspotPoint,
    HourlyPoint,
    PagedData,
    TrendPoint,
    WorkshopStat,
)
from server.services import playback_registry
from server.services.serialize import alarm_brief, alarm_out

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alarms", tags=["内部-告警"])


@router.get("/stats", response_model=AlarmStatsOut, summary="★ 看板统计（今日/待处理/已处理）")
async def alarm_stats(
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require("alarm:read")),
):
    """前端顶部三张卡片 + 左侧红点（红点 = pending）。

    ★ 按车间隔离：只统计当前账号可见车间的数据。
    """
    data = await alarm_crud.count_stats(db, workshops=principal.visible_workshops())
    return AlarmStatsOut(**data)


@router.get("/rule-names", summary="报警类型（规则名）下拉选项")
async def list_rule_names(
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require("alarm:read")),
):
    names = await alarm_crud.list_rule_names(
        db, workshops=principal.visible_workshops()
    )
    return {"items": names}


@router.get("", response_model=PagedData[AlarmBrief], summary="告警分页列表")
async def list_alarms(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    device_id: str | None = None,
    channel: int | None = None,
    alarm_type: int | None = None,
    workshop: str | None = Query(None, description="区域/车间 code"),
    rule_name: str | None = Query(None, description="报警类型（规则名）"),
    start: datetime | None = None,
    end: datetime | None = None,
    status: str | None = None,
    handled: bool | None = Query(None, description="true=只看已处理，false=只看未处理"),
    has_image: bool | None = Query(
        None, description="true=只看有抓拍图的告警（前端值守默认），false=只看无图告警"
    ),
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require("alarm:read")),
):
    """★ 按车间隔离：只返回当前账号可见车间的告警。"""
    rows, total = await alarm_crud.list_alarms_offset(
        db,
        AlarmFilter(
            device_id=device_id,
            channel=channel,
            alarm_type=alarm_type,
            start=start,
            end=end,
            status=status,
            handled=handled,
            has_image=has_image,
            workshops=principal.visible_workshops(),
            workshop=workshop,
            rule_name=rule_name,
        ),
        page=page,
        size=size,
    )
    # ★ 车间 code → 名字（列表里显示「1号车间」而不是裸 code）
    #   ★★ 2026-10-29：改用带 TTL 缓存的统一解析，
    #   保证「列表接口」与「WebSocket 推送」用的是同一份映射 ——
    #   否则两边命名不一致就会造成界面一会儿编码一会儿名称。
    from server.services import workshop_service as _ws_svc

    ws_names = await _ws_svc.workshop_name_map(db)

    briefs = []
    for a in rows:
        b = alarm_brief(a)
        if b.workshop:
            b.workshop_name = ws_names.get(b.workshop, b.workshop)
        briefs.append(b)

    return PagedData(
        items=briefs,
        has_more=page * size < total,
        # ★ 带上真实总数（前端「共 N 条」与分页器用它，替代原来的页码估算）
        total=total,
    )


@router.get(
    "/dashboard",
    response_model=DashboardOut,
    summary="★ 首页看板聚合数据",
    # ★ 必须声明在 /{alarm_id} 之前，否则 "dashboard" 会被当成告警 ID
)
async def dashboard(
    days: int = Query(7, ge=1, le=30, description="趋势图天数"),
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require("alarm:read")),
):
    """首页看板一次请求拿全：今日/昨日对比、待处理、已处理、
    最近 N 天每日趋势（含已处理数）、设备在线统计。

    ★ 全部按当前账号可见车间隔离（workshop 子账号只看到本车间）。
    """
    from datetime import timedelta

    from server.crud.device import count_devices
    from server.services import timeutil

    visible = principal.visible_workshops()
    now = timeutil.now_local()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yest_start = today_start - timedelta(days=1)
    trend_start = today_start - timedelta(days=days - 1)

    # ---- 统计卡片（复用 count_stats：today/pending/handled）----
    stats = await alarm_crud.count_stats(db, today_start=today_start, workshops=visible)

    # ---- 昨日 ----
    yest_rows = await alarm_crud.count_daily_trend(
        db, start=yest_start, end=today_start, workshops=visible
    )
    yesterday = yest_rows[0]["count"] if yest_rows else 0

    # ---- 每日趋势（今天往前 days 天，含今天）----
    trend = await alarm_crud.count_daily_trend(
        db, start=trend_start, end=today_start + timedelta(days=1), workshops=visible
    )

    # ---- 设备在线（按车间隔离）----
    online, total = await count_devices(db, workshops=visible)

    # ---- ★ 车间分布（今日 / 待处理 + 通道在线）----
    ws_stats = await alarm_crud.count_workshop_stats(db, workshops=visible)

    # ---- ★ 今日 24 小时分布 ----
    hourly = await alarm_crud.count_hourly_today(
        db, today_start=today_start, workshops=visible
    )

    # ---- ★ 处置时效（今日已处理的平均时长）----
    latency = await alarm_crud.count_handle_latency(db, workshops=visible)

    # ---- ★ 图片配对队列健康度 ----
    pending_health = await alarm_crud.count_pending_health(db)

    # ---- ★ 未指派车间的告警数（提醒去分配通道）----
    unassigned = await alarm_crud.count_unassigned(db, workshops=visible)

    # ---- ★ 事件口径（今日）：把"推送条数"还原成"违规次数" ----
    # 配置项 ISUP_EVENT_MERGE_SECONDS，现场可调（默认 120 秒）
    from server.config import get_settings
    ev_window = int(getattr(get_settings(), "event_merge_seconds", 120) or 120)
    today_end = today_start + timedelta(days=1)

    ev_stats = await alarm_crud.count_event_stats(
        db, start=today_start, end=today_end, workshops=visible, window_seconds=ev_window
    )
    people_stats = await alarm_crud.count_alarmed_people(
        db, start=today_start, end=today_end, workshops=visible, window_seconds=ev_window
    )
    hotspots = await alarm_crud.count_channel_hotspots(
        db, start=today_start, end=today_end, workshops=visible,
        window_seconds=ev_window, limit=6,
    )
    quality = await alarm_crud.count_data_quality(
        db, start=today_start, end=today_end, workshops=visible
    )

    return DashboardOut(
        today=stats["today"],
        yesterday=yesterday,
        pending=stats["pending"],
        handled=stats["handled"],
        devices_online=online,
        devices_total=total,
        trend=[TrendPoint(**t) for t in trend],
        workshops=[WorkshopStat(**w) for w in ws_stats],
        hourly=[HourlyPoint(**h) for h in hourly],
        avg_handle_minutes=latency.get("avg_minutes"),
        handled_today=int(latency.get("handled_today") or 0),
        pending_images=int(pending_health.get("pending") or 0),
        orphan_images=int(pending_health.get("orphan") or 0),
        unassigned=unassigned,
        # ---- 事件口径 ----
        events_today=ev_stats["events"],
        records_today=ev_stats["records"],
        repeat_ratio=ev_stats["repeat_ratio"],
        event_window_seconds=ev_window,
        people_today=people_stats["people"],
        abnormal_events_today=people_stats["abnormal_events"],
        hotspots=[HotspotPoint(**h) for h in hotspots],
        data_quality=DataQualityOut(**quality),
    )


@router.get("/{alarm_id}", response_model=AlarmOut, summary="告警详情")
async def get_alarm(
    alarm_id: str,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require("alarm:read")),
):
    alarm = await alarm_crud.get_alarm(db, alarm_id)
    if alarm is None:
        raise HTTPException(status_code=404, detail="告警不存在")
    # ★ 对象级隔离：防止靠猜 ID 访问别的车间的告警
    ensure_alarm_visible(alarm, principal)
    return alarm_out(alarm)


# ---------------------------------------------------------------------------
# ★ 人工处置
# ---------------------------------------------------------------------------
@router.patch(
    "/{alarm_id}/handled",
    response_model=AlarmOut,
    summary="★ 标记为已处理 / 取消处理",
)
async def set_alarm_handled(
    alarm_id: str,
    payload: HandleIn,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require("alarm:write")),
):
    """标记处置状态。

    前端「标记为已处理」按钮调用；左侧红点 = 未处理数，会随之减少。
    """
    alarm = await alarm_crud.get_alarm(db, alarm_id)
    if alarm is None:
        raise HTTPException(status_code=404, detail="告警不存在")
    # ★ 对象级隔离
    ensure_alarm_visible(alarm, principal)

    alarm = await alarm_crud.set_handled(
        db, alarm, handled=payload.handled, by=principal.subject
    )

    # 广播给其他客户端，保证多端红点一致。
    # ★ 载荷带 workshop → 总线只推给对应车间
    # ★★ 2026-10-29：同时补 workshop_name，否则实时更新后前端只显示车间编码
    from server.services import workshop_service as _ws_svc
    from server.services.bus import bus

    with contextlib.suppress(Exception):
        payload_out = alarm_brief(alarm).model_dump(mode="json")
        _code = getattr(alarm, "workshop", None)
        payload_out["workshop"] = _code
        payload_out["workshop_name"] = await _ws_svc.resolve_workshop_name(db, _code)
        await bus.publish({"type": "alarm_updated", "data": payload_out})
    return alarm_out(alarm)


# ---------------------------------------------------------------------------
# ★ 批量标记处理（必须声明在 /{alarm_id} 之前）
# ---------------------------------------------------------------------------
@router.post(
    "/batch-handled",
    summary="★ 批量标记为已处理 / 取消处理",
)
async def batch_set_handled(
    payload: BatchHandledIn,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require("alarm:write")),
):
    """多条记录一起处理。★ 车间隔离：越权 ID 静默忽略。"""
    visible = principal.visible_workshops()
    updated = await alarm_crud.set_handled_many(
        db,
        payload.ids,
        handled=payload.handled,
        by=principal.subject,
        workshops=visible,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="未找到可更新的告警")

    # 广播更新，让其他在线客户端的列表/红点同步
    from server.services.bus import bus

    with contextlib.suppress(Exception):
        await bus.publish(
            {
                "type": "alarm_batch_handled",
                "data": {
                    "ids": updated,
                    "handled": payload.handled,
                    "by": principal.subject,
                },
            }
        )
    return {
        "code": 0,
        "message": f"已{'标记' if payload.handled else '取消'}处理 {len(updated)} 条",
        "data": {"updated_ids": updated},
    }


# ---------------------------------------------------------------------------
# ★ 删除
# ---------------------------------------------------------------------------
# ⚠️ 注意：批量删除必须声明在 /{alarm_id} 之前。
#    FastAPI 按声明顺序匹配，`/alarms/batch-delete` 会被 `/alarms/{alarm_id}`
#    当成 alarm_id="batch-delete" 吃掉。虽然两者方法不同（POST vs GET/DELETE）
#    当前不会冲突，但保持这个顺序可以避免以后加 POST /{alarm_id} 时踩坑。
@router.post(
    "/batch-delete",
    summary="★ 批量删除告警（连磁盘文件一起删）",
)
async def batch_delete_alarms(
    payload: BatchDeleteIn,
    request: Request,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require("alarm:write")),
):
    """批量删除。★ 同时删除磁盘上的图片/视频文件。

    ★ 车间隔离：只能删自己可见车间的告警；越权的 ID 会被静默忽略
      （不报错、不删除），避免「猜 ID 删别人的数据」。
    """
    visible = principal.visible_workshops()
    svc = getattr(request.app.state, "playback_service", None)

    deleted_all: list[str] = []
    removed = 0
    failed = 0

    async def _wipe(batch_ids: list[str]) -> None:
        nonlocal removed, failed
        if not batch_ids:
            return
        ids, paths_by_alarm = await alarm_crud.delete_alarms(db, batch_ids)
        if svc is not None:
            for aid in ids:
                svc.cancel(aid)
        for aid in ids:
            r, f = playback_registry.delete_alarm_files(
                aid, file_paths=paths_by_alarm.get(aid, [])
            )
            removed += r
            failed += f
        deleted_all.extend(ids)

    if payload.all:
        flt = AlarmFilter(
            workshops=visible,
            device_id=payload.device_id or None,
            workshop=payload.workshop or None,
            rule_name=payload.rule_name or None,
            start=payload.start,
            end=payload.end,
            has_image=payload.has_image,
            alarm_type=payload.alarm_type,
        )
        while True:
            batch = await alarm_crud.list_alarm_ids(db, f=flt, limit=400)
            if not batch:
                break
            await _wipe(batch)
        unfiltered = not any(
            [
                payload.device_id,
                payload.workshop,
                payload.rule_name,
                payload.start,
                payload.end,
                payload.has_image is not None,
                payload.alarm_type is not None,
            ]
        )
        if visible is None and unfiltered:
            from sqlalchemy import delete as sql_delete

            from server.models import PendingImage

            pend = list((await db.execute(select(PendingImage))).scalars().all())
            for p in pend:
                if p.file_path:
                    r, f = playback_registry.delete_alarm_files(
                        p.matched_alarm_id or "pending",
                        file_paths=[p.file_path],
                    )
                    removed += r
                    failed += f
            if pend:
                await db.execute(sql_delete(PendingImage))
                await db.commit()
            removed += playback_registry.purge_orphan_media_dirs()
    else:
        allowed_ids: list[str] = []
        for aid in dict.fromkeys(payload.ids):
            alarm = await alarm_crud.get_alarm(db, aid)
            if alarm is None:
                continue
            if visible is not None:
                if not visible or getattr(alarm, "workshop", None) not in visible:
                    logger.warning(
                        "拒绝越权删除: %s 试图删除车间 %s 的告警 %s",
                        principal.subject,
                        getattr(alarm, "workshop", None),
                        aid,
                    )
                    continue
            allowed_ids.append(aid)
        await _wipe(allowed_ids)

    if not deleted_all and not payload.all:
        raise HTTPException(status_code=404, detail="未找到可删除的告警")

    logger.info(
        "批量删除 %d 条告警，清理文件 %d 个（失败 %d）",
        len(deleted_all),
        removed,
        failed,
    )
    await _broadcast_delete(deleted_all)
    return {
        "code": 0,
        "message": f"已删除 {len(deleted_all)} 条",
        "data": {"deleted_ids": deleted_all, "files_removed": removed},
    }


@router.delete(
    "/{alarm_id}",
    summary="★ 删除告警（连磁盘上的图片/视频一起删）",
)
async def delete_alarm(
    alarm_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require("alarm:write")),
):
    """删除一条告警。

    ★ 与同事 v3 版本的差异：**同时删除磁盘上的媒体文件**。
      否则每删一条告警就留下一份 mp4 和若干 jpg，长期运行会把盘塞满。

    ★ 车间隔离：先校验该告警对本账号可见，否则 404。
    """
    if alarm_id == "batch-delete":
        # 理论上不可达（POST 优先），但显式挡住更安全
        raise HTTPException(status_code=405, detail="请用 POST /api/alarms/batch-delete")

    # ★ 对象级隔离：必须在删除前校验，否则 B 车间能删掉 A 车间的数据
    alarm = await alarm_crud.get_alarm(db, alarm_id)
    if alarm is None:
        raise HTTPException(status_code=404, detail="告警不存在")
    ensure_alarm_visible(alarm, principal)

    paths = await alarm_crud.delete_alarm(db, alarm_id)
    if paths is None:
        raise HTTPException(status_code=404, detail="告警不存在")

    # 若该告警正在抓取回放，通知回放服务停止（避免产物无人回收）
    svc = getattr(request.app.state, "playback_service", None)
    if svc is not None:
        svc.cancel(alarm_id)

    removed, failed = playback_registry.delete_alarm_files(alarm_id, file_paths=paths)
    logger.info("已删除告警 %s，清理文件 %d 个（失败 %d）", alarm_id, removed, failed)

    await _broadcast_delete([alarm_id])
    return {"code": 0, "message": "已删除", "data": {"id": alarm_id, "files_removed": removed}}


async def _broadcast_delete(ids: list[str]) -> None:
    """通过事件总线通知前端移除这些告警。

    消息形状与 ws.py 的透传约定一致：{"type": ..., "data": {...}}
    """
    from server.services.bus import bus

    with contextlib.suppress(Exception):
        await bus.publish({"type": "alarm_deleted", "data": {"ids": ids}})
