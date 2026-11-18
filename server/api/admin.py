# -*- coding: utf-8 -*-
"""★ 车间 / 通道 / 账号 管理接口（需管理员权限）。

这些是「多车间管理」的操作入口：
  · 车间的增删改
  · 通道指派（admin 看缩略图认出是哪个车间 → 点一下分配）
  · 账号的创建与车间授权

所有写操作都要求 superuser（或未启用登录的开发模式）。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.base import Principal
from server.auth.deps import current_principal
from server.auth.scoping import require_superuser
from server.crud import user as user_crud
from server.db import get_session
from server.models import Alarm, Channel, User, Workshop
from server.schemas import (
    ChannelAssignIn,
    ChannelOut,
    ChannelRenameIn,
    PasswordResetIn,
    UserCreateIn,
    UserOut,
    UserUpdateIn,
    WorkshopIn,
    WorkshopOut,
)
from server.services import workshop_service as ws
from server.services import timeutil

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["管理-车间与账号"])


def _guard(principal: Principal) -> None:
    require_superuser(principal)


# --------------------------------------------------------------------------
# 车间
# --------------------------------------------------------------------------
@router.get("/workshops", response_model=list[WorkshopOut], summary="车间列表")
async def list_workshops(
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(current_principal),
):
    _guard(principal)
    return await ws.list_workshops(db)


@router.post("/workshops", response_model=WorkshopOut, summary="新建/更新车间")
async def upsert_workshop(
    payload: WorkshopIn,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(current_principal),
):
    _guard(principal)
    row = await db.get(Workshop, payload.code)
    if row is None:
        row = Workshop(
            code=payload.code,
            name=payload.name,
            description=payload.description,
            sort_order=payload.sort_order,
        )
        db.add(row)
    else:
        row.name = payload.name
        row.description = payload.description
        row.sort_order = payload.sort_order
    await db.commit()
    await db.refresh(row)
    # ★ 新建或改名都会影响 code→name 映射，让缓存立即失效
    ws.invalidate_workshop_name_cache()
    return row


@router.delete("/workshops/{code}", summary="删除车间")
async def delete_workshop(
    code: str,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(current_principal),
):
    _guard(principal)
    # 安全起见：有告警或通道归属时不允许直接删除
    n_alarm = int(
        (await db.execute(select(func.count(Alarm.id)).where(Alarm.workshop == code))).scalar()
        or 0
    )
    if n_alarm:
        raise HTTPException(
            status_code=409,
            detail=f"该车间还有 {n_alarm} 条告警，请先把通道改派到其它车间",
        )
    row = await db.get(Workshop, code)
    if row is None:
        raise HTTPException(status_code=404, detail="车间不存在")
    await db.delete(row)
    await db.commit()
    ws.invalidate_workshop_name_cache()
    return {"code": 0, "message": "已删除"}


@router.put("/workshops/{code}/name", response_model=WorkshopOut, summary="★ 修改车间名字")
async def rename_workshop(
    code: str,
    name: str,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(current_principal),
):
    """★ 只改名字不动 code —— 归属关系、历史告警全部自动跟随。"""
    _guard(principal)
    row = await db.get(Workshop, code)
    if row is None:
        raise HTTPException(status_code=404, detail="车间不存在")
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="车间名字不能为空")
    row.name = name
    await db.commit()
    await db.refresh(row)
    # ★ 改名立即生效：清缓存，避免列表/推送还显示旧名（最多 60s 才自愈就太慢）
    ws.invalidate_workshop_name_cache()
    return row


# --------------------------------------------------------------------------
# 通道
# --------------------------------------------------------------------------
@router.get(
    "/channels",
    response_model=list[ChannelOut],
    summary="★ 通道列表（含待指派 + 识别信息）",
)
async def list_channels(
    status: str | None = None,
    with_samples: bool = True,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(current_principal),
):
    """★ 通道列表。运维据此把通道指派给车间。

    ### 为什么返回 sample_image_url

    系统只能给出 `childDevID` 这类哈希串，**人无法据此判断是哪个车间**。
    所以这里附带该通道**最近一张告警图**：
    看画面就能认出「这是 1 号车间东侧」。

    参数 `with_samples=False` 可跳过样本查询（通道很多时更快）。

    ### 典型用法

        1. GET /api/admin/channels?status=unassigned   → 看有哪些待指派
        2. 打开返回的 sample_image_url 确认车间
        3. POST /api/admin/channels/{id}/assign        → 指派
    """
    _guard(principal)
    rows = await ws.list_channels(db, status=status)

    # ★ 2026-XX 修复：管理接口原来只做 ChannelOut.model_validate(c)，
    #   而 ChannelOut 没有 online 字段 → 设备管理页所有通道恒显示「离线」，
    #   与「明明在报警」自相矛盾。
    #
    # ★★ 2026-10-26：在线判定改为**查摄像头真实状态**（与
    #   /api/devices/channels 走同一套逻辑），不再直接抄父设备状态。
    #   实测：box001（NVR）在线，但 5 个通道里只有 ch1 真接了摄像头。
    #   原来这里 `item.online = online_map[parent]` 会让 5 个通道全显示在线。
    from server.crud.device import (
        device_online_map,
        list_channel_devices,
    )

    online_map = await device_online_map(db)

    # 一次拿到所有通道的真实状态（含 camera_ip / camera_model）
    real_map: dict[int, dict] = {}
    try:
        for r in await list_channel_devices(db):
            real_map[int(r["id"])] = r
    except Exception:
        logger.debug("获取通道真实状态失败，退回设备级判定", exc_info=True)

    out: list[ChannelOut] = []
    for c in rows:
        item = ChannelOut.model_validate(c)
        item.channel_no = c.channel_id
        parent = c.last_device_id or c.child_dev_id or None
        item.parent_device = parent

        real = real_map.get(int(c.id))
        if real is not None and real.get("camera_online_known"):
            # ★ 优先用摄像头自己的在线状态
            item.online = real.get("online")
            item.parent_missing = bool(real.get("parent_missing"))
            item.camera_ip = real.get("camera_ip")
            item.camera_model = real.get("camera_model")
            item.camera_serial = real.get("camera_serial")
            item.camera_online_known = True
        elif parent and parent in online_map:
            # 查不到真实状态时才退回父设备（NVR）状态
            item.online = online_map[parent]
            item.parent_missing = False
            item.camera_online_known = False
        else:
            # 父设备查不到（历史残留数据）→ 明确「未知」，不谎报离线
            item.online = None
            item.parent_missing = bool(parent)
            item.camera_online_known = False
        item.last_seen = c.last_seen_at

        if with_samples:
            info = await ws.channel_identify_info(db, c)
            item.last_alarm_at = info["last_alarm_at"]
            item.last_alarm_count = info["last_alarm_count"]
            item.sample_image_url = info["sample_image_url"]
            item.sample_image_count = info["sample_image_count"]
        out.append(item)
    return out


@router.get(
    "/channels/{channel_pk}/samples",
    summary="★ 通道样本图片（看画面认车间）",
)
async def channel_samples(
    channel_pk: int,
    limit: int = 5,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(current_principal),
):
    """返回该通道最近几张告警图，供人工确认它属于哪个车间。

    图片 URL 为内部路径（`/media/...`），前端/工具访问时需带
    `?token=<jwt>`；也可用 URL 里的文件名自行拼对外地址。
    """
    _guard(principal)
    from server.models import Channel

    c = await db.get(Channel, channel_pk)
    if c is None:
        raise HTTPException(status_code=404, detail="通道不存在")

    samples = await ws.channel_samples(db, c, limit=limit)
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "channel_id": channel_pk,
            "child_dev_id": c.child_dev_id,
            "workshop_code": c.workshop_code,
            "samples": [
                {
                    # ★ 与 channel_samples() 的返回契约对齐：它给的是
                    #   file_path（相对项目根的落盘路径），不是 url。
                    #   这里原先读 s["url"] 会 KeyError → 整个接口 500
                    #   （2026-10-21 用接口快照回归时发现）。
                    "url": s["file_path"],
                    "alarm_time": timeutil.to_iso_local(s["alarm_time"]),
                    "type_text": s["type_text"],
                }
                for s in samples
            ],
        },
    }


@router.patch(
    "/channels/{channel_pk}",
    response_model=ChannelOut,
    summary="★ 通道改名（如「1号车间东侧摄像头」）",
)
async def rename_channel(
    channel_pk: int,
    payload: ChannelRenameIn,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(current_principal),
):
    _guard(principal)
    c = await db.get(Channel, channel_pk)
    if c is None:
        raise HTTPException(status_code=404, detail="通道不存在")
    c.display_name = payload.display_name
    await db.commit()
    await db.refresh(c)
    return c


@router.post(
    "/channels/{channel_pk}/assign",
    response_model=ChannelOut,
    summary="★ 把通道指派给车间（自动回填历史告警）",
)
async def assign_channel(
    channel_pk: int,
    payload: ChannelAssignIn,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(current_principal),
):
    """把通道指派给车间。

    ★ **副作用**：该通道的**历史告警会被一并归属**到该车间
      （否则旧数据永远无法被甲方拉到）。

    传 `workshop_code: null` 可取消指派（历史告警的归属不会被清除）。
    """
    _guard(principal)
    if payload.workshop_code:
        w = await db.get(Workshop, payload.workshop_code)
        if w is None:
            raise HTTPException(status_code=404, detail=f"车间 {payload.workshop_code} 不存在")
    row = await ws.assign_channel(
        db,
        channel_pk=channel_pk,
        workshop_code=payload.workshop_code or "",
        display_name=payload.display_name or "",
    )
    if row is None:
        raise HTTPException(status_code=404, detail="通道不存在")
    return row


# --------------------------------------------------------------------------
# 账号
# --------------------------------------------------------------------------
@router.get("/users", response_model=list[UserOut], summary="账号列表")
async def list_users(
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(current_principal),
):
    _guard(principal)
    rows = await user_crud.list_users(db)
    out = []
    for u in rows:
        ws_codes = await user_crud.list_user_workshops(db, u.id)
        item = UserOut.model_validate(u)
        item.workshops = ws_codes
        out.append(item)
    return out


@router.post("/users", response_model=UserOut, summary="新建账号并授权车间")
async def create_user(
    payload: UserCreateIn,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(current_principal),
):
    _guard(principal)
    exist = await user_crud.get_by_username(db, payload.username)
    if exist is not None:
        raise HTTPException(status_code=409, detail="用户名已存在")
    u = await user_crud.create_user(
        db,
        username=payload.username,
        password=payload.password,
        display_name=payload.display_name or payload.username,
        role=payload.role,
        superuser=payload.superuser,
        workshops=payload.workshops,
    )
    item = UserOut.model_validate(u)
    item.workshops = await user_crud.list_user_workshops(db, u.id)
    return item


@router.put("/users/{user_id}/workshops", summary="设置账号可见的车间")
async def set_user_workshops(
    user_id: int,
    workshops: list[str],
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(current_principal),
):
    _guard(principal)
    u = await db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    await user_crud.set_user_workshops(db, user_id=user_id, workshops=workshops)
    return {"code": 0, "message": "已更新", "data": {"workshops": workshops}}


@router.put("/users/{user_id}", response_model=UserOut, summary="★ 编辑账号（资料/密码/启停/车间授权）")
async def update_user(
    user_id: int,
    payload: UserUpdateIn,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(current_principal),
):
    """管理员编辑账号。字段全部可选，只更新传入的部分。

    ⚠️ 防锁死：不能停用或降级**最后一个**可用的超管账号。
    """
    _guard(principal)
    u = await db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="账号不存在")

    will_lose_admin = (
        (payload.superuser is False and u.is_superuser)
        or (payload.enabled is False and u.enabled and u.is_superuser)
    )
    if will_lose_admin and u.is_superuser:
        supers = await user_crud.list_users(db)
        active_super = [
            x for x in supers if x.is_superuser and x.enabled and x.id != u.id
        ]
        if not active_super:
            raise HTTPException(
                status_code=409,
                detail="系统至少需要一个可用的管理员账号，无法停用/降级最后一个管理员",
            )

    if payload.display_name is not None:
        u.display_name = payload.display_name
    if payload.superuser is not None:
        u.is_superuser = payload.superuser
    if payload.enabled is not None:
        u.enabled = payload.enabled
        # 停用账号同时清掉车间授权，防止重新启用后残留旧权限
        if not payload.enabled:
            await user_crud.set_user_workshops(db, user_id=u.id, workshops=[])
    if payload.password:
        await user_crud.set_password(db, user=u, password=payload.password)
    await db.commit()
    await db.refresh(u)

    if payload.workshops is not None:
        await user_crud.set_user_workshops(
            db, user_id=u.id, workshops=payload.workshops
        )

    item = UserOut.model_validate(u)
    item.workshops = await user_crud.list_user_workshops(db, u.id)
    return item


@router.delete("/users/{user_id}", summary="★ 删除账号")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(current_principal),
):
    _guard(principal)
    if principal.user_id and user_id == principal.user_id:
        raise HTTPException(status_code=409, detail="不能删除自己当前登录的账号")
    u = await db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    if u.is_superuser:
        supers = await user_crud.list_users(db)
        active_super = [x for x in supers if x.is_superuser and x.enabled and x.id != u.id]
        if not active_super:
            raise HTTPException(
                status_code=409,
                detail="系统至少需要一个管理员账号，无法删除最后一个管理员",
            )
    await db.delete(u)
    await db.commit()
    return {"code": 0, "message": "已删除"}


@router.put("/users/{user_id}/password", summary="重置密码")
async def reset_password(
    user_id: int,
    payload: PasswordResetIn,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(current_principal),
):
    """管理员重置密码。

    ★ 2026-XX 安全审查修复：密码原来走 URL query（?password=...），
      会进 uvicorn/反向代理的访问日志 —— 改为请求体传输。
    """
    _guard(principal)
    u = await db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    await user_crud.set_password(db, user=u, password=payload.password)
    logger.info("管理员 %s 重置了账号 %s 的密码", principal.subject, u.username)
    return {"code": 0, "message": "密码已重置"}


# --------------------------------------------------------------------------
# 队列健康度
# --------------------------------------------------------------------------
@router.get("/pending-stats", summary="待配对图片队列（串图风险监控）")
async def pending_stats(
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(current_principal),
):
    _guard(principal)
    return await ws.pending_stats(db)


# --------------------------------------------------------------------------
# ★★ 设备在线诊断（2026-10-26 新增）
#
# 为什么需要这个接口：
#   现场经常出现「明明在报警却显示离线 / 明明拔电了还显示在线」。
#   在线判定涉及四个数据源，任何一个滞后都会导致界面错误：
#
#     ① SDK 在线设备表（glo.deviceUserMap）—— 最强证据，不需要 IP
#     ② 主动探测（端口层 / ISAPI）—— 需要设备 IP
#     ③ 数据库 online 标记（SDK 回调维护）—— 可能残留旧值
#     ④ last_seen 兜底
#
#   运维在界面上只能看到"在线/离线"两个字，出问题无从下手。
#   这个接口把四个来源全部摊开，一眼就能定位是哪一层错了。
# --------------------------------------------------------------------------
@router.get(
    "/devices/online-debug", summary="★ 设备在线判定诊断（四层证据全展示）"
)
async def devices_online_debug(
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(current_principal),
):
    _guard(principal)

    from sqlalchemy import select

    from server.config import get_settings
    from server.crud.device import device_online_map
    from server.models import Device, utcnow
    from server.services.online_probe import probe_device
    from server.services.sdk_devices import (
        online_device_ids,
        online_snapshot,
        sdk_available,
    )

    cfg = get_settings()
    sdk_ok = sdk_available()
    sdk_ids = online_device_ids() if sdk_ok else set()
    sdk_map = online_snapshot() if sdk_ok else {}

    rows = (await db.execute(select(Device))).scalars().all()
    now = utcnow()

    devices = []
    for d in rows:
        item = {
            "device_id": d.device_id,
            "ip": d.ip,
            "port": d.port,
            "db_online": bool(d.online),
            "last_seen": d.last_seen.isoformat() if d.last_seen else None,
            "last_seen_minutes_ago": (
                round((now - d.last_seen).total_seconds() / 60, 1)
                if d.last_seen
                else None
            ),
            "in_sdk_table": (d.device_id in sdk_ids) if sdk_ok else None,
            "sdk_user_id": sdk_map.get(d.device_id),
        }
        if d.ip:
            r = probe_device(d.device_id, d.ip)
            item["probe_online"] = r.online
            item["probe_reason"] = r.reason
        else:
            item["probe_online"] = None
            item["probe_reason"] = "设备未登记 IP，无法主动探测"
        devices.append(item)

    final = await device_online_map(db)
    for item in devices:
        item["final_online"] = final.get(item["device_id"])

    return {
        "sdk_available": sdk_ok,
        "sdk_online_count": len(sdk_ids),
        "sdk_online_devices": sorted(sdk_ids),
        "probe_port": cfg.device_online_probe_port,
        "offline_after_minutes": cfg.device_offline_after_minutes,
        "devices": devices,
    }


# --------------------------------------------------------------------------
# ★ 视频补抓（历史告警）
# --------------------------------------------------------------------------
@router.post(
    "/videos/backfill",
    summary="★ 批量补抓历史告警的视频片段（±30 秒）",
)
async def backfill_videos(
    request: Request,
    date: str | None = None,
    since_hours: int | None = None,
    workshop: str | None = None,
    limit: int = 0,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(current_principal),
):
    """把历史告警（video_status=not_requested）提交到视频抓取队列。

    为什么需要：自动抓取只在**新告警到达时**触发，
    功能上线前的存量告警不会自己补上视频。

    ⚠️ 设备回放是**独占资源**，抓取串行进行，速度约 1 条/分钟。
    建议先用 limit 小批量试，确认没问题再全量。

    参数：
        date        补抓指定日期 YYYY-MM-DD
        since_hours 补抓最近 N 小时（与 date 二选一）
        workshop    只补抓该车间
        limit       最多提交多少条（0=不限）
    """
    _guard(principal)

    from datetime import timedelta

    from server.models import Alarm
    from server.services import timeutil

    conds = [Alarm.video_status == "not_requested"]
    if date:
        try:
            s, e = timeutil.day_bounds(date)
        except ValueError:
            raise HTTPException(status_code=400, detail="date 格式应为 YYYY-MM-DD")
        conds += [Alarm.alarm_time >= s, Alarm.alarm_time < e]
    elif since_hours:
        s = timeutil.now_local() - timedelta(hours=since_hours)
        conds.append(Alarm.alarm_time >= s)
    if workshop:
        conds.append(Alarm.workshop == workshop)

    stmt = select(Alarm.id).where(*conds).order_by(Alarm.alarm_time.asc())
    if limit:
        stmt = stmt.limit(limit)
    ids = [r[0] for r in (await db.execute(stmt)).all()]

    svc = getattr(request.app.state, "playback_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="回放服务未就绪")

    submitted = 0
    for aid in ids:
        if svc.submit(aid):
            submitted += 1

    logger.info(
        "视频补抓: 提交 %d/%d 条（by %s）", submitted, len(ids), principal.subject
    )
    return {
        "code": 0,
        "message": f"已提交 {submitted} 条到抓取队列",
        "data": {
            "candidates": len(ids),
            "submitted": submitted,
            "queue_size": svc.queue_size(),
            "note": "抓取串行进行，约 1 条/分钟；可用 /openapi/v1/alarms/{id}/video 查进度",
        },
    }


@router.get(
    "/video/grab-status",
    summary="★ 视频抓取链路诊断（在服务进程内查真实状态）",
)
async def video_grab_status(
    principal: Principal = Depends(current_principal),
):
    """★ 排查「为什么报警没有视频」的权威接口。

    ## 为什么要这个接口

    之前排查时用独立脚本读 `isup_runtime` / `playback_service`，
    但那是**另一个进程的新实例**（`started=False, sms=None`），
    和真正提供服务的进程不是同一份 —— 得出的结论是错的。

    这个接口在**服务进程内**执行，返回的是真实运行状态。

    ## 返回什么

      sdk.started        SDK 是否启动成功
      sdk.sms            是否拿到 SMS 实例（抓录像必需）
      playback.running   worker 线程是否在跑
      playback.workers   worker 数量
      playback.queue     当前排队数
      playback.active    正在抓取的告警数
      auto_capture       自动抓取开关
      diagnosis          一句话结论 + 建议
    """
    _guard(principal)

    from server.adapters.isup_runtime import runtime as isup_runtime
    from server.services.playback_service import playback_service as psvc

    sdk_started = bool(getattr(isup_runtime, "started", False))
    sdk_sms = getattr(isup_runtime, "sms", None) is not None
    ps_sms = getattr(psvc, "_sms", None) is not None
    ps_running = bool(getattr(psvc, "_running", False))
    ps_workers = len(getattr(psvc, "_workers", []) or [])
    try:
        qsize = psvc.queue_size() if hasattr(psvc, "queue_size") else None
    except Exception:
        qsize = None
    active = getattr(psvc, "_active", None)
    n_active = len(active) if active is not None else None

    from server.config import get_settings as _gs

    settings = _gs()
    auto = bool(getattr(settings, "video_auto_capture", False))

    # ---- 一句话结论 ----
    if not sdk_started:
        diag = (
            "❌ ISUP SDK 没启动 → 抓不了录像。"
            "检查 7665(SMS)/7661(CMS) 端口、设备是否连上来、SDK 库是否加载。"
        )
        level = "error"
    elif not sdk_sms:
        diag = (
            "❌ SDK 起来了但没拿到 SMS 实例 → 抓不了录像。"
            "检查 isup_runtime.start() 里 SMS 初始化是否成功。"
        )
        level = "error"
    elif not ps_sms:
        diag = (
            "❌ 回放服务没注入 SMS → submit() 会静默返回 False。"
            "这是「报警永远 not_requested」的直接原因。"
        )
        level = "error"
    elif not ps_running:
        diag = (
            "❌ 回放服务 worker 没启动 → 队列不会被消费。"
            "检查 main.py 里 playback_service.start() 是否执行。"
        )
        level = "error"
    elif not auto:
        diag = "⚠️ 自动抓取开关关闭（video_auto_capture=false）→ 需手动触发"
        level = "warn"
    else:
        diag = "✅ 抓取链路正常，新报警会自动入队"
        level = "ok"

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "level": level,
            "diagnosis": diag,
            "sdk": {
                "started": sdk_started,
                "sms": sdk_sms,
                "cms": getattr(isup_runtime, "cms", None) is not None,
                "ams": getattr(isup_runtime, "ams", None) is not None,
                "ss": getattr(isup_runtime, "ss", None) is not None,
                "last_error": getattr(isup_runtime, "last_error", None),
            },
            "playback": {
                "sms_injected": ps_sms,
                "running": ps_running,
                "workers": ps_workers,
                "queue": qsize,
                "active": n_active,
            },
            "auto_capture": auto,
            "video": {
                "pre_seconds": settings.video_pre_seconds,
                "post_seconds": settings.video_post_seconds,
                "use_isapi": getattr(settings, "video_use_isapi", False),
            },
        },
    }
