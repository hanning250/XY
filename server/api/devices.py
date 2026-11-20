# -*- coding: utf-8 -*-
"""内部 API：设备。

★ 设备管理页的数据源：
  · GET /api/devices            → NVR 设备列表（整机在线状态）
  · GET /api/devices/channels   → 通道列表（★ 按车间隔离，每路摄像头一条）
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.base import Principal
from server.auth.deps import require
from server.crud import device as device_crud
from server.db import get_session
from server.schemas import ChannelDeviceInfo, DeviceOut

router = APIRouter(prefix="/devices", tags=["内部-设备"])


@router.get("", response_model=list[DeviceOut], summary="设备列表与在线状态")
async def list_devices(
    db: AsyncSession = Depends(get_session),
    _: Principal = Depends(require("device:read")),
):
    rows = await device_crud.list_devices(db)
    return [DeviceOut.model_validate(r) for r in rows]


@router.get(
    "/channels",
    response_model=list[ChannelDeviceInfo],
    summary="★ 通道列表（按车间隔离，设备管理页用）",
)
async def list_channels_scoped(
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require("device:read")),
):
    """每路摄像头通道一条记录，含父设备在线状态与最近告警时间。

    ★ 车间子账号只能看到绑定本车间的通道 —— 这就是
      「每个车间账号只能看到本车间的设备在线状态」的实现。
    """
    rows = await device_crud.list_channel_devices(
        db, workshops=principal.visible_workshops()
    )
    return [ChannelDeviceInfo(**r) for r in rows]


# --------------------------------------------------------------------------
# ★★ 实时在线设备（2026-10-26 新增）
#
# 与上面两个接口的区别（这是关键）：
#
#   GET /api/devices          → 读**数据库**，返回"历史累积"的设备记录
#                              包括早就下线、再没连过的（HaiKang-1 等）
#
#   GET /api/devices/live     → 读**SDK 内存表**，返回"此刻真正连着平台"
#                              的设备。设备注册进来就在，断开就消失。
#
# 为什么需要 live 接口：
#   现场运维要的是「现在有哪些设备在连」，而不是「历史上出现过的设备」。
#   数据库里的记录可能是几天前注册过、之后再没上线过的，混在一起看
#   会造成"明明没这台设备却列在那里"的困惑。
# --------------------------------------------------------------------------
@router.get(
    "/live",
    summary="★★ 实时在线设备（数据库登记，不含历史记录）",
)
async def list_live_devices(
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require("device:read")),
):
    """当前设备表（数据库登记 + 在线标记）。

    返回字段：
      · device_id / ip / channels / last_alarm
    """
    from sqlalchemy import func, select

    from server.models import Alarm, Channel, Device
    db_devices = {
        d.device_id: d
        for d in (await db.execute(select(Device))).scalars().all()
    }
    ch_counts = dict(
        (
            await db.execute(
                select(Channel.last_device_id, func.count(Channel.id)).group_by(
                    Channel.last_device_id
                )
            )
        ).all()
    )
    last_alarms = dict(
        (
            await db.execute(
                select(Alarm.device_id, func.max(Alarm.alarm_time)).group_by(
                    Alarm.device_id
                )
            )
        ).all()
    )

    out = []
    for device_id, d in sorted(db_devices.items()):
        out.append(
            {
                "device_id": device_id,
                "user_id": None,
                "in_db": True,
                "online": bool(getattr(d, "online", False)),
                "ip": getattr(d, "ip", None),
                "channels": int(ch_counts.get(device_id, 0) or 0),
                "last_alarm": (
                    last_alarms.get(device_id).isoformat()
                    if last_alarms.get(device_id)
                    else None
                ),
            }
        )

    return {
        "count": len(out),
        "note": "设备列表来自数据库（HCNet/ISAPI）",
        "devices": out,
    }

