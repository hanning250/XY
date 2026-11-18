# -*- coding: utf-8 -*-
"""设备 CRUD。"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import time

import asyncio

from server.config import get_settings
from server.crud.scoping import is_denied
from server.models import Alarm, Channel, Device, utcnow

logger = __import__("logging").getLogger(__name__)


async def upsert_online(
    db: AsyncSession, *, device_id: str, ip: str | None = None, port: int | None = None
) -> Device:
    dev = await db.get(Device, device_id)
    if dev is None:
        dev = Device(device_id=device_id, ip=ip, port=port, online=True, last_seen=utcnow())
        db.add(dev)
    else:
        dev.online = True
        dev.last_seen = utcnow()
        if ip:
            dev.ip = ip
        if port:
            dev.port = port
    await db.commit()
    await db.refresh(dev)
    return dev


async def mark_offline(db: AsyncSession, *, device_id: str) -> None:
    dev = await db.get(Device, device_id)
    if dev is not None:
        dev.online = False
        await db.commit()


async def mark_all_offline(db: AsyncSession) -> int:
    """★ 服务启动时把所有设备置为离线。

    为什么：进程重启后，设备与**旧进程**的 ISUP 连接必然已断，
    但 device 表里残留的 online=1 不会被纠正 —— 新进程收不到
    任何离线事件（设备掉线发生在重启之前）。
    设备重新注册时会自动翻回在线，所以启动清零是安全的。

    ★ 2026-XX：清零同时把 last_seen 刷成"现在"。
      理由：设备重连需要约 6~10 秒，期间界面会显示离线；
      若 last_seen 还是几天前的时间戳，用户会以为设备长期掉线、
      甚至怀疑刚收到的报警是假的（"离线了怎么还会报警"）。
      刷新后，前端在线判定里的「静默超时」从重启时刻起算，
      设备一上线就恢复正常显示。
    """
    from sqlalchemy import update

    result = await db.execute(
        update(Device).values(online=False, last_seen=utcnow())
    )
    await db.commit()
    n = int(result.rowcount or 0)
    if n:
        logger.info(
            "启动清零：%d 台设备已重置为离线（等待重新注册，约 6~10 秒）", n
        )
    return n


async def _is_freshly_seen(dev: Device) -> bool:
    """★ online 标记可信度兜底。

    主逻辑：online 标记由 SDK 注册/离线回调维护（已修好离线 ID 解析），
    **以它为准**。

    兜底（ISUP 的离线事件是**尽力而为**的）：
      · 标记残留：进程被强杀收不到离线事件 → last_seen 超过
        device_offline_after_minutes（默认 3 天）按离线。

    ★ 2026-XX 修正：不再用「业务静默 30 分钟」判离线。
      本项目报警是「有人违规才产生」，间隔几小时很正常；
      原来那条规则会让一条安静的产线永远显示离线（实测通道 2 号
      33 分钟前刚报过警仍被判离线）。
      设备真的拔电时，SDK 会回调离线事件（ID 解析已修复）；
      极端的「静默断开且不回调」由 3 天 last_seen 兜底。
    """
    if not dev.online:
        return False
    minutes = get_settings().device_offline_after_minutes
    if minutes <= 0:
        return True
    if dev.last_seen is None:
        return False

    if (utcnow() - dev.last_seen) > timedelta(minutes=minutes):
        return False
    return True


_silence_cache: dict[str, tuple[float, float]] = {}
_SILENCE_CACHE_TTL = 60.0  # 秒：业务活性查询结果缓存，避免每次读请求扫表


async def _latest_business_seconds(device_id: str) -> float | None:
    """该设备最近一次业务数据（告警）距今的秒数。None = 从来没有过。"""
    from server.models import Alarm

    now = time.time()
    cached = _silence_cache.get(device_id)
    if cached and now - cached[0] < _SILENCE_CACHE_TTL:
        return cached[1]

    from server.db import SessionLocal

    async with SessionLocal() as db:
        latest = (
            await db.execute(
                select(func.max(Alarm.alarm_time)).where(
                    Alarm.device_id == device_id
                )
            )
        ).scalar()

    seconds: float | None = None
    if latest is not None:
        seconds = (utcnow() - latest).total_seconds()
        if seconds < 0:
            seconds = 0.0
    _silence_cache[device_id] = (now, seconds if seconds is not None else -1.0)
    return seconds


async def list_devices(db: AsyncSession) -> list[Device]:
    stmt = select(Device).order_by(Device.device_id.asc())
    devices = list((await db.execute(stmt)).scalars().all())
    # ★ 读取时做在线纠偏（不写库，避免读请求产生写放大）
    #
    # ★★ 2026-10-26：改用统一的 device_online_map（SDK 在线表优先），
    #    不再用只依赖 online 标记的 _is_freshly_seen —— 否则
    #    「设备列表」和「首页 5/6」会是两套结论。
    online_map = await device_online_map(db)
    for d in devices:
        d.online = online_map.get(d.device_id, bool(d.online))
    return devices


# ---------------------------------------------------------------------------
# ★ 车间维度的设备/通道统计（首页看板 + 设备管理页）
# ---------------------------------------------------------------------------
async def count_devices(
    db: AsyncSession,
    *,
    workshops: list[str] | None = None,
) -> tuple[int, int]:
    """统计（在线数, 总数）—— **按设备**，不是按通道。

    ## ★★★ 2026-10-26 口径修正（现场反馈）

    原来这个函数统计的是 `Channel.id` 的数量，被首页当成「设备数」显示。
    结果：一台 box001 有 5 个通道 → 首页显示「设备在线 5/6」，
    运维以为有 6 台设备，实际上只有 1 台在线、5 台早就没了。

    **设备数 ≠ 通道数**：
      · 1 台 NVR（box001）可以带 5 个通道（摄像头）
      · 设备管理页要按设备显示的话，1 台就是 1 行
      · 首页的「设备在线」应该是「几台设备连着平台」

    现在改成数 `Device` 表的行数，在线与否由 `device_online_map` 判定。

    ★ 车间隔离怎么处理：设备本身没有车间属性，车间是绑在**通道**上的。
      所以「某车间的设备」= 该车间通道所属的父设备（去重）。
      workshops=None → 全部设备；[] → (0,0)。
    """
    if is_denied(workshops):
        return (0, 0)

    conds: list = []
    if workshops is not None:
        conds.append(Channel.workshop_code.in_(workshops))
        conds.append(Channel.enabled.is_(True))

    # 该范围内的设备 ID 集合（去重）
    if workshops is None:
        dev_rows = (
            await db.execute(select(Device.device_id))
        ).scalars().all()
        device_ids = set(dev_rows)
    else:
        rows = (
            await db.execute(
                select(Channel.last_device_id, Channel.child_dev_id)
                .where(*conds)
            )
        ).all()
        device_ids = set()
        for last_dev, child_dev in rows:
            if last_dev:
                device_ids.add(last_dev)
            if child_dev:
                device_ids.add(child_dev)

    total = len(device_ids)
    if total == 0:
        return (0, 0)

    # 用统一判定（SDK 在线表优先）
    om = await device_online_map(db)
    online = sum(1 for did in device_ids if om.get(did) is True)
    return (online, total)


async def device_online_map(db: AsyncSession) -> dict[str, bool]:
    """★ 统一的「设备 → 是否在线」判定表。

    ## 判定顺序（2026-10-26 重做，四层证据）

    原来的问题：完全依赖 SDK 的 `online` 标记。而 ISUP 的离线事件是
    「尽力而为」——设备拔电、网络闪断、进程被强杀时，标记可能长时间
    停在旧值，界面上就会显示错的在线状态。

    ★★ 关键前提：**有些设备根本没有 IP**（NVR 转发、未填、动态分配），
       所以「靠 IP 探测」不能作为唯一手段。必须有一套管用的、
       不依赖 IP 的证据链。

    现在按以下顺序判断，取第一个能给出明确结论的：

      ① **SDK 在线设备表**（最强，且不需要 IP）
         `glo.deviceUserMap = {device_id: lUserID}` 由 SDK 的
         注册/注销回调直接维护，是「设备此刻是否连着平台」最准确的
         证据。设备注册了就一定在表里，断开就从表里移除。
         → 在表里 = 在线

      ② **主动探测**（有 IP 时二次确认）
         ①说在线、且设备有 IP → 探端口层 / ISAPI 复核
         ①说离线，但有 IP 且探得到 → 说明 SDK 表滞后，按在线处理
           （实测有设备在表外但 ISAPI 可达）

      ③ **SDK online 标记**（无 IP 且 SDK 表不可用时）
         退回数据库里由回调维护的标记。

      ④ **last_seen 兜底**：标记为在线但 last_seen 超过
         device_offline_after_minutes（默认 1 天）→ 判离线。
         只防「进程被强杀导致离线事件彻底丢失」。

    ★ 无 IP 的设备怎么显示：照样显示（设备管理页列出全部设备），
      在线状态由 ① / ③ / ④ 判定 —— ①是主力，不需要 IP。
    """
    from server.services.sdk_devices import (
        online_device_ids,
        sdk_available,
    )

    rows = (await db.execute(select(Device))).scalars().all()

    # ① SDK 在线表快照（一次取，避免每条都读）
    sdk_ids: set[str] = online_device_ids() if sdk_available() else set()
    sdk_ok = sdk_available()

    out: dict[str, bool] = {}

    for d in rows:
        did = d.device_id

        # ---- ① SDK 在线表是唯一的权威（2026-10-26 修正）----
        #
        # ★★★ 重要修正：不能再把「ISAPI 可达」当成在线证据。
        #
        #   实测场景（现场复现）：把所有设备从平台断开后，
        #   设备本身还在网络上（ping/ISAPI 都通），但**没连平台**。
        #   对平台来说这就是「不在线」——ISUP 连接断了，收不到报警、
        #   抓不到视频。
        #
        #   原来把 ISAPI 可达判为在线，导致：
        #     设备全断开后，前端仍显示 5 台在线（错的）
        #
        #   ISAPI 探测只在一种情况下有用：**确认设备彻底断电/断网**
        #   （连 ISAPI 都不通 → 肯定离线）。它不能用来证明"在线"，
        #   因为在线的前提是"连着平台"，那是 SDK 表说了算。
        if sdk_ok:
            if did in sdk_ids:
                out[did] = True
                continue
            # SDK 表里没有 → 没连平台 → 离线
            # （即使 ISAPI 可达也只能说明设备通网了，但没连平台）
            out[did] = False
            continue

        # ---- ② SDK 不可用时才退回旧逻辑 ----
        out[did] = await _is_freshly_seen(d)

    return out


async def list_channel_devices(
    db: AsyncSession,
    *,
    workshops: list[str] | None = None,
) -> list[dict]:
    """通道 + 父设备在线状态 + 最近告警时间。

    ★ workshops=None → 全部；[...] → 只返回绑定了这些车间的通道；[] → 空。
    """
    conds: list = []
    if is_denied(workshops):
        return []
    if workshops is not None:
        conds.append(Channel.workshop_code.in_(workshops))
        conds.append(Channel.enabled.is_(True))

    last_alarm = (
        select(
            Alarm.device_id,
            Alarm.channel,
            func.max(Alarm.alarm_time).label("last_alarm_at"),
        )
        .group_by(Alarm.device_id, Alarm.channel)
        .subquery()
    )

    # 通道没有独立的在线心跳，借用父设备的注册状态近似：
    # 父设备「可信在线」→ 该设备下所有通道视为在线。
    # ★ 在线判定在 Python 侧做新鲜度校验（SQL 里只过滤非空父设备），
    #   因为「online 且 last_seen 新鲜」无法在跨库/表达式里复用同一份配置。
    stmt = (
        select(
            Channel,
            Device.online,
            Device.last_seen,
            last_alarm.c.last_alarm_at,
        )
        .outerjoin(
            Device,
            (Device.device_id == Channel.last_device_id)
            | (Device.device_id == Channel.child_dev_id),
        )
        .outerjoin(
            last_alarm,
            (last_alarm.c.device_id == Channel.last_device_id)
            & (last_alarm.c.channel == Channel.channel_id),
        )
        .where(*conds)
        .order_by(Channel.id.asc())
    )
    rows = (await db.execute(stmt)).all()

    # ★★ 2026-10-26：通道在线判定改为**查摄像头真实状态**。
    #
    #   之前是「父设备（NVR）在线 → 它下面所有通道都算在线」，
    #   实测这是错的：box001 在线，5 个通道里只有 ch1 真接了摄像头，
    #   ch2~ch5 是空通道（online=false）。界面上显示 5 个摄像头在线，
    #   运维根本分不清哪个能用。
    #
    #   现在优先用 ISAPI 的 /InputProxy/channels/<id> 拿真实状态
    #   （见 services/channel_status.py），拿不到才退回父设备状态。
    #
    #   顺带把摄像头自己的 IP / 型号 也带出来，方便后续做绑定/自定义。
    from server.services.channel_status import fetch_channel_states

    from server.services.sdk_devices import online_device_ids, sdk_available

    sdk_ids = online_device_ids() if sdk_available() else set()

    # 按父设备分组，每台 NVR 只发一次请求
    nvr_channels: dict[str, list[int]] = {}
    for c, _online, _ls, _la in rows:
        did = str(c.last_device_id or c.child_dev_id or "")
        if did and c.channel_id:
            nvr_channels.setdefault(did, []).append(int(c.channel_id))

    from server.config import get_settings as _gs

    _cfg = _gs()
    real_states: dict[tuple[str, int], object] = {}

    # ★★ 2026-10-29 修复「两台设备显示同一个摄像头」（现场实测）
    #
    #   原实现：所有 NVR 都用配置里**同一个** isapi_host 去查通道状态
    #       fetch_channel_states(_cfg.isapi_host, ..., chs)
    #   并且 channel_status 的缓存键也是 (host, port, ch)。
    #
    #   于是：现场接了 2 台设备（box001 / HaiKang-1，MAC 不同、childDevID 不同），
    #   设备管理页两条记录的「摄像头型号 / IP」却完全一样 ——
    #   因为它们查的都是**同一台 NVR**（配置里那个地址）的 1 号通道。
    #
    #   修法：优先用**设备自己登记的 IP** 去查；只有该设备没登记 IP 时，
    #   才回退到配置里的默认 ISAPI 地址（并打日志，便于现场发现要补 IP）。
    #   缓存键同步加上 host，两台设备查不同 NVR 时不会互相污染。
    if getattr(_cfg, "video_use_isapi", False):
        # 一次性取出设备 IP 映射，避免每台 NVR 查一次库
        dev_ips: dict[str, str] = {}
        try:
            for _d in (await db.execute(select(Device.device_id, Device.ip))).all():
                if _d[1]:
                    dev_ips[str(_d[0])] = str(_d[1]).strip()
        except Exception:
            logger.debug("读取设备 IP 失败，全部回退默认 ISAPI 地址", exc_info=True)

        _fallback_used: set[str] = set()
        for did, chs in nvr_channels.items():
            # 只有该 NVR 真的在线时才去查（省得对离线设备发请求）
            if sdk_ids and did not in sdk_ids:
                continue
            # ★ 优先设备自己的 IP；没有再回退配置里的默认地址
            host = dev_ips.get(did) or _cfg.isapi_host
            if not host:
                # 既没登记 IP、也没配默认地址 → 跳过（不猜）
                continue
            if not dev_ips.get(did):
                _fallback_used.add(did)
            try:
                # Device HTTP requests are synchronous and may take up to a minute.
                # Keep them off the event loop so dashboard/list/WS requests can proceed.
                states = await asyncio.to_thread(
                    fetch_channel_states,
                    host,
                    _cfg.isapi_port,
                    _cfg.isapi_username,
                    _cfg.isapi_password,
                    chs,
                )
                for ch, st in states.items():
                    real_states[(did, ch)] = st
            except Exception:
                logger.debug("查通道真实状态失败: %s (%s)", did, host, exc_info=True)

        if _fallback_used:
            logger.warning(
                "以下设备未登记 IP，摄像头信息暂用默认 ISAPI 地址（%s）：%s。"
                "多台设备时会导致「摄像头显示成同一台」，请补登设备 IP",
                _cfg.isapi_host,
                ", ".join(sorted(_fallback_used)),
            )

    out: list[dict] = []
    for c, online, last_seen, last_alarm_at in rows:
        # ★ 2026-XX：父设备在 device 表里查不到（online 为 NULL）说明这条通道
        #   是历史残留（例如早期测试写入的 last_device_id='d1'）。
        #   以前它会被判成"离线"，运维看到一堆永久离线通道却查不出原因。
        #   现在明确区分：没有父设备 → online=None（前端显示"未知"），
        #   而不是谎报离线。
        has_parent = online is not None
        parent_id = str(c.last_device_id or c.child_dev_id or "")

        # 摄像头真实状态（优先）
        real = real_states.get((parent_id, int(c.channel_id or 0)))

        if not has_parent:
            ch_online: bool | None = None
        elif real is not None and not getattr(real, "error", ""):
            # ★ 用摄像头（通道）自己的在线状态
            ch_online = bool(getattr(real, "online", False))
        elif parent_id and parent_id in sdk_ids:
            # 查不到真实状态时才借用父设备（NVR 在线）
            ch_online = True
        else:
            # 退回原逻辑（标记 + last_seen + 业务活性）
            silence: float | None
            if last_alarm_at is not None:
                silence = max(
                    (utcnow() - last_alarm_at).total_seconds(), 0.0
                )
            else:
                silence = await _latest_business_seconds(parent_id)
            ch_online = _device_online_fresh(
                bool(online), last_seen, silence
            )

        out.append(
            {
                "id": c.id,
                "display_name": c.display_name,
                "channel_name": c.channel_name,
                "channel_no": c.channel_id,
                "workshop_code": c.workshop_code,
                "status": c.status,
                "enabled": c.enabled,
                "online": ch_online,
                "parent_device": parent_id or None,
                "parent_missing": not has_parent,
                "alarm_count": c.alarm_count,
                "last_seen": last_seen,
                "last_alarm_at": last_alarm_at,
                # ★ 摄像头自己的信息（来自 NVR 的 ISAPI）
                "camera_ip": getattr(real, "ip", None) if real else None,
                "camera_model": getattr(real, "model", None) if real else None,
                "camera_serial": getattr(real, "serial", None) if real else None,
                "camera_online_known": bool(
                    real is not None and not getattr(real, "error", "")
                ),
            }
        )
    return out


def _device_online_fresh(
    online: bool | None,
    last_seen,
    business_silence_seconds: float | None = None,
) -> bool:
    """在线判定（list_channel_devices / count_devices 用）。

    ★★ 2026-XX 重要修正：「业务静默」不再单独判离线。

    原逻辑（三层全部要满足）：online 标记 → last_seen 3天 → 业务活性
    其中业务活性用 device_silence_after_minutes（默认 30 分钟）：
      **超过 30 分钟没有新报警就判离线**。

    这在现场是错的 —— 本项目的报警是「有人违规才产生」，
    两次报警间隔几小时甚至几天完全正常。实测后果：
      · 通道 2 号「33 分钟前刚报过警」照样显示离线
      · 一条安静的产线永远显示离线，运维以为设备坏了

    正确口径（现在就按这个）：
      ① SDK 的 online 标记 **是权威**（设备与平台保持 ISUP 连接，
         拔电/断网时 SDK 会回调离线事件，我们也修好了离线 ID 解析）
      ② last_seen 超长兜底（默认 3 天）只防「进程被强杀导致离线事件丢失」
      ③ 业务静默 **只在 online 标记可疑时**才作为辅助证据 ——
         即：标记为在线、但 last_seen 也异常陈旧时才降级；
         单纯的「安静」不再判离线。

    这样「设备连着但今天没报警」显示在线（正确），
    「设备拔电」由 SDK 离线事件处理（也正确）。
    """
    if not online:
        return False

    minutes = get_settings().device_offline_after_minutes
    if minutes > 0:
        if last_seen is None:
            # 没有 last_seen：无法确认，交给业务活性做唯一判据
            if business_silence_seconds is not None and business_silence_seconds >= 0:
                return (
                    business_silence_seconds
                    <= get_settings().device_silence_after_minutes * 60
                )
            return False
        if (utcnow() - last_seen) > timedelta(minutes=minutes):
            return False

    # ★ last_seen 仍在兜底窗口内 → 信任 SDK 标记，不再因「业务安静」判离线。
    #   （business_silence_seconds 保留在参数里，供上层需要时自行参考）
    return True
