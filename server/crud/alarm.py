# -*- coding: utf-8 -*-
"""告警 CRUD。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta

from sqlalchemy import Integer, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.crud.filters import AlarmFilter
from server.crud.pagination import Cursor
from server.crud.scoping import is_denied, visible_in, workshop_scope
from server.models import Alarm, AlarmImage, AlarmStatus, VideoStatus, utcnow


async def find_recent_duplicate(
    db: AsyncSession,
    *,
    device_id: str,
    channel: int,
    event_type: str,
    dedup_seconds: float,
    now: datetime | None = None,
) -> Alarm | None:
    """★ 去重：找出该 (设备, 通道, 事件类型) 在 dedup_seconds 内的最近一条告警。

    实测海康摄像头会**每秒重复上报同一条 IO 报警**（每分钟 60 条），
    不去重的话真正的告警会被瞬间挤出首页，且数据无限膨胀。
    """
    now = now or utcnow()
    since = now - timedelta(seconds=dedup_seconds)

    stmt = (
        select(Alarm)
        .where(
            Alarm.device_id == device_id,
            Alarm.channel == channel,
            Alarm.alarm_time >= since,
        )
        .order_by(Alarm.alarm_time.desc())
        .limit(20)  # 多取几条，再在 Python 里比对 eventType（存在 JSON 里）
    )
    rows = list((await db.execute(stmt)).scalars().all())

    for alarm in rows:
        if not alarm.content_json:
            continue
        try:
            et = (json.loads(alarm.content_json) or {}).get("eventType") or ""
        except (ValueError, TypeError):
            continue
        if et == event_type:
            return alarm
    return None


async def bump_duplicate(
    db: AsyncSession,
    alarm: Alarm,
    *,
    repeat_count: int,
    last_time: datetime,
) -> Alarm:
    """把重复告警的次数累加到已有记录上。

    ★★ 2026-10-29 修复「报警时间被顶掉」（现场：41 分的报警显示成 42 分）

       原实现有这一行：
           alarm.alarm_time = last_time        # ← 用新时间覆盖了原始报警时间

       后果：告警 A 在 09:41:57 产生，同一窗口内又来了 09:42:00 的同类告警，
       合并时把 A 的 alarm_time 改写成 09:42:00 —— 列表按 alarm_time 排序，
       于是「41 分的记录变成了 42 分」，看起来像「新报警把旧的顶了」。
       更糟的是**原始发生时间永久丢失**，事后无法追溯到底几点几分报的。

       正确语义：
         · alarm_time   = **首次发生时间**（不可变，是事实）
         · lastSeenAt   = 最近一次重复时间（可变，放进 content_json）
         · repeatCount  = 累计次数

       所以这里只更新 repeatCount / lastSeenAt，**绝不碰 alarm_time**。
    """
    try:
        c = json.loads(alarm.content_json or "{}") or {}
    except (ValueError, TypeError):
        c = {}
    c["repeatCount"] = repeat_count
    c["lastSeenAt"] = last_time.isoformat()
    alarm.content_json = json.dumps(c, ensure_ascii=False)
    await db.commit()
    await db.refresh(alarm)
    return alarm


async def find_alarm_near_time(
    db: AsyncSession,
    *,
    at: datetime,
    device_id: str = "",
    channel: int | None = None,
    tolerance_seconds: float = 30.0,
) -> Alarm | None:
    """★ 按时间就近找告警（**不限定状态**）。

    为什么需要它：实测发现**图片可能比告警早到**——
    SS 回调 15:37:15.157 到，AMS 回调 15:37:15.176 才入库，**图片早了 19ms**。
    此时 find_correlatable_alarm() 找不到 awaiting_media 的告警，
    图片就变成孤儿。这里放宽为「时间上最接近的那条告警」。

    ★★ 2026-09-21 关键修复：必须按「与 at 的距离」排序，不能按 alarm_time 倒序。
       原实现用 `order_by(Alarm.alarm_time.desc())` —— 取的是窗口内**最新**的告警。
       而设备约每 3 秒上报一次、图片又比告警晚约 3 秒到，于是时序变成：

           T+0s  告警1 入库
           T+3s  告警2 入库；同时「告警1 的图片」到达
                 → 原实现选中「最新的告警2」，把告警1 的图挂到了告警2 上
           T+6s  告警3 入库；同时「告警2 的图片」到达 → 挂到告警3

       结果：每条告警都拿到**上一条**的图，而**最新那条永远没有图**。
       现场表现就是「第一个报警永远没图片，后面来的把它顶掉」。

       正确的语义是「图片属于拍摄时刻最接近的那条告警」，
       所以这里用 SQL 的 ABS(距离) 排序，取真正最近的一条。

    ★ 2026-10-21：当前 correlator 走的是 find_alarm_for_image（「最早的、
      还没配图的」），本函数已无调用点。**保留**，因为：
        · 它记录了一次真实的现场事故（图被挂到相邻告警上）；
        · 若将来改成「就近匹配」策略，这是已验证正确的实现。
      标记为「备用策略」，不要因为没人调用就当垃圾删掉。
    """
    lo = at - timedelta(seconds=tolerance_seconds)
    hi = at + timedelta(seconds=tolerance_seconds)

    conds: list = [Alarm.alarm_time >= lo, Alarm.alarm_time <= hi]
    if device_id:
        conds.append(Alarm.device_id == device_id)
    if channel is not None:
        conds.append(Alarm.channel == channel)

    # ★ 按与 at 的绝对时间距离升序 —— 距离相同则取更早的那条
    #   （图片晚到时，更早的告警才是它真正的归属）
    distance = func.abs(func.julianday(Alarm.alarm_time) - func.julianday(at))
    stmt = (
        select(Alarm)
        .where(*conds)
        .order_by(distance.asc(), Alarm.alarm_time.asc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def count_alarm_images(db: AsyncSession, alarm_id: str) -> int:
    """某条告警当前挂了多少张图。"""
    stmt = select(func.count(AlarmImage.id)).where(AlarmImage.alarm_id == alarm_id)
    return int((await db.execute(stmt)).scalar() or 0)


async def create_alarm(
    db: AsyncSession,
    *,
    device_id: str,
    channel: int,
    alarm_type: int,
    alarm_time: datetime,
    content_raw: str | None,
    content_json: dict | None,
    correlate_window_seconds: float,
    alarm_id: str | None = None,
    workshop: str | None = None,
    workshop_rule: str | None = None,
) -> Alarm:
    """新建一条告警。

    correlate_window_seconds 的含义：
      · > 0：开启聚合窗口，等图片到达再封板（多条告警可共享窗口）
      · = 0：**不做窗口聚合**——每条告警独立，立即视为 complete，
             图片靠「顺序配对」挂上来（2026-09-17 起的默认行为）

    workshop：★ 归属车间。None = 尚未指派 —— 该告警对所有车间账号不可见，
              直到 admin 把对应通道指派给某个车间（默认拒绝，避免串数据）。
    """
    # 窗口为 0 时立即完成，不再等图片；窗口 >0 时才置 awaiting_media
    if correlate_window_seconds > 0:
        initial_status = AlarmStatus.AWAITING_MEDIA.value
        deadline = utcnow() + timedelta(seconds=correlate_window_seconds)
    else:
        initial_status = AlarmStatus.COMPLETE.value
        deadline = None

    alarm = Alarm(
        id=alarm_id or str(uuid.uuid4()),
        device_id=device_id,
        channel=channel,
        alarm_type=alarm_type,
        alarm_time=alarm_time,
        content_raw=content_raw,
        content_json=json.dumps(content_json, ensure_ascii=False) if content_json else None,
        status=initial_status,
        video_status=VideoStatus.NOT_REQUESTED.value,  # ★ 挂起
        correlate_deadline=deadline,
        workshop=workshop,
        workshop_rule=workshop_rule,
    )
    db.add(alarm)
    await db.commit()
    await db.refresh(alarm)
    return alarm


async def get_alarm(db: AsyncSession, alarm_id: str) -> Alarm | None:
    stmt = select(Alarm).where(Alarm.id == alarm_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def find_alarm_for_image(
    db: AsyncSession,
    *,
    device_id: str = "",
    channel: int | None = None,
    captured_at: datetime | None = None,
    tolerance_seconds: float = 300.0,
) -> Alarm | None:
    """★ 给一张图片找归它的告警：**最早的、还没有图的那条**。

    为什么是「最早的」而不是「最新的」：
        实测本设备时序（09-21 数据）——
            告警每 3 秒一条
            图片比对应告警**晚 1~90 秒**才落盘
        于是图片到达时，后面已经积压了好几条新告警。
        若按「最新」找（旧实现），图片会被最新的告警抢走，
        真正属于它的那条老告警**永远等不到图** ——
        现场表现就是「第一个报警永远没图片，被后面来的顶掉」。

    为什么只找「还没有图的」：
        与同事实现一致（他的 SQL 是 `WHERE image_path IS NULL`）。
        一条告警配一张报警图，配满即止 —— 后续图片不再堆积。

    为什么不需要精确时间匹配：
        图片上没有可读的元数据时间（无 EXIF，时间戳烧在画面像素里），
        所以只能按「谁还没图」+ 时间合理性来配。
        用 captured_at 做一次宽松的上界校验即可，不做精确匹配。
    """
    now = captured_at or utcnow()
    lo = now - timedelta(seconds=tolerance_seconds)

    conds: list = [
        # 还没有配图的告警（用 NOT EXISTS 而不是 join，避免重复行）
        ~Alarm.images.any(),
        # 图片不可能属于「未来」的告警；允许图片稍早于告警（实测早到 19ms）
        Alarm.alarm_time <= now + timedelta(seconds=5),
        Alarm.alarm_time >= lo,
    ]
    if device_id:
        conds.append(Alarm.device_id == device_id)
    if channel is not None:
        conds.append(Alarm.channel == channel)

    # ★ 最早的优先 —— 先来的告警先拿图，杜绝「被后面的顶掉」
    stmt = (
        select(Alarm)
        .where(*conds)
        .order_by(Alarm.alarm_time.asc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def find_earliest_unimaged_alarm(
    db: AsyncSession,
    *,
    before: datetime,
    max_lag_seconds: float = 7200.0,
) -> Alarm | None:
    """★ 积压追补用：找「最早的、还没图的」告警（宽松时间校验）。

    与 find_alarm_for_image 的区别：
        那个服务于**实时流**（图片紧随告警 ±120s）；
        这个服务于**断线后的批量补传**（图片可能迟到几分钟到几小时），
        所以时间校验放宽到 max_lag_seconds（默认 2 小时），
        且只要求「告警时间早于图片到达时间」——
        补传流里图片顺序即抓拍顺序，FIFO 一对一回填就是正确语义。

    返回 None 表示没有值得追补的告警（都已有图 / 全部超时）。
    """
    lo = before - timedelta(seconds=max_lag_seconds)
    stmt = (
        select(Alarm)
        .where(
            ~Alarm.images.any(),
            Alarm.alarm_time <= before,
            Alarm.alarm_time >= lo,
        )
        .order_by(Alarm.alarm_time.asc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def find_correlatable_alarm(
    db: AsyncSession,
    *,
    device_id: str,
    channel: int,
    now: datetime | None = None,
) -> Alarm | None:
    """★ 聚合核心：找出该 (设备, 通道) 下仍在等待媒体、且窗口未过期的告警。

    图片到达时调用。多设备场景必须按 (device_id, channel) 过滤，
    否则会串图（docs 风险 R2）。
    """
    now = now or utcnow()
    stmt = (
        select(Alarm)
        .where(
            Alarm.status == AlarmStatus.AWAITING_MEDIA.value,
            Alarm.device_id == device_id,
            Alarm.channel == channel,
            Alarm.correlate_deadline >= now,
        )
        .order_by(Alarm.alarm_time.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def find_any_pending_alarm(
    db: AsyncSession, *, now: datetime | None = None
) -> Alarm | None:
    """降级路径：拿不到 device_id 时，退化为纯时间窗口。

    ⚠️ 仅在单设备场景下可用，多设备会串图。见 docs §3.3。

    ★ 2026-10-21：当前 correlator 已统一走「顺序配对 + 就近匹配」，
      不再有调用点。**保留但标记为降级路径**（单设备现场仍可手工启用），
      不删是因为它表达了一条仍有意义的安全退化策略。
    """
    now = now or utcnow()
    stmt = (
        select(Alarm)
        .where(
            Alarm.status == AlarmStatus.AWAITING_MEDIA.value,
            Alarm.correlate_deadline >= now,
        )
        .order_by(Alarm.alarm_time.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def add_image(
    db: AsyncSession,
    *,
    alarm: Alarm,
    file_hash: str,
    file_path: str,
    source_name: str | None = None,
    width: int | None = None,
    height: int | None = None,
    file_size: int | None = None,
    linked_by: str = "ss",
    alarm_id: str | None = None,
    content_hash: str | None = None,
) -> AlarmImage | None:
    """给告警挂一张图。**按内容哈希去重**，重复的返回 None。

    ⚠️ 实测发现设备会用**不同文件名**上传**完全相同的内容**：
         A2B991EDD81675D8FF8A55FBCFD9BD8E.jpg  (132472 字节)
         7EAFD23A163B7100CCEFEB256E7E0754.jpg  (132472 字节)   ← 内容 sha256 相同
       所以按文件名去重无效，必须按内容哈希去重。

    另外：images 是 selectin 关系，同一 Session 内连续 add_image 时
    alarm 对象上的集合是**陈旧缓存**，依赖它会算错序号。seq 必须从数据库现算。
    """
    alarm_id = alarm_id or alarm.id

    # ★ 内容去重：同一告警下内容相同的图片只保留一张
    if content_hash:
        dup_stmt = select(AlarmImage.id).where(
            AlarmImage.alarm_id == alarm_id,
            AlarmImage.content_hash == content_hash,
        )
        if (await db.execute(dup_stmt)).first() is not None:
            return None

    seq_stmt = select(func.coalesce(func.max(AlarmImage.seq), -1)).where(
        AlarmImage.alarm_id == alarm_id
    )
    # ⚠️ 不能用 `scalar() or -1`：seq 可能是 0，而 0 是 falsy，
    #    会被错误地当成「没有记录」而永远算出 0。必须显式判 None。
    current_max = (await db.execute(seq_stmt)).scalar()
    next_seq = (int(current_max) if current_max is not None else -1) + 1

    img = AlarmImage(
        alarm_id=alarm_id,
        file_hash=file_hash,
        content_hash=content_hash,
        file_path=file_path,
        source_name=source_name,
        seq=next_seq,
        width=width,
        height=height,
        file_size=file_size,
        linked_by=linked_by,
    )
    db.add(img)
    await db.commit()
    await db.refresh(img)
    return img


async def set_alarm_status(db: AsyncSession, alarm: Alarm, status: AlarmStatus) -> None:
    alarm.status = status.value
    if status in (AlarmStatus.COMPLETE, AlarmStatus.EXPIRED):
        alarm.correlate_deadline = None
    await db.commit()


async def set_video_state(
    db: AsyncSession,
    alarm: Alarm,
    *,
    status: VideoStatus,
    url: str | None = None,
    duration: int | None = None,
    provider: str | None = None,
) -> None:
    alarm.video_status = status.value
    if url is not None:
        alarm.video_url = url
    if duration is not None:
        alarm.video_duration = duration
    if provider is not None:
        alarm.video_provider = provider
    await db.commit()


async def list_alarms_offset(
    db: AsyncSession,
    f: AlarmFilter | None = None,
    *,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Alarm], int]:
    """内部 API 用的 offset 分页（前端表格翻页，总量已知更友好）。

    参数：
      · f    —— 全部筛选条件（见 server/crud/filters.py，三态语义在那里说明）
      · page —— 从 1 开始
      · size —— 每页条数

    ★ 原来的 12 个参数已收敛为 3 个。筛选条件集中到 AlarmFilter，
      offset 与 cursor 两种分页共用同一份 to_conditions()，不会各自漂移。
    """
    f = f or AlarmFilter()

    if f.is_denied():
        return [], 0  # 未分配车间 → 什么都看不到

    conds = f.to_conditions()

    total = int(
        (await db.execute(select(func.count(Alarm.id)).where(*conds))).scalar() or 0
    )

    stmt = (
        select(Alarm)
        .where(*conds)
        .order_by(Alarm.alarm_time.desc(), Alarm.id.desc())
        .offset(max(0, (page - 1) * size))
        .limit(size)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    return rows, total


async def list_alarms_page(
    db: AsyncSession,
    f: AlarmFilter | None = None,
    *,
    after: Cursor | None = None,
    limit: int = 50,
    ascending: bool = True,
) -> tuple[list[Alarm], bool]:
    """★ 游标分页的**唯一实现**，open API 用它。返回 (rows, has_more)。

    为什么参数是 `after: Cursor` 而不是 `cursor: str`：
      · 游标的解析与「范围校验后报 400」属于 HTTP 层职责；
      · 这里只负责「把 already-validated 的游标翻译成 SQL 条件」。

    与 offset 分页共用 `AlarmFilter.to_conditions()`，
    所以「加一个筛选条件」不会出现两处分页行为不一致。

    ★ `ascending` 必须显式传：
        内部接口用**降序**（最新在前，前端表格），
        开放 API 用**升序**（甲方从旧到新按天拉，配合游标不会漏）。
      方向不同则游标的比较符必须相反，这是原有的真实差异，
      不能因为「统一」就抹平。
    """
    f = f or AlarmFilter()
    if f.is_denied():
        return [], False

    conds = f.to_conditions()

    if after is not None:
        c_time, c_id = after.alarm_time, after.alarm_id
        if ascending:
            conds.append(
                or_(
                    Alarm.alarm_time > c_time,
                    (Alarm.alarm_time == c_time) & (Alarm.id > c_id),
                )
            )
        else:
            conds.append(
                or_(
                    Alarm.alarm_time < c_time,
                    (Alarm.alarm_time == c_time) & (Alarm.id < c_id),
                )
            )

    if ascending:
        order = (Alarm.alarm_time.asc(), Alarm.id.asc())
    else:
        order = (Alarm.alarm_time.desc(), Alarm.id.desc())

    stmt = (
        select(Alarm)
        .where(*conds)
        .order_by(*order)
        .limit(limit + 1)  # 多取一条用于判断 has_more
    )
    rows = list((await db.execute(stmt)).scalars().all())

    has_more = len(rows) > limit
    return rows[:limit], has_more


async def expire_overdue_alarms(db: AsyncSession, *, now: datetime | None = None) -> list[Alarm]:
    """聚合窗口巡检：把超时未收齐媒体的告警封板。

    返回被处理的告警（调用方据此推送 WS）。
    """
    now = now or utcnow()
    stmt = select(Alarm).where(
        Alarm.status == AlarmStatus.AWAITING_MEDIA.value,
        Alarm.correlate_deadline < now,
    )
    rows = list((await db.execute(stmt)).scalars().all())

    for alarm in rows:
        # 有图就算 complete，没图算 expired。
        # ⚠️ 用 count 查询而不是 alarm.images：后者可能是陈旧缓存。
        count_stmt = select(func.count(AlarmImage.id)).where(
            AlarmImage.alarm_id == alarm.id
        )
        has_image = int((await db.execute(count_stmt)).scalar() or 0) > 0
        alarm.status = (
            AlarmStatus.COMPLETE.value if has_image else AlarmStatus.EXPIRED.value
        )
        alarm.correlate_deadline = None

    if rows:
        await db.commit()
    return rows


async def list_alarms_since(
    db: AsyncSession,
    *,
    since: datetime,
    limit: int = 200,
    device_id: str | None = None,
) -> list[Alarm]:
    """★ 增量拉取：按时间游标取新告警（升序，适合轮询）。"""
    conds = [Alarm.alarm_time > since]
    if device_id:
        conds.append(Alarm.device_id == device_id)

    stmt = (
        select(Alarm)
        .where(*conds)
        .order_by(Alarm.alarm_time.asc(), Alarm.id.asc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())

# ---------------------------------------------------------------------------
# ★ 人工处置
# ---------------------------------------------------------------------------
async def set_handled(
    db: AsyncSession,
    alarm: Alarm,
    *,
    handled: bool,
    by: str | None = None,
) -> Alarm:
    """标记 / 取消标记「已处理」。"""
    alarm.handled = handled
    alarm.handled_at = utcnow() if handled else None
    alarm.handled_by = by if handled else None
    await db.commit()
    await db.refresh(alarm)
    return alarm


async def set_handled_many(
    db: AsyncSession,
    alarm_ids: list[str],
    *,
    handled: bool,
    by: str | None = None,
    workshops: list[str] | None = None,
) -> list[str]:
    """★ 批量标记处理。

    ★ 车间隔离：workshops 传入可见车间列表，越权 ID 静默忽略
      （与批量删除同一策略，不泄露「这条存在但不属于你」）。
    返回实际更新的 id 列表。
    """
    updated: list[str] = []
    for aid in dict.fromkeys(alarm_ids):
        alarm = await get_alarm(db, aid)
        if alarm is None:
            continue
        # 对象级隔离，与列表查询同一口径（crud/scoping.py）
        if not visible_in(getattr(alarm, "workshop", None), workshops):
            continue
        alarm.handled = handled
        alarm.handled_at = utcnow() if handled else None
        alarm.handled_by = by if handled else None
        updated.append(aid)
    if updated:
        await db.commit()
    return updated


async def count_stats(
    db: AsyncSession,
    *,
    today_start: datetime | None = None,
    workshops: list[str] | None = None,
) -> dict:
    """看板统计：今日报警 / 待处理 / 已处理。

    ★ 「待处理」统计的是**全部未处理**，不限今日 —— 昨天没处理的告警
      今天仍然需要处理，只算今日会让红点数说谎。

    ★ workshops：车间隔离。None=不过滤；[]=全空；[...]=只看这些车间。
    """
    if today_start is None:
        now = utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 车间隔离（口径见 crud/scoping.py）
    if is_denied(workshops):
        return {"today": 0, "pending": 0, "handled": 0}
    ws_cond = workshop_scope(Alarm.workshop, workshops)

    today_stmt = select(func.count(Alarm.id)).where(
        Alarm.alarm_time >= today_start, *ws_cond
    )
    pending_stmt = select(func.count(Alarm.id)).where(
        Alarm.handled.is_(False), *ws_cond
    )
    handled_stmt = select(func.count(Alarm.id)).where(
        Alarm.handled.is_(True), *ws_cond
    )

    today = int((await db.execute(today_stmt)).scalar() or 0)
    pending = int((await db.execute(pending_stmt)).scalar() or 0)
    handled = int((await db.execute(handled_stmt)).scalar() or 0)
    return {"today": today, "pending": pending, "handled": handled}


# ---------------------------------------------------------------------------
# ★ 每日趋势（首页看板条形图）
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# ★ 每小时分布（今日 24 小时）—— 看「什么时候在报警」
# ---------------------------------------------------------------------------
async def count_hourly_today(
    db: AsyncSession,
    *,
    today_start: datetime,
    workshops: list[str] | None = None,
) -> list[dict]:
    """今日按小时统计报警数（00~23 共 24 格，无数据补 0）。

    用途：看板的小时分布柱图 —— 一眼看出报警集中在哪个班次/时段，
    比「只有一根 7 天柱」有信息量得多。
    """
    if is_denied(workshops):
        return [{"hour": h, "count": 0} for h in range(24)]

    conds: list = [Alarm.alarm_time >= today_start]
    conds.extend(workshop_scope(Alarm.workshop, workshops))

    # SQLite：strftime('%H', alarm_time) 取小时
    stmt = (
        select(func.strftime("%H", Alarm.alarm_time), func.count(Alarm.id))
        .where(*conds)
        .group_by(func.strftime("%H", Alarm.alarm_time))
    )
    rows = (await db.execute(stmt)).all()
    by_hour = {int(r[0]): int(r[1] or 0) for r in rows if r[0] is not None}
    return [{"hour": h, "count": by_hour.get(h, 0)} for h in range(24)]


# ---------------------------------------------------------------------------
# ★ 处置时效 —— 看「我们处理得够快吗」
# ---------------------------------------------------------------------------
async def count_handle_latency(
    db: AsyncSession,
    *,
    workshops: list[str] | None = None,
) -> dict:
    """今日已处理告警的平均处置时长（分钟）。

    口径：handled_at - alarm_time（都是 naive 本地时间，同一时钟口径）。
    SQLite 用 julianday 差值 * 1440 得到分钟。
    """
    if is_denied(workshops):
        return {"avg_minutes": None, "handled_today": 0}

    now = utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    conds: list = [
        Alarm.handled.is_(True),
        Alarm.handled_at.is_not(None),
        # 只看「今日处理的」，避免历史积压拉偏平均值
        Alarm.handled_at >= today_start,
    ]
    conds.extend(workshop_scope(Alarm.workshop, workshops))

    minutes = (
        func.julianday(Alarm.handled_at) - func.julianday(Alarm.alarm_time)
    ) * 1440.0

    stmt = select(func.avg(minutes), func.count(Alarm.id)).where(*conds)
    row = (await db.execute(stmt)).first()
    avg = row[0] if row else None
    cnt = int(row[1] or 0) if row else 0
    # 负值（时钟回拨/脏数据）按 0 处理，别让看板显示 -3 分钟
    avg_minutes = max(0.0, float(avg)) if avg is not None else None
    return {"avg_minutes": avg_minutes, "handled_today": cnt}


# ---------------------------------------------------------------------------
# ★ 待配对图片队列健康度 —— 串图风险指标
# ---------------------------------------------------------------------------
async def count_pending_health(db: AsyncSession) -> dict:
    """待配对 / 孤儿图片数量（图片与告警配对的健康度）。

    ★ 这是本项目最关键的内部指标：队列积压意味着「图片配不上告警」，
      超过上限会自动停止配对（人工介入）。放到看板上比藏在 admin 接口里好。
    """
    from server.models import PendingImage

    stmt = select(PendingImage.status, func.count(PendingImage.id)).group_by(
        PendingImage.status
    )
    rows = (await db.execute(stmt)).all()
    out = {str(r[0]): int(r[1] or 0) for r in rows}
    return {
        "pending": out.get("pending", 0),
        "matched": out.get("matched", 0),
        "orphan": out.get("orphan", 0),
    }


async def count_unassigned(
    db: AsyncSession,
    *,
    workshops: list[str] | None = None,
) -> int:
    """未指派车间的告警数（workshop 为 NULL）。

    ★ 这类告警对所有车间账号都不可见（默认拒绝），如果一直涨说明
      有人没把通道指派给车间 —— 看板上要提醒，否则数据会「凭空消失」。
    """
    if is_denied(workshops):
        return 0
    stmt = select(func.count(Alarm.id)).where(Alarm.workshop.is_(None))
    return int((await db.execute(stmt)).scalar() or 0)


async def count_workshop_stats(
    db: AsyncSession,
    *,
    workshops: list[str] | None = None,
) -> list[dict]:
    """★ 按车间的报警分布（今日 + 待处理）。

    看板的「车间分布」块用 —— 多车间场景下，管理员扫一眼就知道
    哪条产线在报警、哪条产线有积压没处理。

    workshops: None=全部可见；[]=空；[...]=仅这些车间（隔离口径与列表一致）
    """
    if is_denied(workshops):
        return []

    conds: list = list(workshop_scope(Alarm.workshop, workshops))

    from server.models import Workshop

    # 今日起点（本地 naive，与库内口径一致）
    now = utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    today_stmt = (
        select(Alarm.workshop, func.count(Alarm.id))
        .where(Alarm.alarm_time >= today_start, *conds)
        .group_by(Alarm.workshop)
    )
    pending_stmt = (
        select(Alarm.workshop, func.count(Alarm.id))
        .where(Alarm.handled.is_(False), *conds)
        .group_by(Alarm.workshop)
    )
    today_map = {r[0]: int(r[1] or 0) for r in (await db.execute(today_stmt)).all()}
    pending_map = {r[0]: int(r[1] or 0) for r in (await db.execute(pending_stmt)).all()}

    # 车间名字表（code → name），未指派车间的归到「未指派」
    wrows = (await db.execute(select(Workshop.code, Workshop.name))).all()
    names = {r[0]: r[1] for r in wrows}

    # ★ 各车间的通道数 / 在线数：判断「这个车间没报警」是设备掉线还是真没违规
    from server.models import Channel, Device

    ch_rows = (
        await db.execute(
            select(Channel.workshop_code, Channel.id, Device.online)
            .select_from(Channel)
            .outerjoin(Device, Device.device_id == Channel.last_device_id)
            .where(Channel.enabled.is_(True))
        )
    ).all()
    ch_total: dict[str, int] = {}
    ch_online: dict[str, int] = {}
    for code, _cid, online in ch_rows:
        key = code or ""
        ch_total[key] = ch_total.get(key, 0) + 1
        if online:
            ch_online[key] = ch_online.get(key, 0) + 1

    codes = set(today_map) | set(pending_map)
    out: list[dict] = []
    for code in codes:
        key = code or ""
        out.append(
            {
                "code": key,
                "name": names.get(key, "未指派" if not key else key),
                "today": today_map.get(code, 0),
                "pending": pending_map.get(code, 0),
                "channels": ch_total.get(key, 0),
                "channels_online": ch_online.get(key, 0),
            }
        )
    # 今日报警多的排前面；都为空时按待处理排
    out.sort(key=lambda x: (-x["today"], -x["pending"], x["name"]))
    return out


async def count_workshop_frequency(
    db: AsyncSession,
    *,
    start: datetime,
    end: datetime,
    workshops: list[str] | None = None,
    bucket: str = "hour",
) -> list[dict]:
    """★ 按车间的**报警频率**统计，范围 [start, end)。

    与 count_workshop_stats 的区别：
      · 那个是「今日 / 待处理」快照（看板卡片用）；
      · 这个是**任意时间区间 + 按小时/按天分桶**（看频率、看趋势）。
        频率 = 区间内条数 / 区间小时数，单位「次/小时」，
        多车间横向对比时用它，比裸条数有意义（区间长短不同也能比）。

    ★ 车间隔离：workshops=None 全部；[]=空；[...]=只看这些车间。
      —— 账号只看到自己有权看的车间，这是需求 7 的核心。
    """
    if is_denied(workshops):
        return []

    span_hours = max((end - start).total_seconds() / 3600.0, 1e-9)
    bucket_fmt = "%Y-%m-%d %H" if bucket == "hour" else "%Y-%m-%d"

    conds: list = [Alarm.alarm_time >= start, Alarm.alarm_time < end]
    conds.extend(workshop_scope(Alarm.workshop, workshops))

    total_stmt = (
        select(
            Alarm.workshop,
            func.count(Alarm.id),
            func.sum(func.cast(Alarm.handled, Integer)),
        )
        .where(*conds)
        .group_by(Alarm.workshop)
    )
    totals = {
        r[0]: (int(r[1] or 0), int(r[2] or 0))
        for r in (await db.execute(total_stmt)).all()
    }

    pending_stmt = (
        select(Alarm.workshop, func.count(Alarm.id))
        .where(*conds, Alarm.handled.is_(False))
        .group_by(Alarm.workshop)
    )
    pendings = {
        r[0]: int(r[1] or 0) for r in (await db.execute(pending_stmt)).all()
    }

    bucket_col = func.strftime(bucket_fmt, Alarm.alarm_time)
    series_stmt = (
        select(Alarm.workshop, bucket_col, func.count(Alarm.id))
        .where(*conds)
        .group_by(Alarm.workshop, bucket_col)
        .order_by(bucket_col)
    )
    series: dict[str | None, list[dict]] = {}
    for code, bkt, cnt in (await db.execute(series_stmt)).all():
        if bkt is None:
            continue
        series.setdefault(code, []).append(
            {"bucket": str(bkt), "count": int(cnt or 0)}
        )

    # 车间名 + 通道数（判断「没报警」是设备掉线还是真没违规）
    from server.models import Channel, Device, Workshop

    names = {
        r[0]: r[1]
        for r in (await db.execute(select(Workshop.code, Workshop.name))).all()
    }

    ch_rows = (
        await db.execute(
            select(Channel.workshop_code, Channel.id, Device.online)
            .select_from(Channel)
            .outerjoin(Device, Device.device_id == Channel.last_device_id)
            .where(Channel.enabled.is_(True))
        )
    ).all()
    ch_total: dict[str, int] = {}
    ch_online: dict[str, int] = {}
    # ★ 通道统计也必须过车间隔离 —— 否则「车间账号」会看到别的车间的条目
    #   （total=0 但名字出现），等于泄露了"有哪些车间"。
    #   2026-10-22：这一条漏了，被 test_stats 抓出来。
    visible_codes = set(workshops) if workshops is not None else None
    for code, _cid, online in ch_rows:
        key = code or ""
        if visible_codes is not None and key not in visible_codes:
            continue
        ch_total[key] = ch_total.get(key, 0) + 1
        if online:
            ch_online[key] = ch_online.get(key, 0) + 1

    # ★ 只统计「有数据或有通道」的车间，避免空车间刷屏
    codes = set(totals) | set(series) | set(ch_total)
    out: list[dict] = []
    for code in codes:
        key = code or ""
        total, handled = totals.get(code, (0, 0))
        out.append(
            {
                "code": key,
                "name": names.get(key, "未指派" if not key else key),
                "total": total,
                "per_hour": round(total / span_hours, 3),
                "pending": pendings.get(code, 0),
                "handled": handled,
                "channels": ch_total.get(key, 0),
                "channels_online": ch_online.get(key, 0),
                "series": series.get(code, []),
            }
        )
    out.sort(key=lambda x: (-x["total"], x["name"]))
    return out


async def count_daily_trend(
    db: AsyncSession,
    *,
    start: datetime,
    end: datetime,
    workshops: list[str] | None = None,
) -> list[dict]:
    """按天统计告警数量（含已处理数），范围 [start, end)。

    ★ SQLite 按本地时间直接 group by date(alarm_time)（库里存的就是本地 naive）。
    ★ 没有数据的天也要返回 0 —— 前端条形图不能缺格子。
    """
    conds: list = [Alarm.alarm_time >= start, Alarm.alarm_time < end]
    if is_denied(workshops):
        return []
    conds.extend(workshop_scope(Alarm.workshop, workshops))

    stmt = (
        select(
            func.date(Alarm.alarm_time).label("d"),
            func.count(Alarm.id),
            func.sum(func.cast(Alarm.handled, Integer)),  # true→1
        )
        .where(*conds)
        .group_by(func.date(Alarm.alarm_time))
    )
    by_day = {
        str(r[0]): (int(r[1] or 0), int(r[2] or 0))
        for r in (await db.execute(stmt)).all()
    }

    out: list[dict] = []
    cur = start.date()
    while cur < end.date():
        key = cur.isoformat()
        c, h = by_day.get(key, (0, 0))
        out.append({"date": key, "count": c, "handled": h})
        cur += timedelta(days=1)
    return out


# ---------------------------------------------------------------------------
# ★ 删除
# ---------------------------------------------------------------------------
# ★ 媒体文件路径提取（唯一实现）
#
# 原来 delete_alarm / delete_alarms / purge_old_alarms 各抄了一份几乎
# 一字不差的实现，改一处漏两处。收敛到这里。
# ---------------------------------------------------------------------------
_MEDIA_URL_MARKER = "/media/"


def _media_paths_of(alarm: Alarm) -> list[str]:
    """一条告警关联的所有媒体**相对项目根**的路径。

    · 图片：直接用落库的 file_path（本来就是 storage/... 相对路径）
    · 视频：video_url 可能是 `/media/video/x.mp4`，也可能是绝对 URL
      `http://host/media/video/x.mp4` —— 两种都按 `/media/` 截断，
      统一成 `media/video/x.mp4`。
    """
    paths: list[str] = []
    for img in alarm.images:
        if img.file_path:
            paths.append(img.file_path)
    if alarm.video_url and _MEDIA_URL_MARKER in alarm.video_url:
        tail = alarm.video_url.split(_MEDIA_URL_MARKER, 1)[1]
        paths.append("media/" + tail)
    return paths


async def delete_alarm(db: AsyncSession, alarm_id: str) -> list[str] | None:
    """删除一条告警，返回它关联的媒体相对路径（供调用方删磁盘文件）。

    返回 None 表示告警不存在。

    ★ 先取出文件路径再删行 —— 行删掉后就查不到路径了，
      这正是同事 v3 版本留下孤儿文件的原因。
    """
    alarm = await get_alarm(db, alarm_id)
    if alarm is None:
        return None

    paths = _media_paths_of(alarm)

    await db.delete(alarm)
    await db.commit()
    return paths


async def delete_alarms(db: AsyncSession, alarm_ids: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    """批量删除。返回 (成功删除的 id 列表, {alarm_id: [媒体相对路径]})。

    一次查询把所有文件路径取出来，避免 N+1。
    """
    if not alarm_ids:
        return [], {}

    unique_ids = list(dict.fromkeys(alarm_ids))
    stmt = select(Alarm).where(Alarm.id.in_(unique_ids))
    rows = list((await db.execute(stmt)).scalars().all())
    if not rows:
        return [], {}

    paths_by_alarm: dict[str, list[str]] = {
        alarm.id: _media_paths_of(alarm) for alarm in rows
    }

    found_ids = [a.id for a in rows]
    await db.execute(delete(Alarm).where(Alarm.id.in_(found_ids)))
    await db.commit()
    return found_ids, paths_by_alarm


# ---------------------------------------------------------------------------
# ★ 告警记录保留期清理
# ---------------------------------------------------------------------------
async def purge_old_alarms(
    db: AsyncSession,
    *,
    retention_days: int,
    by: str = "alarm_time",
    batch: int = 2000,
) -> tuple[int, dict[str, list[str]]]:
    """删除超过保留期的告警**记录**（连磁盘媒体文件一起删）。

    为什么要它：box001 是轮询抓拍模式，每 6 秒重复上报，
    关闭去重后每天约 14400 条重复告警 —— 不清理会撑爆数据库。

    返回 (删除条数, {alarm_id: [相对路径]})。
    分批处理，避免一次锁库太久。
    """
    if retention_days <= 0:
        return 0, {}

    col = Alarm.created_at if by == "created_at" else Alarm.alarm_time
    cutoff = utcnow() - timedelta(days=retention_days)

    stmt = select(Alarm).where(col < cutoff).limit(batch)
    rows = list((await db.execute(stmt)).scalars().all())
    if not rows:
        return 0, {}

    paths_by_alarm: dict[str, list[str]] = {
        alarm.id: _media_paths_of(alarm) for alarm in rows
    }

    ids = [a.id for a in rows]
    await db.execute(delete(Alarm).where(Alarm.id.in_(ids)))
    await db.commit()
    return len(ids), paths_by_alarm


# ---------------------------------------------------------------------------
# ★ 事件归并（把「推送条数」还原成「违规次数」）
#
# 背景（2026-10-26 实测定量）：
#   box001 是 AIOP 轮询抓拍模式，同一个人站在镜头前会每 3~4 秒推一条。
#   实测 2026-10-22 一天 4202 条，其中 4188 条挤在 17:11~17:58 这一个小时，
#   相邻两条间隔：1 秒 2702 次、0 秒 1471 次 —— 本质是设备在"刷屏"。
#   今日 43 条实际只对应 9 个事件。
#
# 所以看板不能直接数「条」，要按 (设备, 通道, 事件类型) 做时间窗归并：
#   相邻两条间隔 <= 窗口秒数 → 视为同一次违规，合并成一个事件。
#   窗口默认 120 秒（现场可配），实测能把 5826 条还原成 121 个事件。
# ---------------------------------------------------------------------------
def _consolidate_events(
    rows: list[tuple], window_seconds: int
) -> list[dict]:
    """把按时间升序的 (device_id, channel, alarm_type, alarm_time) 归并成事件。

    返回每个事件的首条时间 + 条数 + 该窗口内最大目标人数。
    纯 Python 实现（数据量在万级，比在 SQLite 里做窗口函数简单可靠）。
    """
    out: list[dict] = []
    last_at: dict[tuple, datetime] = {}
    for device_id, channel, alarm_type, alarm_time in rows:
        key = (device_id, channel, alarm_type)
        prev = last_at.get(key)
        if prev is None or (alarm_time - prev).total_seconds() > window_seconds:
            out.append({"at": alarm_time, "count": 1})
        else:
            out[-1]["count"] += 1
        last_at[key] = alarm_time
    return out


async def count_event_stats(
    db: AsyncSession,
    *,
    start: datetime,
    end: datetime,
    workshops: list[str] | None = None,
    window_seconds: int = 120,
) -> dict:
    """★ 区间内的「事件数 / 条数 / 涉及违规人数」—— 看板的核心口径。

    三个数的区别（现场最容易被混淆的地方）：
      · records  原始推送条数 —— 反映设备推送频率，不是违规次数
      · events   归并后的事件数 —— **真正的"违规发生了几次"**
      · people   涉及违规人次（sum of alarmed_count）—— "卷进了几个人"
      · repeat   冗余倍数 = records / events —— 大于 10 说明设备在刷屏
    """
    if is_denied(workshops):
        return {"events": 0, "records": 0, "people": 0, "repeat_ratio": 0.0}

    conds: list = [Alarm.alarm_time >= start, Alarm.alarm_time < end]
    conds.extend(workshop_scope(Alarm.workshop, workshops))

    stmt = (
        select(Alarm.device_id, Alarm.channel, Alarm.alarm_type, Alarm.alarm_time)
        .where(*conds)
        .order_by(Alarm.alarm_time.asc())
    )
    rows = [tuple(r) for r in (await db.execute(stmt)).all()]
    events = _consolidate_events(rows, window_seconds)
    records = len(rows)

    return {
        "events": len(events),
        "records": records,
        "people": 0,  # 由 count_alarmed_people 补充（需解析 extra）
        "repeat_ratio": round(records / len(events), 1) if events else 0.0,
    }


async def count_alarmed_people(
    db: AsyncSession,
    *,
    start: datetime,
    end: datetime,
    workshops: list[str] | None = None,
    window_seconds: int = 120,
) -> dict:
    """★ 涉及违规人次：按**事件**去重后统计，而不是把每条推送都累加。

    ⚠️ 这里踩过一个坑（2026-10-26 实测）：
       直接把每条 alarm 的 alerted 人数相加，今日 43 条会得到「48 人次」——
       但其中 08:29:23~08:30:39 这 76 秒内的 26 条是**同一个人站在镜头前**
       被轮询反复抓拍（逐条看 targets 全是 1）。累加等于把人复制了 26 份。

       正确口径：先按 (设备, 通道, 事件类型) + window_seconds 归并成事件，
       每个事件内只取**峰值人数**（同时出现在画面里的最多人数）——
       这才是"这次违规卷进了几个人"。

    返回：
      · people           去重后的违规人次（事件内取峰值再求和）
      · events           事件数
      · abnormal_events  含违规的事件数（alarmed > 0 的事件）
      · records          原始条数（便于前端展示"条 / 次"的对比）
    """
    if is_denied(workshops):
        return {"people": 0, "events": 0, "abnormal_events": 0, "records": 0}

    conds: list = [Alarm.alarm_time >= start, Alarm.alarm_time < end]
    conds.extend(workshop_scope(Alarm.workshop, workshops))

    stmt = select(
        Alarm.device_id, Alarm.channel, Alarm.alarm_type, Alarm.alarm_time, Alarm.content_json
    ).where(*conds).order_by(Alarm.alarm_time.asc())
    rows = (await db.execute(stmt)).all()

    # 逐个事件聚合：事件内取人数峰值
    events: list[dict] = []
    last_at: dict[tuple, datetime] = {}
    for device_id, channel, alarm_type, alarm_time, raw in rows:
        key = (device_id, channel, alarm_type)
        prev = last_at.get(key)
        n = 0
        if raw:
            try:
                j = json.loads(raw)
            except (ValueError, TypeError):
                j = {}
            aiop = j.get("AIOPData") or {}
            alerts = (aiop.get("events") or {}).get("alertInfo") or []
            targets = aiop.get("targets") or []
            # 口径与前端 isAbnormal / serialize 保持一致：优先 alertInfo
            n = len(alerts) if alerts else len(targets)
        if prev is None or (alarm_time - prev).total_seconds() > window_seconds:
            events.append({"peak": n})
        else:
            events[-1]["peak"] = max(events[-1]["peak"], n)
        last_at[key] = alarm_time

    people = sum(e["peak"] for e in events if e["peak"] > 0)
    abnormal_events = sum(1 for e in events if e["peak"] > 0)

    return {
        "people": people,
        "events": len(events),
        "abnormal_events": abnormal_events,
        "records": len(rows),
    }


async def count_channel_hotspots(
    db: AsyncSession,
    *,
    start: datetime,
    end: datetime,
    workshops: list[str] | None = None,
    window_seconds: int = 120,
    limit: int = 6,
) -> list[dict]:
    """★ 违规热点排行：按 (设备, 通道) 统计事件数，从多到少。

    比「车间分布」有用得多 —— 车间粒度太粗（整个车间都"有报警"），
    工位粒度才能直接对应到「哪台相机、哪个位置」的管理动作。

    返回：通道名、设备、车间、事件数、占比、环比（可不填）。
    """
    if is_denied(workshops):
        return []

    conds: list = [Alarm.alarm_time >= start, Alarm.alarm_time < end]
    conds.extend(workshop_scope(Alarm.workshop, workshops))

    stmt = (
        select(
            Alarm.device_id,
            Alarm.channel,
            Alarm.workshop,
            Alarm.alarm_type,
            Alarm.alarm_time,
        )
        .where(*conds)
        .order_by(Alarm.alarm_time.asc())
    )
    rows = [tuple(r) for r in (await db.execute(stmt)).all()]

    # 按 (设备, 通道) 归并事件
    per_key: dict[tuple, list] = {}
    for device_id, channel, workshop, alarm_type, alarm_time in rows:
        per_key.setdefault((device_id, channel, workshop), []).append(
            (device_id, channel, alarm_type, alarm_time)
        )

    events_total = 0
    items: list[dict] = []
    for (device_id, channel, workshop), evs in per_key.items():
        consolidated = _consolidate_events(evs, window_seconds)
        n = len(consolidated)
        events_total += n
        items.append(
            {
                "device_id": device_id or "",
                "channel": channel,
                "workshop": workshop or "",
                "events": n,
                "records": len(evs),
                "last_at": evs[-1][3],
            }
        )

    items.sort(key=lambda x: (-x["events"], x["device_id"], x["channel"]))
    items = items[:limit]

    # 补通道显示名（channel 表里有甲方配置的名字）
    from server.models import Channel

    codes = {(i["device_id"], i["channel"]) for i in items}
    ch_rows = (
        await db.execute(
            select(
                Channel.last_device_id,
                Channel.channel_id,
                Channel.display_name,
                Channel.channel_name,
            ).where(Channel.enabled.is_(True))
        )
    ).all()
    names: dict[tuple, str] = {}
    for dev, cid, disp, cname in ch_rows:
        nm = disp or cname or ""
        if nm:
            names[(dev or "", cid)] = nm

    for it in items:
        it["channel_name"] = names.get(
            (it["device_id"], it["channel"]), f"CH{it['channel']}"
        )
        it["share"] = round(it["events"] * 100.0 / events_total, 1) if events_total else 0.0
        it["last_at"] = it["last_at"].isoformat() if it["last_at"] else None

    return items


async def count_data_quality(
    db: AsyncSession,
    *,
    start: datetime,
    end: datetime,
    workshops: list[str] | None = None,
) -> dict:
    """★ 数据可信度：有图率 / 无图条数 / 未指派车间条数。

    为什么看板必须有这一块：
      实测今日 43 条里只有约 12 条配到了图（全局 26.8%）。
      没有抓拍图，值班员就无法判断要不要管 ——
      「有图率」低的时候，前面所有业务指标都不可信，必须亮出来。
    """
    if is_denied(workshops):
        return {
            "total": 0, "with_image": 0, "without_image": 0,
            "with_image_pct": 0.0, "unassigned": 0,
        }

    conds: list = [Alarm.alarm_time >= start, Alarm.alarm_time < end]
    conds.extend(workshop_scope(Alarm.workshop, workshops))

    total = int(
        (await db.execute(select(func.count(Alarm.id)).where(*conds))).scalar() or 0
    )
    with_img = int(
        (
            await db.execute(
                select(func.count(func.distinct(AlarmImage.alarm_id)))
                .select_from(Alarm)
                .join(AlarmImage, AlarmImage.alarm_id == Alarm.id)
                .where(*conds)
            )
        ).scalar()
        or 0
    )
    return {
        "total": total,
        "with_image": with_img,
        "without_image": max(0, total - with_img),
        "with_image_pct": round(with_img * 100.0 / total, 1) if total else 0.0,
        "unassigned": await count_unassigned(db, workshops=workshops),
    }
