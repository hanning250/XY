# -*- coding: utf-8 -*-
"""★ 告警聚合服务（项目的核心难点，见 docs §3）。

ISUP SDK 里，「告警消息 / 图片 / 视频」是三条**完全独立**的回调链路，
SDK 不知道它们属于同一条业务告警。本模块负责把它们「缝合」成一条记录。

三条路径：
  情况 A：告警报文自带图片（NET_EHOME_ALARM_ISAPI_INFO.byPicturesNumber）
          → 同一次回调内直接配对，可靠性 ★★★
  情况 B：图片走 SS 存储回调
          → 时间窗口 + (device_id, channel) 时序关联，可靠性 ★★
  情况 C：拿不到 device_id
          → 纯时间窗降级（仅单设备可用，会串图，不推荐）
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
from datetime import datetime

from server.config import PROJECT_ROOT, get_settings
from server.crud import alarm as alarm_crud
from server.db import SessionLocal
from server.models import AlarmStatus, PendingImage
from sqlalchemy import select
from server.services import media as media_svc
from server.services.alarm_filter import get_filter as get_alarm_filter
from server.services.alarm_parser import parse_alarm_payload
from server.services.bus import EventBus

logger = logging.getLogger(__name__)


class Correlator:
    """聚合器：接收原始事件 → 落库 → 缝合 → 推送到 WS。

    所有耗时操作（解析、IO、DB）都在这里做，**绝不在 SDK 回调线程里做**。
    """

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._settings = get_settings()
        self._filter = get_alarm_filter()
        self._task: asyncio.Task | None = None
        self._sweeper: asyncio.Task | None = None
        self._running = False
        # 用于降低日志噪音（现场设备可能每秒一条告警）
        self._alarm_count = 0
        self._expire_count = 0
        self._expire_logged = 0
        self._dedup_count = 0
        self._filtered_count = 0
        # ★ 回放服务（用于告警后自动抓取 ±30s 视频），由 main.py 注入
        self._playback_service = None
        # ★ 待配对图片已改为**持久化队列**（pending_image 表），
        #   不再用内存 list —— 重启不丢、积压量可监控。
        #   见 server/services/workshop_service.py

    # ---------------------------------------------------------------- 生命周期
    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._consume_loop(), name="correlator-consume")
        self._sweeper = asyncio.create_task(
            self._sweep_loop(), name="correlator-sweep"
        )
        # ★ 启动即跑一次积压追补：把孤儿重置后**立刻**回填，
        #   抢在巡检（5 分钟 TTL 清理）把它们再次标成孤儿之前。
        #   用独立任务，不阻塞启动流程。
        asyncio.create_task(self._startup_backfill(), name="correlator-backfill")
        logger.info("聚合器已启动")

    async def _startup_backfill(self) -> None:
        """启动追补：给孤儿图第二次机会（见 start() 注释）。"""
        await asyncio.sleep(0.5)  # 等 init/清零事务全部提交
        try:
            async with SessionLocal() as db:
                n = await self._backfill_oldest_alarms(db)
                if n:
                    logger.info("启动追补完成：回填 %d 张积压图片", n)
        except Exception:
            logger.exception("启动积压追补失败（不影响正常服务）")

    async def stop(self) -> None:
        self._running = False
        for t in (self._task, self._sweeper):
            if t is not None:
                t.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await t
        logger.info("聚合器已停止")

    # ---------------------------------------------------------------- 消费循环
    async def _consume_loop(self) -> None:
        """从事件队列取原始事件并处理。

        SDK 回调只把字节丢进队列，真正的解析/落库在这里做 ——
        这样既不阻塞 SDK 回调线程，也不违反「回调里不做耗时操作」的约束。
        """
        while self._running:
            try:
                event = await self._bus.get_raw_event()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("从事件队列取数据失败")
                continue

            try:
                await self.handle_event(event)
            except Exception:
                logger.exception("处理事件失败: %s", event.get("kind"))

    async def handle_event(self, event: dict) -> None:
        kind = event.get("kind")
        if kind == "alarm":
            await self.on_alarm(event)
        elif kind == "storage_image":
            await self.on_storage_image(event)
        elif kind == "device":
            await self.on_device(event)
        else:
            logger.warning("未知事件类型: %s", kind)

    # ---------------------------------------------------------------- ⓪ 设备
    async def on_device(self, event: dict) -> None:
        """设备上下线。维护 device 表，供前端展示与告警归属判断。"""
        from server.crud import device as device_crud

        device_id = event.get("device_id") or ""
        online = bool(event.get("online"))
        if not device_id:
            return
        try:
            async with SessionLocal() as db:
                if online:
                    await device_crud.upsert_online(db, device_id=device_id)
                else:
                    await device_crud.mark_offline(db, device_id=device_id)
        except Exception:
            logger.exception("更新设备状态失败: %s", device_id)

    # ---------------------------------------------------------------- ① 告警
    async def on_alarm(self, event: dict) -> None:
        """收到告警消息。

        若报文自带图片（byPicturesNumber > 0），直接在同一事务里挂上，
        状态直接置 complete，无需等时间窗。
        """
        device_id = event.get("device_id") or ""
        # ★ 不再默认成 1：0 表示「SDK 回调未确定通道」，
        #   由下面的报文解析结果来定（报文才是权威来源）。
        channel = int(event.get("channel") or 0)
        alarm_type = int(event.get("alarm_type") or 0)
        alarm_time: datetime = event.get("alarm_time") or datetime.now()
        content_raw = event.get("content_raw")
        content_json = event.get("content_json")
        inline_pics: list[dict] = event.get("inline_pictures") or []

        # ★ 用专门的解析器补齐设备/通道/事件类型（真实报文是 XML）
        parsed = parse_alarm_payload(
            content_raw, alarm_type=alarm_type, device_id_hint=device_id
        )
        if not device_id:
            device_id = parsed.device_id

        # ★★★ 2026-10-26：收到报警时，顺便把设备 IP 补进 device 表。
        #
        #   为什么需要：在线判定原来完全依赖 SDK 的 online 标记，
        #   但 ISUP 的离线事件是「尽力而为」——设备拔电/网络闪断时
        #   未必回调，界面上的"在线"可能长时间是错的。
        #   要主动探测（端口层 / ISAPI）就必须知道设备 IP，
        #   而 device.ip 一直是 NULL：upsert_online 支持传 ip，
        #   但调用方（on_device）从来没传过。
        #
        #   报警报文里恰好带 ipAddress（实测：box001 → 192.168.1.64，
        #   LE5676358 → 192.168.1.102），所以在这里顺手补上。
        #   只在报文有 IP 时写，避免把已有的值覆盖成空。
        if device_id and isinstance(content_json, dict):
            _ip = (content_json.get("ipAddress") or "").strip()
            if _ip:
                try:
                    async with SessionLocal() as _db:
                        from server.models import Device as _Device

                        _dev = await _db.get(_Device, device_id)
                        if _dev is not None and not _dev.ip:
                            _dev.ip = _ip
                            await _db.commit()
                            logger.info(
                                "补登记设备 IP: %s → %s", device_id, _ip
                            )
                except Exception:
                    logger.debug("补登记设备 IP 失败: %s", device_id, exc_info=True)

        # ★★ 通道号解析（BUG 修复，2026-09-23）
        #
        #   旧实现有两个问题，导致「通道 2 的告警被静默记成通道 1」：
        #     ① isup_runtime._extract_alarm_event 只解析 JSON 报文体，
        #        遇到 XML（VMD 等）时 content_json 为 None，于是 channel 落到默认值 1，
        #        并把这个 1 当成「已知值」放进 event["channel"]。
        #     ② 这里用 `if not event.get("channel")` 判断是否需要覆盖 ——
        #        而 1 是 truthy，所以**永远不会**用 parsed.channel 覆盖，
        #        正确的通道号被丢弃。
        #
        #   修复原则：**报文解析出来的值优先**（它来自设备原文，最权威），
        #   事件里的值只作为兜底；并且用 channel_known 区分
        #   「设备明确上报」与「默认值 1」，不再把默认值当成事实。
        if parsed.channel_known:
            channel = parsed.channel
        elif not channel:
            # 两个来源都没给出通道号 → 退回 1（保持历史行为，不可为 0）
            channel = parsed.channel or 1
        # 最终兜底：DB 列是 NOT NULL 且语义上通道号 >= 1
        if channel < 1:
            channel = 1
        if parsed.alarm_time and not event.get("alarm_time_explicit"):
            alarm_time = parsed.alarm_time

        # 结构化字段合并进 content_json，便于前端与 IT 部门直接取用
        structured = dict(content_json or {})
        structured.update(
            {
                "deviceID": device_id,
                "channelID": channel,
                "eventType": parsed.event_type,
                "eventState": parsed.event_state,
                "eventDescription": parsed.event_description,
                "channelName": parsed.channel_name,
                "ipAddress": parsed.ip_address,
                "typeText": parsed.type_text,
                "rawKind": parsed.raw_kind,
            }
        )
        # ★ 归属识别字段（不硬编码任何具体设备，全部来自报文）：
        #   childDevID 每个视频通道唯一，taskID 每个算法任务唯一。
        #   将来做「多车间/多租户」隔离时，用它们建立映射即可，
        #   换设备、加通道都不需要改代码。
        for _key, _val in (
            ("childDevID", parsed.child_dev_id),
            ("taskID", parsed.task_id),
            ("macAddress", parsed.mac_address),
        ):
            if _val:
                structured[_key] = _val
        # ★ AIOP 智能分析告警（未穿防护服等）的业务语义
        if parsed.is_aiop:
            structured["isAiop"] = True
            structured["ruleName"] = parsed.rule_name
            structured["mpName"] = parsed.mp_name
            structured["personCount"] = parsed.person_count
            structured["alarmedCount"] = parsed.alarmed_count
            structured["summary"] = parsed.summary
            structured["aiop"] = parsed.aiop
        if parsed.extra:
            structured["fields"] = parsed.extra

        # ★ 告警过滤：屏蔽无业务含义的噪音设备/事件
        #   （实测 HaiKang-1 每秒重复上报 IO 告警，且不上传图片，会淹没盒子的真告警）
        ignored, reason = self._filter.should_ignore(device_id, parsed.event_type)
        if ignored:
            self._filtered_count += 1
            self._filter.log_once(
                f"filter:{device_id}:{parsed.event_type}",
                f"★ 已过滤告警：{reason}（该类告警不再入库，累计已过滤 "
                f"{self._filtered_count} 条）",
            )
            return

        # ★★ 去重：与同事实现对齐 —— **不做去重**。
        #
        #   同事的做法（src/Backend/main.py + alarm_bridge.py）：
        #       每条 SDK 回调都 enqueue → 每条都 insert_alarm → 每条都 broadcast
        #   即「收到一条就存一条、推一条」，没有任何合并逻辑。
        #
        #   保留下面这段代码是为了可回退：把 ISUP_DEDUP_WINDOW_SECONDS
        #   设为 > 0 即可恢复合并行为。
        #   默认 0 = 关闭去重，完全按同事的方式工作。
        dedup_seconds = self._settings.dedup_window_seconds
        if dedup_seconds > 0 and device_id and parsed.event_type:
            async with SessionLocal() as db:
                dup = await alarm_crud.find_recent_duplicate(
                    db,
                    device_id=device_id,
                    channel=channel,
                    event_type=parsed.event_type,
                    dedup_seconds=dedup_seconds,
                )
                if dup is not None:
                    prev = 1
                    try:
                        prev = int(
                            (json.loads(dup.content_json or "{}") or {}).get(
                                "repeatCount", 1
                            )
                        )
                    except (ValueError, TypeError):
                        pass
                    dup = await alarm_crud.bump_duplicate(
                        db, dup, repeat_count=prev + 1, last_time=alarm_time
                    )
                    self._dedup_count += 1
                    if self._dedup_count == 1:
                        logger.info(
                            "★ 去重生效：%s 的 %s 重复上报，已合并（窗口 %.0fs）",
                            device_id,
                            parsed.type_text,
                            dedup_seconds,
                        )
                    # 合并后不重复推送，避免前端刷屏
                    return

        async with SessionLocal() as db:
            # ★ 车间归属：按 childDevID → taskID → channelID 三级兜底解析。
            #   解析不到就留空（不可见），**绝不塞默认车间** —— 避免串数据。
            #   同时会把没见过的通道登记为「待指派」，供 admin 在界面上分配。
            from server.services import workshop_service as ws_svc

            workshop_code, workshop_rule = await ws_svc.resolve_workshop(
                db,
                child_dev_id=parsed.child_dev_id,
                task_id=parsed.task_id,
                channel_id=parsed.channel if parsed.channel_known else None,
                channel_name=parsed.channel_name,
                device_id=device_id,
                mac=parsed.mac_address,
            )
            if workshop_code is None:
                logger.debug(
                    "告警归属未指派（childDevID=%s ch=%s），暂不可见",
                    parsed.child_dev_id or "-",
                    channel,
                )

            alarm = await alarm_crud.create_alarm(
                db,
                device_id=device_id,
                channel=channel,
                alarm_type=alarm_type,
                alarm_time=alarm_time,
                content_raw=content_raw,
                content_json=structured,
                correlate_window_seconds=self._settings.correlate_window_seconds,
                workshop=workshop_code,
                workshop_rule=workshop_rule,
            )

            # ---- 情况 A：报文自带图片，立即配对 ----
            linked = 0
            for pic in inline_pics:
                data = pic.get("data") or b""
                source_name = pic.get("name") or ""
                file_hash = media_svc.decide_file_hash(source_name, data)
                width, height = media_svc.probe_jpeg_size(data)
                path = media_svc.build_storage_path(
                    file_hash=file_hash, source_name=source_name or f"{file_hash}.jpg"
                )
                try:
                    path.write_bytes(data)
                except OSError:
                    logger.exception("写入告警报文内嵌图片失败: %s", path)
                    continue

                await alarm_crud.add_image(
                    db,
                    alarm=alarm,
                    alarm_id=alarm.id,
                    file_hash=file_hash,
                    file_path=media_svc.relative_to_project(path),
                    source_name=source_name,
                    width=width,
                    height=height,
                    file_size=len(data),
                    linked_by="ams",
                )
                linked += 1

            if linked:
                await alarm_crud.set_alarm_status(db, alarm, AlarmStatus.COMPLETE)
                await db.refresh(alarm)
                logger.info("告警 %s 自带 %d 张图，直接完成", alarm.id, linked)
            else:
                # ★ 顺序配对：从待配对队列头部取最早的一张图配给本条告警。
                #   见 workshop_service 顶部说明：设备与平台是同一根 ISUP 连接，
                #   到达顺序即配对顺序；比纯时间窗匹配可靠得多
                #   （实测两通道告警间隔仅 1~2 秒，时间窗切不开）。
                await self._pair_pending_image(db, alarm)

                # ⚠️ 现场设备可能每秒上报一条告警，逐条 INFO 会淹没日志。
                #    这里降为 DEBUG，只在首次时提示。
                logger.debug(
                    "告警 %s 已入库 device=%s ch=%s type=%s",
                    alarm.id,
                    device_id or "(未知)",
                    channel,
                    parsed.type_text,
                )
                self._alarm_count += 1
                if self._alarm_count == 1:
                    mode = (
                        f"聚合窗口 {self._settings.correlate_window_seconds:.0f}s"
                        if self._settings.correlate_window_seconds > 0
                        else "独立处理（无窗口聚合）"
                    )
                    logger.info(
                        "首条告警已入库，设备上报正常（device=%s ch=%s type=%s，%s）",
                        device_id or "(未知)",
                        channel,
                        parsed.type_text,
                        mode,
                    )
            # ★ 立刻推送（即使还在等图片）—— 前端能看到告警，图片到了会再推一次更新
            await self._publish(alarm)

            # ★ 自动抓取视频片段（甲方要求：前后各 30 秒）
            #
            #   为什么要在告警落库时立刻抓：
            #     甲方 IT 部门是**按天批量拉取**的，拉的时候视频必须已生成好。
            #     如果等他们点了才抓，那天拉取时视频全是空的。
            #
            #   注意：这里只是**入队**，真正的抓取在 worker 线程里做
            #   （设备回放是独占资源，并发限制为 1），不会阻塞告警处理。
            self._maybe_auto_capture_video(alarm)

        # 顺序配对已在上面的 SessionLocal 块内完成（_pair_pending_image），
        # 不再有「内存队列回填」这一步。

    def _maybe_auto_capture_video(self, alarm) -> None:
        """告警落库后自动申请抓取视频片段（非阻塞）。

        三重保护，避免视频任务把设备连接占死：

          ① 开关：video_auto_capture=False 时完全不抓（退回按需模式）
          ② 队列上限：积压超过 video_auto_max_queue 就跳过本次
                      （告警与图片照常，只是这条没有视频）
          ③ 失败静默：抓取失败只记日志，不影响告警本身
        """
        if not getattr(self._settings, "video_auto_capture", True):
            return

        svc = self._playback_service
        if svc is None:
            return

        try:
            # 队列积压保护
            qsize = getattr(svc, "queue_size", None)
            if callable(qsize):
                pending = qsize()
                limit = int(getattr(self._settings, "video_auto_max_queue", 200))
                if pending >= limit:
                    logger.warning(
                        "视频抓取队列积压 %d（上限 %d），跳过本条 alarm=%s",
                        pending,
                        limit,
                        alarm.id[:8],
                    )
                    return
            svc.submit(alarm.id)
        except Exception:
            # 视频是「锦上添花」，绝不能因为它影响告警主流程
            logger.exception("自动申请视频抓取失败 alarm=%s", alarm.id)

    def set_playback_service(self, svc) -> None:
        """注入回放服务（由 main.py 在启动后调用）。"""
        self._playback_service = svc

    async def _pair_pending_image(self, db, alarm) -> None:
        """★ 顺序配对：从待配对队列取**最早**的一张图配给这条告警。

        为什么是「最早」而不是「时间最近」（这是防串图的关键）：

            实测现场：两路通道的告警**每 1~2 秒交替一次**，而图片比告警早到约 11 秒。
            任何时间窗都切不开这两个通道 —— 用「就近匹配」必然串图。

            但设备和平台之间是**同一根 ISUP 连接**，告警与图片的到达顺序
            严格等于设备侧的抓拍顺序，且实测严格一一对应
            （activePostCount=1，一次抓拍一张图）。
            所以**队头配对**才是正确语义，时间只用来做合理性校验。

        保护机制（见 workshop_service.take_oldest_pending）：
            · 积压超上限 → 停止自动配对，转人工
            · 时间差超容忍 → 标记孤儿，不硬配
        """
        from server.services import workshop_service as ws_svc

        existing = await alarm_crud.count_alarm_images(db, alarm.id)
        if existing > 0:
            return

        pending, reason = await ws_svc.take_oldest_pending(
            db, alarm_time=alarm.alarm_time
        )
        if pending is None:
            return

        abs_path = PROJECT_ROOT / pending.file_path
        try:
            data = abs_path.read_bytes()
        except OSError:
            logger.warning("待配对图片文件缺失，标记孤儿: %s", pending.file_path)
            pending.status = "orphan"
            await db.commit()
            return

        width, height = media_svc.probe_jpeg_size(data)
        file_hash = media_svc.decide_file_hash(pending.source_name or "", data)

        await alarm_crud.add_image(
            db,
            alarm=alarm,
            alarm_id=alarm.id,
            file_hash=file_hash,
            content_hash=pending.content_hash,
            file_path=pending.file_path,
            source_name=pending.source_name,
            width=width,
            height=height,
            file_size=pending.file_size or len(data),
            linked_by="ss-seq",
        )
        await ws_svc.mark_matched(db, pending=pending, alarm_id=alarm.id)
        await db.refresh(alarm)

        n = await ws_svc.count_pending(db)
        logger.info(
            "★ 顺序配对：图片 %s → 告警 %s (ch=%s, 队列剩余 %d 张)",
            (pending.source_name or pending.file_path)[:16],
            alarm.id[:8],
            alarm.channel,
            n,
        )

    # ---------------------------------------------------------------- 积压追补
    BACKFILL_MAX_LAG_SECONDS = 7200.0  # 2 小时：比这更迟到的图没有追补价值

    async def _backfill_oldest_alarms(self, db) -> int:
        """★ 积压追补：把队头图片回填给「最早的、还没图的告警」。

        使用场景（与顺序配对互补）：
            服务重启 / 网络抖动 → 设备与旧进程的 SS 会话断开 →
            图片积压在设备侧 → 重连后**批量补传**。
            此时告警早已落库，图片落库时间与告警时间差了几分钟到几小时，
            正常匹配窗口（120s）与顺序配对容忍（90s）都切不中，
            图片只能沦为孤儿。

        配对语义：
            同一根 ISUP 连接，图片补传顺序 = 设备侧抓拍顺序，
            所以按 FIFO「队头图 → 最早没图的告警」一对一回填，
            时间只做宽松校验（告警时间必须早于图片到达，且滞后不超过
            BACKFILL_MAX_LAG_SECONDS）。

        什么时候不会误伤正常流：
            正常时序下图片比告警早到 ~13s 或晚到 1~90s，
            on_storage_image 主路径的 find_alarm_for_image（120s 窗口）
            与告警到达时的 _pair_pending_image（90s 容忍）都能配上，
            根本不会进入「无告警可配」的入队分支 → 本方法不会被触发。
        """
        from server.services import workshop_service as ws_svc

        linked = 0
        while True:
            # 队头图片（最早的一张待配对）
            stmt = (
                select(PendingImage)
                .where(PendingImage.status == "pending")
                .order_by(PendingImage.arrived_at.asc(), PendingImage.id.asc())
                .limit(1)
            )
            pending = (await db.execute(stmt)).scalars().first()
            if pending is None:
                break

            # 最早的、还没有图的告警（不区分设备/通道 —— 补传流里
            # SS 回调本就带不上通道信息，顺序是唯一可用的配对依据）
            alarm = await alarm_crud.find_earliest_unimaged_alarm(
                db,
                before=pending.arrived_at,
                max_lag_seconds=self.BACKFILL_MAX_LAG_SECONDS,
            )
            if alarm is None:
                # 没有可追补的告警（都已有图 / 超出时限）→ 剩余图片留着等新告警
                break

            abs_path = PROJECT_ROOT / pending.file_path
            try:
                data = abs_path.read_bytes()
            except OSError:
                logger.warning(
                    "追补：图片文件缺失，标记孤儿: %s", pending.file_path
                )
                pending.status = "orphan"
                await db.commit()
                continue

            width, height = media_svc.probe_jpeg_size(data)
            file_hash = media_svc.decide_file_hash(
                pending.source_name or "", data
            )

            await alarm_crud.add_image(
                db,
                alarm=alarm,
                alarm_id=alarm.id,
                file_hash=file_hash,
                content_hash=pending.content_hash,
                file_path=pending.file_path,
                source_name=pending.source_name,
                width=width,
                height=height,
                file_size=pending.file_size or len(data),
                linked_by="backfill",
            )
            await ws_svc.mark_matched(db, pending=pending, alarm_id=alarm.id)
            await db.refresh(alarm)
            await alarm_crud.set_alarm_status(db, alarm, AlarmStatus.COMPLETE)
            linked += 1
            logger.info(
                "★ 积压追补：图片 %s → 告警 %s (alarm_time=%s, 迟到 %.0f 分钟)",
                (pending.source_name or pending.file_path)[:16],
                alarm.id[:8],
                alarm.alarm_time,
                (pending.arrived_at - alarm.alarm_time).total_seconds() / 60,
            )

            # 补推一次，前端卡片当场出现缩略图
            await self._publish(alarm)

        if linked:
            remaining = await ws_svc.count_pending(db)
            logger.info(
                "积压追补完成：本轮回填 %d 张，队列剩余 %d 张", linked, remaining
            )
        return linked

    # ---------------------------------------------------------------- ② 图片
    async def on_storage_image(self, event: dict) -> None:
        """收到 SS 存储回调的图片 —— 时序关联到告警上。"""
        data: bytes = event.get("data") or b""
        if not data:
            logger.warning("存储回调收到空图片，忽略")
            return

        source_name = event.get("file_name") or ""
        device_id = event.get("device_id") or ""
        channel = event.get("channel")
        captured_at = event.get("captured_at") or datetime.now()

        # ★ 内容 sha256：设备会用不同文件名重复上传同一张图，必须按内容去重
        content_hash = hashlib.sha256(data).hexdigest()

        file_hash = media_svc.decide_file_hash(source_name, data)
        width, height = media_svc.probe_jpeg_size(data)
        path = media_svc.build_storage_path(
            file_hash=file_hash, source_name=source_name or f"{file_hash}.jpg", when=captured_at
        )
        try:
            path.write_bytes(data)
        except OSError:
            logger.exception("写入告警图片失败: %s", path)
            return

        async with SessionLocal() as db:
            # ★★ 主路径：找「**最早**的、还没有图的那条告警」。
            #
            #   为什么不是「最新的」：
            #     实测本设备告警每 3 秒一条，而图片比对应告警晚 1~90 秒落盘。
            #     图片到达时后面已积压多条新告警 —— 若按「最新」找，
            #     图片会被最新告警抢走，真正属于它的老告警永远没图。
            #     现场表现就是「第一个报警永远没图片，被后面来的顶掉」。
            #
            #   为什么只找「还没有图的」：
            #     与同事实现一致（他的 SQL 是 `WHERE image_path IS NULL`），
            #     一条告警配一张报警图，配满即止 —— 后续图片不再堆积。
            alarm = await alarm_crud.find_alarm_for_image(
                db,
                device_id=device_id,
                channel=int(channel) if channel else None,
                captured_at=captured_at,
                tolerance_seconds=self._settings.image_match_tolerance_seconds,
            )

            if alarm is None and device_id:
                # 降级：设备匹配失败时放宽设备限制（pUser 常为 None）
                alarm = await alarm_crud.find_alarm_for_image(
                    db,
                    captured_at=captured_at,
                    tolerance_seconds=self._settings.image_match_tolerance_seconds,
                )

            # ⚠️ 不要再加「按时间就近」的兜底 —— 那条路径不检查「是否已有图」，
            #    会把图片重复挂到已有图的告警上，破坏「一条告警一张图」的约束。
            #    找不到就进待关联队列，等新告警到达时回填。

            if alarm is None:
                # ★ 没有「还没图的告警」可配 → 持久化入队，等告警到达时配对。
                #
                #   与旧实现的区别：旧的是**内存 list**，服务重启就全丢，
                #   且看不到积压量。现在写 pending_image 表：
                #     · 重启不丢图片
                #     · 积压量可监控（串图风险指标）
                #     · 按 arrived_at 排序 → 支撑「顺序配对」
                from server.services import workshop_service as ws_svc

                # ★ enqueue_image 按内容去重：重复图片返回 None。
                #   此时本文件是**刚落盘的重复副本**，必须删掉 ——
                #   否则轮询抓拍设备每天漏一张孤儿文件，磁盘慢慢被塞满。
                pending_row = await ws_svc.enqueue_image(
                    db,
                    file_path=media_svc.relative_to_project(path),
                    source_name=source_name,
                    content_hash=content_hash,
                    file_size=len(data),
                )
                if pending_row is None:
                    logger.debug("图片内容重复且已在队列中，丢弃新副本: %s", path.name)
                    self._discard_file(path)
                    return
                n = await ws_svc.count_pending(db)
                logger.info(
                    "图片 %s 暂无告警可关联（比告警早到），已入待配对队列（%d 张）",
                    file_hash,
                    n,
                )
                if n > ws_svc.MAX_PENDING:
                    logger.error(
                        "★ 待配对队列积压 %d 张（上限 %d），已暂停自动配对以防串图",
                        n,
                        ws_svc.MAX_PENDING,
                    )
                # ★★★ 积压追补（backfill）：
                #   重启/断线期间图片积压在设备侧，重连后批量补传，
                #   告警可能早已落库且超出了正常匹配窗口 ——
                #   按「最早的没图告警 ← 队头图」FIFO 一对一回填。
                #   正常时序（图片比告警早到十几秒）不会走到这里：
                #   上面 find_alarm_for_image 的 120s 窗口足够覆盖。
                #   时间校验放宽到 BACKFILL_MAX_LAG（2 小时），
                #   超过它的图没有追补价值，留给清理策略。
                await self._backfill_oldest_alarms(db)
                return

            # ★★ 与同事实现对齐：一条告警只认一张图
            #
            #   他的做法（src/Backend/database.py: update_alarm_image_path）：
            #       SELECT id FROM alarms
            #       WHERE image_path IS NULL OR image_path = ''
            #       ORDER BY id DESC LIMIT 1
            #   即「只把图片挂给还没有图的告警」，挂上后该告警不再是候选，
            #   后续图片自然被拒绝。配合他表里 image_path 是单值字段，
            #   物理上一条告警就只能有一张图。
            #
            #   这里等价实现：该告警已有图 → 直接丢弃，不再接收。
            existing = await alarm_crud.count_alarm_images(db, alarm.id)
            if existing > 0:
                logger.info(
                    "告警 %s 已有报警图（%d 张），忽略后续抓拍图 %s",
                    alarm.id,
                    existing,
                    file_hash,
                )
                self._discard_file(path)
                return

            await alarm_crud.add_image(
                db,
                alarm=alarm,
                alarm_id=alarm.id,
                file_hash=file_hash,
                content_hash=content_hash,
                file_path=media_svc.relative_to_project(path),
                source_name=source_name,
                width=width,
                height=height,
                file_size=len(data),
                linked_by="ss",
            )
            await db.refresh(alarm)
            logger.info(
                "图片 %s 已关联到告警 %s (共 %d 张)",
                file_hash,
                alarm.id,
                len(alarm.images),
            )
            # ★ 图片到达后立刻补推一次，前端卡片当场出现缩略图
            await self._publish(alarm)

    # ---------------------------------------------------------------- 巡检
    async def _sweep_loop(self) -> None:
        """定期把聚合窗口超时的告警封板并推送。"""
        interval = self._settings.correlate_sweep_interval
        while self._running:
            await asyncio.sleep(interval)
            try:
                async with SessionLocal() as db:
                    finished = await alarm_crud.expire_overdue_alarms(db)
                    for alarm in finished:
                        await db.refresh(alarm)
                        await self._publish(alarm)
                    if finished:
                        # 同样降低噪音：按批汇总，且只在数量变化时打印
                        self._expire_count += len(finished)
                        self._expire_logged += len(finished)
                        if self._expire_logged >= 20:
                            logger.info(
                                "聚合窗口已封板 %d 条（其中无图片的记为 expired）",
                                self._expire_count,
                            )
                            self._expire_logged = 0
                    # 顺带清理超期未配对的图片（标记孤儿，不再参与自动配对）
                    from server.services import workshop_service as ws_svc

                    await ws_svc.expire_stale_pending(db)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("聚合窗口巡检失败")

    def _discard_file(self, path) -> None:
        """删掉刚落盘但不打算入库的图片，避免留下无引用的孤儿文件。"""
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            logger.warning("删除未使用的图片失败: %s", path)

    async def _publish(self, alarm) -> None:
        """把完整告警推给 WS 订阅者。

        ★ 载荷里带 workshop —— 事件总线据此分房间投递，
          确保 B 车间收不到 A 车间的实时推送。

        ★★ 2026-10-29 修复「车间名闪烁」（现场：一会儿编码一会儿自定义名）：
           alarm_brief() 只填 workshop（code），workshop_name 要调用方补。
           之前这里漏了，于是：
               实时推送（无 name）→ 前端 fallback 显示 code
               轮询列表（有 name）→ 显示自定义名
               又来推送           → 又变回 code
           现在统一补上 workshop_name（带 TTL 缓存的 code→name 解析）。
        """
        from server.db import SessionLocal
        from server.services import workshop_service as ws_svc
        from server.services.serialize import alarm_brief

        payload = alarm_brief(alarm).model_dump(mode="json")
        code = getattr(alarm, "workshop", None)
        payload["workshop"] = code
        # 补全自定义名称；解析失败也要给可用值，绝不能让前端拿到空
        if code:
            try:
                async with SessionLocal() as db:
                    payload["workshop_name"] = await ws_svc.resolve_workshop_name(db, code)
            except Exception:
                logger.warning("补全车间名失败，回退 code=%s", code, exc_info=True)
                payload["workshop_name"] = code
        else:
            payload["workshop_name"] = None

        await self._bus.publish_alarm(payload)
