# -*- coding: utf-8 -*-
"""★ 摄像头身份解析（一次查询批量还原，避免 N+1）。

## 为什么需要它

甲方现场是「单盒子多通道」：一台 NVR 下挂多路摄像头，`deviceID` 相同、
`channel` 不同。甲方要能**按摄像头区分**，而 `device_id + channel` 这种
组合对人不友好，也没法展示"这是哪个位置的摄像头"。

所以对外统一给出四件套：

    device_id   父设备（NVR）标识
    channel     通道号（该 NVR 下的第几路）
    camera_id   每路摄像头唯一的稳定标识（childDevID，换设备也稳定）
    camera_name 管理员起的名字（如「1号车间-东侧工装检测」）

## 数据来源与优先级

    ① Channel 表按 (last_device_id, channel_id) 精确匹配 —— 实测覆盖 1306/1307
    ② 匹配不上时退回报文里的 childDevID / channelName（调试模拟数据走这条）
    ③ 都没有 → None（前端/甲方自己按 device_id+channel 处理）

## 为什么批量查

告警列表一页最多 1000 条，逐条查 Channel 就是 1000 次查询。
这里先把本页出现的 (device_id, channel) 去重，再一条 IN 查询拿全。
"""

from __future__ import annotations

import json
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models import Alarm, Channel

__all__ = ["resolve_cameras", "camera_of", "resolve_camera_details", "CameraInfo"]

# (device_id, channel) -> 摄像头信息
CameraInfo = dict


async def resolve_cameras(
    db: AsyncSession, alarms: Iterable[Alarm]
) -> dict[tuple[str, int], Channel]:
    """批量取本页告警对应的 Channel 记录。"""
    pairs = {(a.device_id, a.channel) for a in alarms}
    if not pairs:
        return {}

    devices = {d for d, _ in pairs}
    channels = {c for _, c in pairs}
    stmt = select(Channel).where(
        Channel.last_device_id.in_(devices),
        Channel.channel_id.in_(channels),
    )
    rows = (await db.execute(stmt)).scalars().all()
    return {(c.last_device_id, c.channel_id): c for c in rows}


def camera_of(
    alarm: Alarm, cmap: dict[tuple[str, int], Channel]
) -> tuple[str | None, str | None]:
    """返回 (camera_id, camera_name)。"""
    ch = cmap.get((alarm.device_id, alarm.channel))
    if ch is not None:
        return (
            ch.child_dev_id,
            ch.display_name or ch.channel_name,
        )

    # 兜底：报文里自带（调试模拟告警没有 Channel 记录，但可能带这些字段）
    try:
        payload = json.loads(alarm.content_json or "{}") or {}
    except (ValueError, TypeError):
        payload = {}
    return payload.get("childDevID"), payload.get("channelName")

async def resolve_camera_details(
    db: AsyncSession, alarms: Iterable[Alarm]
) -> dict[tuple[str, int], dict]:
    """★★ 批量解析告警对应的摄像头**完整信息**（给甲方报信用）。

    返回 ``{(device_id, channel): {
        camera_no, camera_id, camera_name, display_name,
        camera_ip, camera_model
    }}``

    ## 甲方要求（2026-10-27）

    对外的报警报文必须能定位到「具体哪一台摄像头」，字段与前端一致：

      · camera_no     摄像头编号（前端显示 CH1 / CH2 …）
      · camera_id     唯一哈希（childDevID，换设备也不变）
      · camera_name   NVR 上的原始名（如 Camera 01，多路可能重名）
      · display_name  管理员在前端起的自定义名（如「2号车间-西侧工装检测」）
      · camera_ip     摄像头**自己**的 IP（不是 NVR 的）
      · camera_model  摄像头型号（如 DS-2CD7T4KY-LSW）

    ## 数据来源

    ① **channel 表**（必需）：channel_id / child_dev_id / display_name / channel_name
    ② **NVR 的 ISAPI**（补 IP 和型号）：channel 表里没有硬件信息，
       需要现查 ``/ISAPI/ContentMgmt/InputProxy/channels/<id>``。
       按 NVR 分组批量查一次，带 30 秒缓存，不拖慢接口。

    ★ ISAPI 不可用时（NVR 离线 / 没配密码），camera_ip / camera_model 为 None，
      其余字段照常返回 —— 不影响主要功能。
    """
    pairs = {(a.device_id, a.channel) for a in alarms}
    if not pairs:
        return {}

    cmap = await resolve_cameras(db, alarms)

    # ---- ① 先看配置能不能查 ISAPI ----
    try:
        from server.config import get_settings

        cfg = get_settings()
        use_isapi = bool(
            getattr(cfg, "video_use_isapi", False)
            and getattr(cfg, "isapi_host", "")
        )
    except Exception:
        cfg = None
        use_isapi = False

    # ---- ② 按 NVR 分组批量查摄像头 IP / 型号 ----
    isapi_states: dict[int, object] = {}
    if use_isapi and cfg is not None:
        chs = sorted({int(ch) for _, ch in pairs if ch})
        if chs:
            try:
                from server.services.channel_status import fetch_channel_states

                isapi_states = fetch_channel_states(
                    cfg.isapi_host,
                    cfg.isapi_port,
                    cfg.isapi_username,
                    cfg.isapi_password,
                    chs,
                )
            except Exception:
                # 查不到就留空，不能因为补字段把主接口搞挂
                isapi_states = {}

    # ---- ③ 组装（三级兜底，2026-10-27 修）----
    #
    # 背景：为修车间归属，昨天清空了 channel 表的 child_dev_id / task_id。
    # 现在 channel 行还在（能按 device_id+channel 查到），但 child_dev_id 是 None。
    # 如果不从报警报文兜底，对外报文的 camera_id / display_name 就会是空。
    out: dict[tuple[str, int], dict] = {}
    for a in alarms:
        key = (a.device_id, a.channel)
        ch_row = cmap.get(key)

        # 先解报警报文（兜底用）
        try:
            payload = json.loads(a.content_json or "{}") or {}
        except (ValueError, TypeError):
            payload = {}
        payload_child = payload.get("childDevID") or payload.get("childDevId")
        payload_ch_name = payload.get("channelName") or ""

        if ch_row is not None:
            camera_no = ch_row.channel_id or a.channel
            # ★ channel 表优先，空则用报文的 childDevID
            camera_id = ch_row.child_dev_id or payload_child
            # ★ 自定义名（管理员在前端起的）优先
            display_name = ch_row.display_name
            # ★ NVR 原始名，空则用报文里的，再空则 CH{n}
            camera_name = (
                ch_row.channel_name
                or payload_ch_name
                or (f"CH{camera_no}" if camera_no else None)
            )
        else:
            # 连 channel 行都没有：全从报文兜底
            camera_no = a.channel
            camera_id = payload_child
            display_name = None
            camera_name = payload_ch_name or (
                f"CH{a.channel}" if a.channel else None
            )

        st = isapi_states.get(int(a.channel)) if a.channel else None
        camera_ip = getattr(st, "ip", None) if st else None
        camera_model = getattr(st, "model", None) if st else None

        out[key] = {
            "camera_no": camera_no,
            "camera_id": camera_id,
            "camera_name": camera_name,
            # ★ 自定义名 > NVR 原始名 > CH{n}，永不返回空
            "display_name": display_name or camera_name,
            "camera_ip": camera_ip,
            "camera_model": camera_model,
        }
    return out
