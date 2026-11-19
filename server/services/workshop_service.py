# -*- coding: utf-8 -*-
"""★ 车间归属与图片配对服务 —— 多车间隔离的核心。

本模块解决两个问题：

一、**告警归属哪个车间**
    报文里有三个可用字段（按可信度）：
        childDevID  → 每路视频通道唯一，换设备也稳定  ★主依据
        taskID      → 每个算法任务唯一                ★次依据
        channelID   → 设备内部通道号                  ★兜底
    用「三级兜底」查 channel 表得到 workshop_code。
    **查不到就标记待指派，绝不猜** —— 猜错就是把 A 车间的报警推给 B 车间。

二、**图片属于哪条告警**（防串图的关键）
    现场约束：单盒子多通道、只能配一个报警主机 → 无法按端口区分图片来源。
    图片走 SS 回调时**不带任何通道信息**，而从告警到图片的时间差约 11 秒，
    两通道告警间隔仅 1~2 秒 —— **纯时间匹配必然串图**。

    实测发现：图片与告警**严格一一对应**（activePostCount=1，一次抓拍一张图）。
    且设备与平台之间是同一根 ISUP 连接，**到达顺序即配对顺序**。
    因此改用 **顺序配对**：

        图片到达 → 入队（按 arrived_at 排序）
        告警到达 → 从队头取最早的一张配对

    并加三重保护，宁可「待确认」也不猜错：
        ① 时间合理性：图片与告警时间差超过阈值 → 不配对
        ② 队列健康度：积压超过上限 → 停止自动配对，转人工
        ③ 内容去重：同内容图片只算一张，避免重复入队把顺序搞乱
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from server.models import Alarm, Channel, PendingImage, Workshop, utcnow

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# ★★ 车间 code → 自定义名称 的内存缓存
#
# 为什么需要它：
#   前端所有告警列表都这么渲染（fallback 到 code）：
#       {{ row.workshop_name || row.workshop }}
#   而 `serialize.alarm_brief()` 是**同步函数**、拿不到数据库连接，
#   所以它只填 workshop（code），workshop_name 由调用方补全。
#
#   结果就是：只有分页列表接口补了名字，**WebSocket 实时推送没补**。
#   于是现场出现典型抖动 ——
#       实时推送（无 name）→ 显示 code
#       轮询列表（有 name）→ 显示自定义名
#       又来一条推送       → 又变回 code
#   看上去像「刷新一次变一次」。
#
#   修法：给所有出告警的路径一个统一的 code→name 解析，
#   用 60 秒 TTL 缓存避免每条推送都查库；改名/新增/删除时主动失效。
# --------------------------------------------------------------------------
_NAME_CACHE: dict[str, str] = {}
_NAME_CACHE_AT: float = 0.0
_NAME_CACHE_TTL: float = 60.0


def invalidate_workshop_name_cache() -> None:
    """车间被新增/改名/删除后调用，让下一次解析重新查库。"""
    global _NAME_CACHE, _NAME_CACHE_AT
    _NAME_CACHE = {}
    _NAME_CACHE_AT = 0.0


async def workshop_name_map(
    db: AsyncSession, *, force: bool = False
) -> dict[str, str]:
    """返回 {code: 自定义名称}。带 TTL 缓存，避免高频推送打库。

    force=True 时强制刷新（改名后立即生效用）。
    """
    global _NAME_CACHE, _NAME_CACHE_AT
    now = time.monotonic()
    if not force and _NAME_CACHE and (now - _NAME_CACHE_AT) < _NAME_CACHE_TTL:
        return _NAME_CACHE
    rows = (await db.execute(select(Workshop.code, Workshop.name))).all()
    _NAME_CACHE = {r[0]: r[1] for r in rows}
    _NAME_CACHE_AT = now
    return _NAME_CACHE


async def resolve_workshop_name(db: AsyncSession, code: str | None) -> str | None:
    """code → 显示名。查不到就回退成 code（与前端 fallback 语义一致）。"""
    if not code:
        return None
    try:
        names = await workshop_name_map(db)
        return names.get(code, code)
    except Exception:
        logger.warning("解析车间名称失败，回退为 code: %s", code, exc_info=True)
        return code

# --------------------------------------------------------------------------
# 配对参数
# --------------------------------------------------------------------------
# 图片与告警「平台到达时间」允许的最大差（秒）。
# 顺序配对必须用同一时钟（服务器 arrived_at / created_at），
# 切勿拿设备上报的 alarm_time —— 盒子时钟偏差常见 1~数分钟，
# 会把本该配上的图误标孤儿（有录像、无图片）。
MATCH_TOLERANCE_SECONDS = 180.0

# 待配对队列的积压上限。超过则认为流已失序，**停止自动配对**转人工，
# 避免「顺序错位后一路错下去」把图全配错。
MAX_PENDING = 60

# 待配对图片的存活时间（秒）。超期标记 orphan，不再参与自动配对。
PENDING_TTL_SECONDS = 300.0

# 归属判定规则名（写入 alarm.workshop_rule，便于排查）
RULE_CHILD = "childDevID"
RULE_TASK = "taskID"
RULE_CHANNEL = "channelID"
RULE_NONE = "unassigned"


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------
# 一、通道登记与车间归属
# --------------------------------------------------------------------------
async def ensure_workshop(
    db: AsyncSession, *, code: str, name: str | None = None
) -> Workshop:
    """确保车间存在（幂等）。"""
    ws = await db.get(Workshop, code)
    if ws is None:
        ws = Workshop(code=code, name=name or code)
        db.add(ws)
        await db.commit()
        await db.refresh(ws)
        # 新车间加入 → 名称缓存失效
        invalidate_workshop_name_cache()
    return ws


async def list_workshops(db: AsyncSession, *, enabled_only: bool = False) -> list[Workshop]:
    stmt = select(Workshop).order_by(Workshop.sort_order.asc(), Workshop.code.asc())
    if enabled_only:
        stmt = stmt.where(Workshop.enabled.is_(True))
    return list((await db.execute(stmt)).scalars().all())


async def find_channel(
    db: AsyncSession,
    *,
    child_dev_id: str = "",
    task_id: str = "",
    channel_id: int | None = None,
    device_id: str = "",
) -> Channel | None:
    """三级兜底查通道登记。

    ## ★★★ 2026-10-26 重排优先级（现场踩坑）

    原顺序：childDevID → taskID → channelID

    问题：**taskID 会跨设备复用**。
    实测现场：NVR 换过摄像头后，新摄像头上报的 taskID 恰好等于
    channel 表里**另一条记录（CH2）**存的 taskID —— 于是一条 CH1 的报警
    被判成「2号车间」（CH2 的车间）。运维看到「设备管理页 CH1 绑 1号车间，
    报警却显示 2号车间」，完全无法理解。

    taskID 是**算法任务 ID**（设备侧配置的检测任务），换设备/重配后
    可能被复用，不具备唯一性。

    新顺序（按可靠性）：

      ① childDevID —— 摄像头唯一哈希，换设备也稳定。**唯一最可信**
      ② channelID + 设备ID —— 同一台 NVR 上通道号唯一且稳定；
         叠加设备约束后不会跨设备撞车
      ③ taskID —— 只在前两级都没有时兜底，且**必须叠加设备约束**

    另外所有匹配都**优先在指定设备范围内找**（device_id 非空时），
    避免跨 NVR 撞车。
    """
    # ---- ① childDevID（最强，全局唯一）----
    if child_dev_id:
        row = (
            await db.execute(
                select(Channel).where(Channel.child_dev_id == child_dev_id)
            )
        ).scalar_one_or_none()
        if row is not None:
            return row

    # ---- ② channelID + 设备（同设备内唯一）----
    if channel_id is not None:
        stmt = select(Channel).where(Channel.channel_id == channel_id)
        if device_id:
            stmt = stmt.where(Channel.last_device_id == device_id)
        row = (await db.execute(stmt.order_by(Channel.id.asc()))).scalars().first()
        if row is not None:
            return row

    # ---- ③ taskID（最弱，可能跨设备复用，必须叠加设备约束）----
    if task_id:
        stmt = select(Channel).where(Channel.task_id == task_id)
        if device_id:
            stmt = stmt.where(Channel.last_device_id == device_id)
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row is not None:
            return row

    return None


async def register_channel(
    db: AsyncSession,
    *,
    child_dev_id: str = "",
    task_id: str = "",
    channel_id: int | None = None,
    channel_name: str = "",
    device_id: str = "",
    mac: str = "",
) -> Channel | None:
    """★ 通道自动发现：收到没登记过的通道就建一条「待指派」记录。

    这是「不锁死设备」的落地点：
      · 换盒子 / 加摄像头 → 系统自动发现，不需要改代码
      · admin 在界面上看缩略图认出是哪个车间 → 点一下分配

    ⚠️ 2026-10-22：三个标识（childDevID / taskID / channelID）**全空时不登记**。

       背景：接入新设备后告警报文解析失败（原文被丢，见 isup_runtime 的修复），
       于是每条告警都拿不到任何标识 → find_channel 永远匹配不到 →
       每条告警插一行空白 channel 记录。实测 4 分钟涨了 289 行，
       管理页出现几百条「待指派」噪声，且这些行**永远无法被指派**
       （没有任何字段可用于匹配），纯属垃圾。

       现在返回 None：调用方（resolve_workshop）把它当「未指派」处理，
       告警照常入库（workshop=None → 不可见），但不再污染通道表。
    """
    if not child_dev_id and not task_id and channel_id is None:
        logger.debug(
            "跳过空白通道登记（childDevID/taskID/channelID 全空，device=%s）",
            device_id or "-",
        )
        return None

    row = await find_channel(
        db,
        child_dev_id=child_dev_id,
        task_id=task_id,
        channel_id=channel_id,
        device_id=device_id,
    )

    now = utcnow()
    if row is None:
        row = Channel(
            child_dev_id=child_dev_id or None,
            task_id=task_id or None,
            channel_id=channel_id,
            channel_name=channel_name or None,
            last_device_id=device_id or None,
            last_mac=mac or None,
            status="unassigned",
            first_seen_at=now,
            last_seen_at=now,
            alarm_count=0,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        logger.info(
            "★ 发现新通道: childDevID=%s taskID=%s channelID=%s（待指派车间）",
            child_dev_id or "-",
            task_id or "-",
            channel_id,
        )
        return row

    # 已存在：补齐缺失字段 + 刷新最近出现时间
    dirty = False
    for attr, val in (
        ("child_dev_id", child_dev_id),
        ("task_id", task_id),
        ("channel_name", channel_name),
        ("last_device_id", device_id),
        ("last_mac", mac),
    ):
        if val and not getattr(row, attr):
            setattr(row, attr, val)
            dirty = True
    if channel_id is not None and row.channel_id != channel_id:
        row.channel_id = channel_id
        dirty = True
    row.last_seen_at = now
    row.alarm_count = (row.alarm_count or 0) + 1
    if dirty:
        await db.commit()
        await db.refresh(row)
    return row


async def resolve_workshop(
    db: AsyncSession,
    *,
    child_dev_id: str = "",
    task_id: str = "",
    channel_id: int | None = None,
    channel_name: str = "",
    device_id: str = "",
    mac: str = "",
    auto_register: bool = True,
) -> tuple[str | None, str]:
    """★ 解析告警归属的车间。

    返回 (workshop_code, rule)。
    workshop_code 为 None 表示**尚未指派** —— 调用方应把它当作
    「不可见」处理，而不是塞进某个默认车间（那会造成串数据）。
    """
    row = await find_channel(
        db,
        child_dev_id=child_dev_id,
        task_id=task_id,
        channel_id=channel_id,
        device_id=device_id,
    )

    if row is None:
        if auto_register:
            await register_channel(
                db,
                child_dev_id=child_dev_id,
                task_id=task_id,
                channel_id=channel_id,
                channel_name=channel_name,
                device_id=device_id,
                mac=mac,
            )
        return None, RULE_NONE

    # 命中规则留痕
    if child_dev_id and row.child_dev_id == child_dev_id:
        rule = RULE_CHILD
    elif task_id and row.task_id == task_id:
        rule = RULE_TASK
    else:
        rule = RULE_CHANNEL

    if not row.enabled or row.status == "disabled":
        return None, RULE_NONE
    if not row.workshop_code:
        # 通道已发现但还没指派车间 → 不可见（不猜）
        return None, RULE_NONE
    return row.workshop_code, rule


async def _channel_alarm_conds(channel: Channel) -> list:
    """★ 构造「这个通道自己的告警」筛选条件。

    ## 2026-10-26 修复串图问题

    原实现把三个条件用 `or_()` 连起来：
        childDevID 匹配  OR  taskID 匹配  OR  Alarm.channel == channel_id

    问题：`Alarm.channel == N` 是**跨设备**的。box001 的 ch1 会命中
    .102 设备的通道 1、以及任何设备的通道 1。实测后果：
      · ch1（5351 条）和 ch2（488 条）**显示了同一张图**
      · 空通道 ch3/ch4/ch5（没接摄像头）也显示出几十条"告警"，
        其实全是别的设备串过来的

    正确口径（与告警归属判定一致）：
      · 有 child_dev_id → 只按它精确匹配（最强，绝不串）
      · 否则有 task_id  → 只按它匹配
      · 都没有          → 才退到 channel_id，但**必须加上设备约束**
        （Alarm.device_id == 该通道的父设备）
    """
    from server.models import Alarm

    # ① 最强标识：childDevID（摄像头的唯一哈希）
    if channel.child_dev_id:
        return [
            Alarm.content_raw.like(f'%"{channel.child_dev_id}"%'),
        ]

    # ② 次强：taskID
    if channel.task_id:
        return [
            Alarm.content_raw.like(f'%"{channel.task_id}"%'),
        ]

    # ③ 最弱：通道号 —— ★ 必须叠加设备，否则跨设备串图
    conds = []
    parent = channel.last_device_id
    if parent:
        conds.append(Alarm.device_id == parent)
    if channel.channel_id is not None:
        conds.append(Alarm.channel == channel.channel_id)
    return conds


async def channel_samples(
    db: AsyncSession, channel: Channel, *, limit: int = 5
) -> list[dict]:
    """★ 取该通道最近几张告警图，用于**人工识别这是哪个车间**。

    为什么需要：系统只能给出 childDevID 这类哈希串，运维无法据此判断
    「这是几号车间」。必须让他**看到画面**才能确认。

    ★ 匹配口径见 _channel_alarm_conds（2026-10-26 修了跨设备串图）。
    """
    conds = await _channel_alarm_conds(channel)
    if not conds:
        return []

    from sqlalchemy import and_

    stmt = (
        select(Alarm)
        .where(and_(*conds))
        .order_by(Alarm.alarm_time.desc())
        .limit(max(1, min(limit, 20)))
    )
    rows = list((await db.execute(stmt)).scalars().all())

    out: list[dict] = []
    for a in rows:
        imgs = sorted(a.images, key=lambda x: x.seq)
        if not imgs:
            continue
        # ★ 存 file_path（storage/...）而不是 /media/ URL ——
        #   交付模式下内部 /media/* 未注册（404），运维拿着 URL 打不开。
        #   调用方按需把 file_path 转成可访问的地址：
        #     · 自用模式 → /media/...（带 token）
        #     · 交付模式 → /openapi/v1/media/...（免鉴权）
        out.append(
            {
                "file_path": imgs[0].file_path,
                "alarm_time": a.alarm_time,
                "type_text": _short_type(a),
            }
        )
    return out


def sample_open_url(file_path: str) -> str | None:
    """把样本图的 file_path 转成**交付模式下能直接打开**的 URL。

    交付模式（enable_internal_api=false）里内部 /media/* 是 404，
    所以这里统一给免鉴权的开放路径 /openapi/v1/media/...。
    """
    if not file_path:
        return None
    p = str(file_path).replace("\\", "/").lstrip("/")
    if p.startswith("storage/"):
        p = p[len("storage/"):]
    from server.config import get_settings

    return f"{get_settings().public_base_url.rstrip('/')}/openapi/v1/media/{p}"


def _short_type(alarm: Alarm) -> str:
    """从 content_json 里取可读的类型文本（取不到就留空）。"""
    import json as _json

    try:
        c = _json.loads(alarm.content_json or "{}") or {}
    except (ValueError, TypeError):
        return ""
    return str(c.get("typeText") or "")


async def channel_identify_info(db: AsyncSession, channel: Channel) -> dict:
    """汇总某通道的「识别信息」：最近告警时间、总数、样本图。

    ★ 2026-10-26：改用 _channel_alarm_conds（and_ 而非 or_），
      修掉「同一张图挂到多个通道」「空通道显示几十条告警」的问题。
    """
    conds = await _channel_alarm_conds(channel)

    if not conds:
        return {
            "last_alarm_at": None,
            "last_alarm_count": 0,
            "sample_image_url": None,
            "sample_image_count": 0,
        }

    from sqlalchemy import and_, func

    total = int(
        (
            await db.execute(
                select(func.count(Alarm.id)).where(and_(*conds))
            )
        ).scalar()
        or 0
    )
    last_dt = (
        await db.execute(select(func.max(Alarm.alarm_time)).where(and_(*conds)))
    ).scalar()

    samples = await channel_samples(db, channel, limit=5)
    # 样本图给两个形式：
    #   file_path   → 权威落盘路径（CLI / 排查用）
    #   open_url    → 交付模式下能直接在浏览器打开的免鉴权地址
    first = samples[0] if samples else None
    return {
        "last_alarm_at": last_dt,
        "last_alarm_count": total,
        "sample_file_path": first["file_path"] if first else None,
        "sample_image_url": sample_open_url(first["file_path"]) if first else None,
        "sample_image_count": len(samples),
    }


async def assign_channel(
    db: AsyncSession, *, channel_pk: int, workshop_code: str, display_name: str = ""
) -> Channel | None:
    """把通道指派给车间，并**回填历史告警**。"""
    row = await db.get(Channel, channel_pk)
    if row is None:
        return None

    row.workshop_code = workshop_code or None
    row.status = "assigned" if workshop_code else "unassigned"
    if display_name:
        row.display_name = display_name
    await db.commit()
    await db.refresh(row)

    # ★ 回填历史告警：该通道之前的告警一并归到该车间
    if workshop_code:
        n = await backfill_alarms_for_channel(db, row)
        logger.info(
            "通道 %s 已指派给车间 %s，回填历史告警 %d 条",
            row.child_dev_id or row.channel_id,
            workshop_code,
            n,
        )
    return row


async def backfill_alarms_for_channel(db: AsyncSession, row: Channel) -> int:
    """把某通道名下的历史告警回填 workshop。

    按 childDevID / taskID / channelID 匹配 content_json 里的原始报文。
    """
    if not row.workshop_code:
        return 0

    from sqlalchemy import or_, text as sa_text

    conds = []
    if row.child_dev_id:
        conds.append(Alarm.content_raw.like(f'%"{row.child_dev_id}"%'))
    if row.task_id:
        conds.append(Alarm.content_raw.like(f'%"{row.task_id}"%'))
    if row.channel_id is not None:
        conds.append(Alarm.channel == row.channel_id)
    if not conds:
        return 0

    stmt = select(Alarm).where(or_(*conds), Alarm.workshop.is_(None))
    rows = list((await db.execute(stmt)).scalars().all())
    for a in rows:
        a.workshop = row.workshop_code
        a.workshop_rule = "backfill"
    if rows:
        await db.commit()
    return len(rows)


async def list_channels(db: AsyncSession, *, status: str | None = None) -> list[Channel]:
    stmt = select(Channel).order_by(Channel.id.asc())
    if status:
        stmt = stmt.where(Channel.status == status)
    return list((await db.execute(stmt)).scalars().all())


# --------------------------------------------------------------------------
# 二、图片顺序配对
# --------------------------------------------------------------------------
async def enqueue_image(
    db: AsyncSession,
    *,
    file_path: str,
    source_name: str = "",
    content_hash: str | None = None,
    file_size: int | None = None,
) -> PendingImage | None:
    """图片入待配对队列。

    ★ 按内容去重：实测设备会用不同文件名上传**完全相同的内容**
      （两路通道同时抓拍、或重复上报）。若不在这里去重，
      队列会被重复项撑大，顺序配对的「一对一」前提就破坏了。
    """
    if content_hash:
        dup = (
            await db.execute(
                select(PendingImage.id).where(
                    PendingImage.content_hash == content_hash,
                    PendingImage.status == "pending",
                )
            )
        ).first()
        if dup is not None:
            logger.debug("图片内容重复，不入队: %s", source_name)
            return None

    row = PendingImage(
        file_path=file_path,
        source_name=source_name or None,
        content_hash=content_hash,
        file_size=file_size,
        arrived_at=utcnow(),
        status="pending",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def count_pending(db: AsyncSession) -> int:
    return int(
        (
            await db.execute(
                select(func.count(PendingImage.id)).where(
                    PendingImage.status == "pending"
                )
            )
        ).scalar()
        or 0
    )


async def take_oldest_pending(
    db: AsyncSession,
    *,
    reference_time: datetime | None = None,
    alarm_time: datetime | None = None,
) -> tuple[PendingImage | None, str]:
    """★ 从队列头取最早的一张图片配对。

    返回 (图片, 结果说明)。图片为 None 表示无可配对。

    reference_time：优先传告警的 **平台入库时间 created_at**（与图片 arrived_at
    同一时钟）。历史调用若仍传 alarm_time=，会当作 reference 兼容。

    三重保护：
      ① 积压超过 MAX_PENDING → 返回 'overflow'，**不配对**，转人工
      ② 时间差超过 MATCH_TOLERANCE_SECONDS → 丢弃过期的，继续找
      ③ 只有完全在容忍范围内的才配对
    """
    ref = reference_time if reference_time is not None else alarm_time
    if ref is None:
        return None, "empty"

    pending_count = await count_pending(db)
    if pending_count > MAX_PENDING:
        logger.error(
            "★ 待配对图片积压 %d 张（上限 %d），已暂停自动配对以防串图，请人工处理",
            pending_count,
            MAX_PENDING,
        )
        return None, "overflow"

    stmt = (
        select(PendingImage)
        .where(PendingImage.status == "pending")
        .order_by(PendingImage.arrived_at.asc(), PendingImage.id.asc())
        .limit(1)
    )
    row = (await db.execute(stmt)).scalars().first()
    if row is None:
        return None, "empty"

    # 时间合理性校验（两边都是平台时钟）
    delta = abs((ref - row.arrived_at).total_seconds())
    if delta > MATCH_TOLERANCE_SECONDS:
        # 这张图太旧/太新，与当前告警无关 → 标记孤儿，继续尝试下一张
        row.status = "orphan"
        await db.commit()
        logger.warning(
            "图片 %s 与告警到达时间差 %.1fs 超出容忍 %.0fs，标记为孤儿",
            row.source_name,
            delta,
            MATCH_TOLERANCE_SECONDS,
        )
        return await take_oldest_pending(db, reference_time=ref)

    return row, "ok"


async def mark_matched(
    db: AsyncSession, *, pending: PendingImage, alarm_id: str
) -> None:
    pending.status = "matched"
    pending.matched_alarm_id = alarm_id
    pending.matched_at = utcnow()
    await db.commit()


async def reset_recent_orphans(
    db: AsyncSession, *, within_minutes: int = 120
) -> int:
    """★ 服务启动时把近期的孤儿图片重置回待配对队列（积压追补自愈）。

    场景：后端重启期间，设备与旧进程的 SS 会话断开，图片积压在设备侧；
    重连后设备把积压图一次补传，此时如果告警已经落库（或已过期），
    这些图会超时成为孤儿。重启后给它们一次重新配对的机会。

    · 只处理 within_minutes 内的孤儿（更老的没有追补价值，图片也过期了）
    · 只重置 status='orphan' 且 matched_alarm_id 为空的（真孤儿）
    返回重置数量。
    """
    cutoff = utcnow() - timedelta(minutes=within_minutes)
    result = await db.execute(
        update(PendingImage)
        .where(
            PendingImage.status == "orphan",
            PendingImage.matched_alarm_id.is_(None),
            PendingImage.arrived_at >= cutoff,
        )
        .values(status="pending")
    )
    await db.commit()
    n = int(result.rowcount or 0)
    if n:
        logger.info("积压追补：%d 张近期孤儿图片已重新入队等待配对", n)
    return n


async def expire_stale_pending(db: AsyncSession) -> int:
    """把超期未配对的图片标记为孤儿（由清理循环周期调用）。"""
    cutoff = utcnow() - timedelta(seconds=PENDING_TTL_SECONDS)
    rows = list(
        (
            await db.execute(
                select(PendingImage).where(
                    PendingImage.status == "pending",
                    PendingImage.arrived_at < cutoff,
                )
            )
        ).scalars().all()
    )
    for r in rows:
        r.status = "orphan"
    if rows:
        await db.commit()
        logger.info("清理超期待配对图片 %d 张", len(rows))
    return len(rows)


async def pending_stats(db: AsyncSession) -> dict:
    """队列健康度 —— 串图风险的监控指标。"""
    rows = (
        await db.execute(
            select(PendingImage.status, func.count(PendingImage.id)).group_by(
                PendingImage.status
            )
        )
    ).all()
    out = {k: int(v) for k, v in rows}
    out["pending"] = out.get("pending", 0)
    out["overflow"] = out["pending"] > MAX_PENDING
    return out
