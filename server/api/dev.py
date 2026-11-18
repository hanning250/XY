# -*- coding: utf-8 -*-
"""★ 开发调试接口（仅 ISUP_DEBUG=true 时注册，交付机不注册）。

现场报警稀疏，开发/演示时需要一个「随时造一条报警」的入口来验证
值守页、大图、WS 推送等链路。生产环境（ISUP_DEBUG=false）本模块
**根本不会注册**，攻击面为零。

⚠️ 与真实链路的一致性：本接口走的是与设备上报**同一条**落库 + 总线
推送路径（alarm_crud.create_alarm → bus.publish_alarm），因此前端
看到的行为与真实报警完全一致（含车间隔离、图片、WS 推送）。
"""

from __future__ import annotations

import logging
import random
import shutil
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.base import Principal
from server.auth.deps import require
from server.config import PROJECT_ROOT
from server.db import get_session
from server.models import Alarm, AlarmImage
from server.services import media as media_svc
from server.services.bus import bus
from server.services.serialize import alarm_brief

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dev", tags=["调试（仅 debug 模式）"])


@router.post("/simulate-alarm", summary="★ 模拟一条报警（造数据用，仅 debug 模式）")
async def simulate_alarm(
    workshop: str | None = Query(None, description="指定车间 code；留空随机取已有告警的车间"),
    device_id: str = Query("sim-box", description="设备 ID"),
    channel: int = Query(1, ge=1, description="通道号"),
    # ★ 下面两个参数用于验证前端的触发口径（全屏/响铃只对"检出违规"生效）：
    #   alarmed_count=0 或 is_aiop=false 时，前端**不应**弹全屏、不应响铃。
    #   本接口仅 debug 模式注册，交付机不存在。
    alarmed_count: int = Query(1, ge=0, description="违规人数（0 = 检出但全部合规）"),
    is_aiop: bool = Query(True, description="是否为 AIOP 智能分析类告警（false 模拟移动侦测等噪声）"),
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require("alarm:write")),
):
    """造一条报警并**立即通过 WebSocket 推送**（前端会像收到真报警一样处理）。

    图片：直接从库里已有的告警图片复制一份（演示效果与真实现场一致）；
    若库里一张图都没有，则创建一条无图报警（前端会显示"暂无抓拍图"占位）。
    """
    # 1) 找一张已有图片当素材（复制成新文件，避免多条告警共用同一文件被误删）
    src = (
        await db.execute(select(AlarmImage).order_by(AlarmImage.id.desc()).limit(1))
    ).scalars().first()

    ws = workshop
    if ws is None and src is not None:
        owner = (
            await db.execute(select(Alarm).where(Alarm.id == src.alarm_id))
        ).scalars().first()
        if owner is not None:
            ws = owner.workshop
    if ws is None:
        # 兜底：取第一个车间，保证告警可见（否则未指派 = 谁也看不到）
        from server.models import Workshop

        row = (await db.execute(select(Workshop).order_by(Workshop.code))).scalars().first()
        ws = row.code if row else None

    # 2) 建告警（与设备上报同一条路径）
    now = datetime.now()
    from server.crud import alarm as alarm_crud

    alarm = await alarm_crud.create_alarm(
        db,
        device_id=device_id,
        channel=channel,
        alarm_type=13,
        alarm_time=now,
        content_raw='{"simulated": true}',
        content_json={
            "deviceID": device_id,
            "channelID": channel,
            "eventType": "AIOP_Polling_Snap" if is_aiop else "VMD",
            "typeText": "模拟报警（调试）",
            "isAiop": is_aiop,
            "ruleName": "未穿防护服报警",
            "mpName": "模拟算法模型",
            "personCount": random.randint(1, 4),
            "alarmedCount": alarmed_count,
            "summary": f"模拟报警，检出 {random.randint(1, 4)} 人，其中 {alarmed_count} 人违规",
            "simulated": True,
        },
        correlate_window_seconds=0,
        workshop=ws,
        workshop_rule="simulated",
    )

    # 3) 复制图片素材挂到新告警上
    images = 0
    if src is not None:
        src_abs = PROJECT_ROOT / src.file_path
        if src_abs.is_file():
            try:
                data = src_abs.read_bytes()
                new_path = media_svc.build_storage_path(
                    file_hash=media_svc.decide_file_hash("", data),
                    source_name=f"sim_{alarm.id[:8]}.jpg",
                    when=now,
                )
                shutil.copyfile(src_abs, new_path)
                w, h = media_svc.probe_jpeg_size(data)
                await alarm_crud.add_image(
                    db,
                    alarm=alarm,
                    alarm_id=alarm.id,
                    file_hash="SIMULATED",
                    file_path=media_svc.relative_to_project(new_path),
                    source_name="simulated.jpg",
                    width=w,
                    height=h,
                    file_size=len(data),
                    linked_by="dev",
                )
                images = 1
            except OSError:
                logger.exception("模拟报警：复制图片失败（继续创建无图告警）")

    await db.refresh(alarm)

    # 4) 走总线推送（带 workshop，事件总线按车间分房间投递）
    # ★★ 2026-10-29：同时补 workshop_name，避免实时推送只显示车间编码
    from server.services import workshop_service as _ws_svc

    payload = alarm_brief(alarm).model_dump(mode="json")
    payload["workshop"] = alarm.workshop
    payload["workshop_name"] = await _ws_svc.resolve_workshop_name(db, alarm.workshop)
    await bus.publish_alarm(payload)

    logger.info("★ 已模拟一条报警 %s（车间=%s，图片=%d）", alarm.id[:8], ws, images)
    return {
        "code": 0,
        "message": "已模拟一条报警并推送",
        "data": {"id": alarm.id, "workshop": ws, "images": images},
    }
