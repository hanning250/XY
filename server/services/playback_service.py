# -*- coding: utf-8 -*-
"""★ SMS 现场回放 Provider —— 直接从设备抓取告警时间段的录像。

来源：移植自同事 XY-development v3 的 playback_service.py，
      但**适配到本项目架构**：
        · 同事是自己一套 sqlite3 + 自己的表；这里改为复用本项目的
          Alarm / VideoSession 模型与会话机制
        · 同事用全局 _busy 标志串行化；这里改成**每告警一个任务 + 有界队列**，
          避免「第二条告警被永久标记为 failed」
        · 同事删告警时不清理磁盘文件；这里所有失败/超时路径都清理产物

★ 为什么需要它
    设备的录像存在设备本地（NVR/SD 卡）。要拿到「告警发生那 1 分钟」的画面，
    必须通过 SMS SDK 的按时间回放把码流拉下来。拉下来的是 MPEG-PS，
    浏览器播不了，需要 ffmpeg 转成 MP4。

★ 关键经验
    告警取证只要画面：转码一律 -an 丢弃音轨。
    设备 PS 音轨（pcm_alaw / 损坏 mp2）曾导致整段 Conversion failed。
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import queue
import shutil
import subprocess
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from server.config import MEDIA_VIDEO_DIR, PROJECT_ROOT, get_settings

logger = logging.getLogger(__name__)

# 抓取用的原始 PS 流放这里，转码成功后即删
RAW_DIR = PROJECT_ROOT / "data" / "playback_raw"

# ffmpeg 转码超时（秒）
TRANSCODE_TIMEOUT_SECONDS = 120

# 同时允许几个抓取任务并行。
#
# ★★★ 2026-10-24 实测结论：**设备只支持 1 路并发回放**。
#
#   ── 测试方法 ──
#   scripts/test_concurrent_by_alarm.py
#     1. 先从数据库取报警时刻，逐个试回放，找到**确实有录像**的窗口
#        → probe.mpegps = 16.0 秒 / 5879 KB（证明该时段录像完整）
#     2. 用**同一个窗口**开 3 路并发
#        → lane0 = 1.1 秒 (7%)   被踢
#        → lane1 = 0.4 秒 (2%)   被踢
#        → lane2 = 16.0 秒 (100%) 只有最后一路完整
#
#   这是典型的「后开踢前开」：每开一个新回放会话，
#   设备就把前面那个切掉。box001 / .102 都是海康 NVR，此限制相同。
#
#   ── 对容量的影响 ──
#     1 路回放 = 每分钟约 0.9 段（单段占用约 65 秒：等15 + 码流35 + 转码10）
#     3 台摄像头需求 = 3 段/分钟（每台每分钟 1 段，合并后）
#     → **差约 3.3 倍，物理上不可能满足**
#
#   ── ★ 2026-10-28 改为并发 3 ──
#
#     上面那段限制说的是 **SDK 回放**（NET_ECMS_StartPlayBack），
#     实测确实「后开踢前开」。但现在走的是 **ISAPI HTTP 下载**
#     （video_use_isapi=True），是完全不同的路径，不受那个限制。
#
#     实测（同通道不同时段并发，模拟多摄像头）：
#       单段        下载 25.2s + remux 1.0s = 26.2s（44.9 MB）
#       串行 3 段   75.6s（25.2 × 3，完全线性）
#       并发 3 段   50.8s（加速 1.49x）
#         → 段1 27.3s / 段2 26.9s / 段3 50.8s
#         → 前 2 路完全并行，第 3 路因带宽/设备限流慢一倍
#
#     为什么必须从 1 改成 3：
#       高峰 3 摄像头 × 每分钟 1 段 × 10 分钟 = 30 段
#       串行只能做 600/26 = 23 段 → 峰值永远积压 7 段
#       并发 3 实测加速 1.49x → 约 34 段，够用
#
#     ⚠️ 若将来换回 SDK 回放（video_use_isapi=False），必须改回 1，
#        否则会互相踢产生残缺视频。
_MAX_CONCURRENT = 3

# ★ 等设备上线的窗口（秒）：覆盖「服务重启后 SDK 重新监听、设备重连注册」
#   这段空窗实测约 6~10 秒。用户在这期间点「获取视频」不该直接失败。
_DEVICE_WAIT_SECONDS = 12.0


def _get_ffmpeg() -> str:
    """取 ffmpeg 可执行文件路径。

    优先系统 PATH 中的 ffmpeg（Docker / 本机安装）；
    若未安装，再尝试可选的 imageio-ffmpeg 便携包。
    """
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise RuntimeError(
            "未找到 ffmpeg。请安装系统 ffmpeg，或可选 pip install imageio-ffmpeg。"
        ) from exc


def _probe_stream_codecs(path: Path) -> tuple[str | None, str | None]:
    """用 ffmpeg 探测输入文件的视频/音频编码名（如 h264 / hevc / aac）。

    返回 (video_codec, audio_codec)，取不到的为 None。

    ★ 为什么需要（2026-10-23 现场问题）：
       海康设备录像输出 **HEVC/H.265**，而 Chrome/Edge 原生 <video>
       不支持 HEVC。原来转码用 `-c:v copy` 只换容器不换编码，
       产出的 MP4 前端**播不了**（提示"没有找到支持的视频格式"）。
       所以必须先探测编码，HEVC 就重编码成 H.264。

    ★ 为什么用 ffmpeg 而不是纯 Python 解析：
       输入可能是 PS 流（没有 MP4 box），统一交给 ffmpeg 最稳。
       探测失败不阻塞主流程（返回 None，调用方走保守路径重编码）。
    """
    import re

    try:
        ffmpeg = _get_ffmpeg()
    except Exception:
        return None, None

    try:
        result = subprocess.run(
            [
                ffmpeg,
                "-analyzeduration", "10M",
                "-probesize", "10M",
                "-i", str(path),
                "-hide_banner",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except Exception:
        logger.debug("探测编码失败（忽略，走保守转码路径）: %s", path, exc_info=True)
        return None, None

    text = result.stderr or ""
    video_codec = audio_codec = None
    # 形如：Stream #0:0[0x1](und): Video: hevc (Main) (hev1), yuv420p...
    #      Stream #0:1[0x2](und): Audio: aac (LC) (mp4a / 0x6134706D), ...
    for m in re.finditer(r"Stream #\d+:\d+.*?:\s*(\w+):\s*(\w+)", text):
        kind, codec = m.group(1).lower(), m.group(2).lower()
        if kind == "video" and video_codec is None:
            video_codec = codec
        elif kind == "audio" and audio_codec is None:
            audio_codec = codec
    return video_codec, audio_codec


def transcode_ps_to_mp4(ps_path: Path, mp4_path: Path) -> None:
    """MPEG-PS → MP4（仅视频，丢弃音轨）。

    ★ 告警取证只要画面；设备 PS 音轨常损坏（mp2 Header missing），
      转 AAC 会整段 Conversion failed。直接 -an，避免踩坑、也更快。
      视频 H.264 则 copy；HEVC 则重编码为 H.264。+faststart 方便边下边播。
    """
    ffmpeg = _get_ffmpeg()
    video_codec, _audio_codec = _probe_stream_codecs(ps_path)

    if video_codec == "h264":
        v_args = ["-c:v", "copy"]
        logger.info("视频轨已是 H.264，直接拷贝（无音频）: %s", ps_path.name)
    else:
        # ★★ 2026-10-23 现场修复：设备输出 HEVC/H.265，Chrome 原生不支持，
        #    必须重编码为 H.264（原来 -c:v copy 产出的 MP4 前端播不了）。
        logger.info(
            "视频轨 %s 浏览器不支持，重编码为 H.264（无音频）: %s",
            video_codec or "unknown",
            ps_path.name,
        )
        v_args = [
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-pix_fmt", "yuv420p",
            "-vf", "scale='min(960,iw)':-2",
            "-threads", "4",
        ]

    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-analyzeduration", "10M",
            "-probesize", "10M",
            "-i", str(ps_path),
            "-map", "0:v:0?",
            *v_args,
            "-an",
            "-movflags", "+faststart",
            "-f", "mp4",
            str(mp4_path),
        ],
        capture_output=True,
        text=True,
        timeout=TRANSCODE_TIMEOUT_SECONDS,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown error").strip()
        tail = detail[-800:]
        if "matches no streams" in detail or "does not contain any stream" in detail:
            raise RuntimeError("该时段录像没有视频轨（可能只有音频或为空）")
        raise RuntimeError(tail)


def _file_has_data(path: Path) -> bool:
    """文件存在且非空。★ 用 try 包住：文件可能刚被清理策略删掉。"""
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def probe_duration_seconds(path: Path) -> int | None:
    """用 ffprobe 读 MP4 时长（秒）。失败返回 None（不影响主流程）。

    ★ 为什么要它：甲方拿到的每条告警都带 video_duration，
      可以据此确认片段确实是「告警前后各 30 秒」（约 60 秒），
      而不必先下载完整个文件。
    """
    import re

    try:
        ffmpeg = _get_ffmpeg()
        result = subprocess.run(
            [ffmpeg, "-i", str(path), "-hide_banner"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr or "")
        if not m:
            return None
        h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
        return int(round(h * 3600 + mi * 60 + s))
    except Exception:
        logger.debug("探测视频时长失败: %s", path, exc_info=True)
        return None


def parse_alarm_time(value: str) -> datetime:
    """解析告警时间为东八区 naive，供 ISAPI/SDK 按设备 OSD 时间取流。

    不能用 datetime.astimezone()（跟操作系统时区走）。本机是 UTC 时，
    15:00+08:00 会被收成 07:00，录像就抓到早上。
    """
    from server.services.timeutil import parse_any

    text = (value or "").strip()
    if not text:
        raise ValueError("告警时间为空")
    dt = parse_any(text)
    if dt is None:
        raise ValueError(f"无法解析告警时间: {value!r}")
    return dt


class PlaybackService:
    """按需抓取告警回放。

    使用方式：
        svc = PlaybackService()
        svc.start()
        await svc.capture(alarm_id, device_id, channel, alarm_time, on_done=...)
    """

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: queue.Queue[str] = queue.Queue()
        self._workers: list[threading.Thread] = []
        self._running = False
        # ★ 每告警独立状态：替代同事的全局 _busy，
        #   否则第二条告警会被误判为失败且永不重试
        self._active: set[str] = set()
        self._cancelled: set[str] = set()
        self._active_lock = threading.Lock()
        self._settings = get_settings()
        # ★ 失败冷却表：{alarm_id: 失败时刻}（防反复重试导致 SDK 句柄泄漏）
        self._failures: dict[str, float] = {}
        # ★★ 片段合并登记表（2026-10-23）：
        #   key = (device_id, channel, 自然分钟)
        #   value = {owner, min_t, max_t, alarms[]}
        #   同一分钟同通道只由 owner 抓一次，其余报警登记为 peer 等共享视频。
        #   见 _register_in_plan 与 services/fragment_planner.py
        self._plan_acc: dict[tuple[str, int, datetime], dict] = {}
        self._window_lock = threading.Lock()

    # ------------------------------------------------------------ 生命周期
    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def _cleanup_stale_starting(self) -> None:
        """把超时仍停在 starting 的告警标记为 failed。

        为什么要：进程重启会丢 worker 里的任务，数据库状态却留在 starting。
        甲方接口对此返回 425（请稍后重试），但永远不会好 ——
        对方会一直重试到放弃，还以为是网络问题。

        超时阈值 30 分钟：单段视频最长约 3 分钟，留 10 倍余量。
        """
        loop = self._loop

        async def _do() -> None:
            from datetime import datetime, timedelta

            from sqlalchemy import select

            from server.db import SessionLocal
            from server.models import Alarm

            cutoff = datetime.now() - timedelta(minutes=30)
            async with SessionLocal() as db:
                rows = list(
                    (
                        await db.execute(
                            select(Alarm).where(
                                Alarm.video_status == "starting",
                                Alarm.alarm_time < cutoff,
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                if not rows:
                    return
                for a in rows:
                    a.video_status = "failed"
                    a.video_error = (
                        "抓取任务中断（服务重启或设备异常），已清理僵尸状态"
                    )
                await db.commit()
                logger.warning(
                    "★ 清理僵尸 starting：%d 条标记为 failed（最早 %s）",
                    len(rows),
                    rows[0].alarm_time.strftime("%m-%d %H:%M"),
                )

        try:
            if loop is not None and not loop.is_closed():
                asyncio.run_coroutine_threadsafe(_do(), loop)
            else:
                logger.debug("事件循环不可用，跳过僵尸 starting 清理")
        except Exception:
            logger.exception("清理僵尸 starting 出错（不影响主流程）")

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        MEDIA_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
        for i in range(_MAX_CONCURRENT):
            t = threading.Thread(
                target=self._worker, name=f"playback-worker-{i}", daemon=True
            )
            t.start()
            self._workers.append(t)
        logger.info("回放服务已启动（并发 %d）", _MAX_CONCURRENT)
        # ★★ 2026-10-27：启动时清理「僵尸 starting」
        #
        #   进程重启时，worker 里正在跑的任务会直接丢失，
        #   数据库里这些告警永远停在 starting ——
        #   甲方接口看到 starting 会返回 425 让对方重试，但永远没结果。
        #
        #   实测积压了 6 条，最早一条卡了 11 天。
        self._cleanup_stale_starting()

    def stop(self) -> None:
        self._running = False
        # 放哨兵值唤醒 worker
        for _ in self._workers:
            self._queue.put("")

    # ------------------------------------------------------------ 失败标记
    def _mark_failed_async(self, alarm_id: str, reason: str) -> None:
        """把抓取失败原因写进数据库（尽力而为，不阻塞调用方）。

        ★ 为什么用异步任务而不是直接写：
          submit() 可能在 worker 线程里被调（甚至从同步上下文），
          直接 await 会破坏线程模型。这里把写库丢回事件循环，
          失败也只是记日志 —— 标记失败不能影响告警主流程。
        """
        loop = self._loop
        if loop is None or loop.is_closed():
            logger.warning("事件循环不可用，无法标记 alarm=%s 失败", alarm_id)
            return

        async def _do() -> None:
            try:
                from sqlalchemy import select

                from server.db import SessionLocal
                from server.models import Alarm

                async with SessionLocal() as db:
                    row = (
                        await db.execute(select(Alarm).where(Alarm.id == alarm_id))
                    ).scalars().first()
                    if row is None:
                        return
                    # 已有视频或已失败的不要覆盖（避免覆盖正常结果）
                    if str(getattr(row, "video_status", "")) in ("ready", "failed"):
                        return
                    row.video_status = "failed"
                    row.video_error = reason[:500]
                    await db.commit()
                logger.info("已标记 alarm=%s 视频抓取失败：%s", alarm_id, reason[:80])
            except Exception:
                logger.exception("标记视频失败状态出错 alarm=%s", alarm_id)

        try:
            asyncio.run_coroutine_threadsafe(_do(), loop)
        except Exception:
            logger.exception("调度失败标记出错 alarm=%s", alarm_id)

    # ------------------------------------------------------------ 提交任务
    def submit(self, alarm_id: str, *, on_done=None) -> bool:
        """把一条告警加入抓取队列。

        返回 True 表示已入队（或已在处理中）；False 表示服务未就绪或队列已满。

        ★ 与同事版本的关键差异：同一告警重复提交是幂等的；
          不同告警会排队执行，而不是被直接标记为 failed。

        ★ 2026-XX 并发加固：对**所有**入口（自动抓取 / 手动回放 / 批量补抓）
          统一执行队列硬上限（video_auto_max_queue，默认 200）。
          原来只有自动抓取路径检查积压，手动 backfill 可以一次塞进
          上千条 —— 设备回放是独占资源（约 1 条/分钟），队列无界会把
          设备连接占死数小时。
        """
        if not self._isapi_enabled():
            reason = "录像抓取未配置（ISAPI 地址/密码未配齐）"
            logger.error("视频抓取失败 alarm=%s：%s", alarm_id, reason)
            self._mark_failed_async(alarm_id, reason)
            return False

        with self._active_lock:
            if alarm_id in self._active:
                logger.info("告警 %s 已在抓取中，忽略重复请求", alarm_id)
                return True
            self._active.add(alarm_id)

        # ★★ 2026-10-23 关键修正：片段登记必须放在**入队之前**。
        #
        #   原来放在 _run_job 里（worker 线程），流程是：
        #       第 1 条入队 → worker 取出 → 登记 owner → 延迟 30s → 抓 60s → 完成
        #       第 2 条入队 → **在队列里排队 90 秒** → 轮到自己才开始登记
        #                  → 此时 owner 已释放 → 自己变成新 owner → 又抓一次
        #
        #   结果：同一分钟的报警永远合并不了（实测 17:41:10 与 17:41:13
        #   两条各抓了一次）。
        #
        #   现在在入队时登记：第 2 条一进来就知道「本分钟已有 owner」，
        #   直接登记为 peer 并**不入队**，等 owner 抓完共享视频。
        owner_plan = None
        if self._plan_enabled:
            is_owner, owner_plan = self._submit_register(alarm_id)
            if not is_owner:
                with self._active_lock:
                    self._active.discard(alarm_id)
                logger.info(
                    "★ 片段合并：alarm=%s 并入本分钟已有片段，不入队（共享同一段视频）",
                    alarm_id[:8],
                )
                return True

        # 队列硬上限（排队中的任务数，不含正在处理的）
        try:
            limit = int(getattr(self._settings, "video_auto_max_queue", 200))
        except (TypeError, ValueError):
            limit = 200
        if limit > 0 and self._queue.qsize() >= limit:
            with self._active_lock:
                self._active.discard(alarm_id)
            logger.warning(
                "回放队列积压 %d（上限 %d），拒绝新任务 alarm=%s",
                self._queue.qsize(),
                limit,
                alarm_id,
            )
            return False

        self._queue.put(alarm_id)
        logger.info("告警 %s 已加入回放队列（队列长度 %d）", alarm_id, self._queue.qsize())
        return True

    @property
    def _plan_enabled(self) -> bool:
        """片段合并开关。让用户能一键退回「每条各抓 60 秒」。"""
        return bool(getattr(self._settings, "video_merge_by_minute", True))

    def _submit_register(self, alarm_id: str) -> tuple[bool, object]:
        """入队前登记片段。读库拿 (设备, 通道, 报警时间)。

        返回 (is_owner, plan)。出错时按 owner 处理（宁可多抓一次不可丢）。
        """
        from server.services.playback_registry import get_alarm_snapshot

        try:
            snap = get_alarm_snapshot(alarm_id)
            if snap is None:
                return True, None
            device_id, channel, alarm_time_raw = snap
            alarm_dt = parse_alarm_time(alarm_time_raw)
        except Exception:
            logger.exception("片段登记失败 alarm=%s（按单条抓取处理）", alarm_id)
            return True, None
        return self._register_in_plan(alarm_id, device_id, channel, alarm_dt)

    def is_active(self, alarm_id: str) -> bool:
        with self._active_lock:
            return alarm_id in self._active

    # ------------------------------------- 片段合并：按 (设备,通道,分钟) 聚合
    def _register_in_plan(
        self, alarm_id: str, device_id: str, channel: int, alarm_dt: datetime
    ) -> tuple[bool, object]:
        """把一条报警登记进「本分钟的抓取片段」。

        返回 (is_owner, plan)：
          · is_owner=True,  plan=CapturePlan → 由本任务抓取整个片段
          · is_owner=False, plan=None        → 已登记为 peer，调用方 return
          · is_owner=True,  plan=None        → 无法合并，走单条抓取

        ★ 并集实时重算：owner 开始抓之前可能又来了新报警，区间会自动扩大。
        """
        if not device_id:
            return True, None
        try:
            ch = int(channel)
        except (TypeError, ValueError):
            return True, None
        if ch <= 0:
            return True, None

        from datetime import timedelta

        minute = alarm_dt.replace(second=0, microsecond=0)
        key = (device_id, ch, minute)
        pre = max(0, int(getattr(self._settings, "video_pre_seconds", 30)))
        post = max(0, int(getattr(self._settings, "video_post_seconds", 30)))

        with self._window_lock:
            rec = self._plan_acc.get(key)
            if rec is None:
                # 本片段第一条 → 成为 owner
                rec = {
                    "owner": alarm_id,
                    "min_t": alarm_dt,
                    "max_t": alarm_dt,
                    "alarms": [alarm_id],
                }
                self._plan_acc[key] = rec
                is_owner = True
            else:
                # 已有片段 → 更新并集
                rec["min_t"] = min(rec["min_t"], alarm_dt)
                rec["max_t"] = max(rec["max_t"], alarm_dt)
                if alarm_id not in rec["alarms"]:
                    rec["alarms"].append(alarm_id)
                is_owner = rec["owner"] == alarm_id

        if not is_owner:
            return False, None

        # owner 拿到当前的并集区间
        from server.services.fragment_planner import CapturePlan

        return True, CapturePlan(
            device_id=device_id,
            channel=ch,
            start=rec["min_t"] - timedelta(seconds=pre),
            end=rec["max_t"] + timedelta(seconds=post),
            alarm_ids=list(rec["alarms"]),
            minute=minute,
        )

    def _current_plan(
        self, device_id: str, channel: int, alarm_dt: datetime
    ) -> object | None:
        """读取当前片段（不修改状态）。

        worker 在抓取前调用：拿到**最新**的并集区间
        （登记后可能又来了新报警，_min_t/_max_t 已被更新）。
        """
        from datetime import timedelta

        from server.services.fragment_planner import CapturePlan

        try:
            ch = int(channel)
        except (TypeError, ValueError):
            return None
        if ch <= 0 or not device_id:
            return None

        minute = alarm_dt.replace(second=0, microsecond=0)
        pre = max(0, int(getattr(self._settings, "video_pre_seconds", 30)))
        post = max(0, int(getattr(self._settings, "video_post_seconds", 30)))

        with self._window_lock:
            rec = self._plan_acc.get((device_id, ch, minute))
            if rec is None:
                return None
            min_t, max_t = rec["min_t"], rec["max_t"]
            alarm_ids = list(rec["alarms"])

        return CapturePlan(
            device_id=device_id,
            channel=ch,
            start=min_t - timedelta(seconds=pre),
            end=max_t + timedelta(seconds=post),
            alarm_ids=alarm_ids,
            minute=minute,
        )

    def _release_plan(self, device_id: str, channel: int, alarm_dt: datetime) -> None:
        """片段抓取完成（成功或失败）后释放登记，避免 _plan_acc 只增不减。"""
        try:
            ch = int(channel)
        except (TypeError, ValueError):
            return
        if ch <= 0 or not device_id:
            return
        minute = alarm_dt.replace(second=0, microsecond=0)
        with self._window_lock:
            self._plan_acc.pop((device_id, ch, minute), None)

    # --------------------------------------------------------- 失败冷却
    # 同一告警失败后，这段时间内不再接受新的提交。
    # 为什么需要：实测用户反复点「获取视频」→ 每次新建回放监听 →
    #   失败 → 再点，SDK 句柄号一路涨（10/11/12/13/14/15…）最终崩溃。
    FAILURE_COOLDOWN_SECONDS = 120.0

    def _failure_cooldown_remaining(self, alarm_id: str) -> float:
        """该告警距上次失败还剩多少秒冷却（0 = 可以重试）。"""
        ts = self._failures.get(alarm_id)
        if not ts:
            return 0.0
        remain = self.FAILURE_COOLDOWN_SECONDS - (time.monotonic() - ts)
        if remain <= 0:
            self._failures.pop(alarm_id, None)
            return 0.0
        return remain

    def _mark_failure(self, alarm_id: str) -> None:
        """记录一次失败，进入冷却。"""
        self._failures[alarm_id] = time.monotonic()
        if len(self._failures) > 2000:
            for key in sorted(self._failures, key=self._failures.get)[:1000]:
                self._failures.pop(key, None)

    # ---------------------------------------------- 片段合并：共享 / 连坐
    def _share_with_plan_peers(
        self, device_id: str, channel: int, alarm_dt: datetime,
        mp4_path: Path, duration: int | None,
    ) -> int:
        """把已生成的视频共享给同片段的其他报警。

        ★ 为什么能共享：这些报警落在同一个自然分钟、同一个 (设备,通道)，
          画面物理上是同一路。共用一段视频既满足「每条都有视频」，
          又不必重复抓取。

        ★ 只共享视频，不共享图片 —— 每条报警的抓拍图仍是各自的。
        """
        from server.services.playback_registry import set_playback_ready

        try:
            ch = int(channel)
        except (TypeError, ValueError):
            return 0
        minute = alarm_dt.replace(second=0, microsecond=0)
        with self._window_lock:
            rec = self._plan_acc.get((device_id, ch, minute))
            peers = list(rec["alarms"]) if rec else []

        shared = 0
        for pid in peers:
            with contextlib.suppress(Exception):
                if set_playback_ready(pid, mp4_path, duration=duration):
                    shared += 1
                    self._notify(pid)
        if shared:
            logger.info(
                "★ 片段共享：本段视频服务 %d 条报警（%s ch%s %s）",
                shared, device_id, ch, minute.strftime("%H:%M"),
            )
        self._release_plan(device_id, channel, alarm_dt)
        return shared

    def _fail_plan_peers(
        self, device_id: str, channel: int, alarm_dt: datetime, reason: str
    ) -> None:
        """主抓失败时，同片段其他报警一并标失败（否则永远卡在 starting）。"""
        from server.services.playback_registry import set_playback_failed

        try:
            ch = int(channel)
        except (TypeError, ValueError):
            return
        minute = alarm_dt.replace(second=0, microsecond=0)
        with self._window_lock:
            rec = self._plan_acc.get((device_id, ch, minute))
            peers = list(rec["alarms"]) if rec else []

        for pid in peers:
            with contextlib.suppress(Exception):
                set_playback_failed(pid, reason or "同片段的抓取任务失败")
                self._notify(pid)
        self._release_plan(device_id, channel, alarm_dt)


    def queue_size(self) -> int:
        """当前积压的抓取任务数（排队中 + 正在处理）。

        供自动抓取的限流判断使用：积压过多时跳过新任务，
        避免设备回放连接被占死。
        """
        try:
            return self._queue.qsize()
        except Exception:
            return 0

    def cancel(self, alarm_id: str) -> None:
        """告警被删除时调用：标记取消，并清掉**抓取中途**产出的半成品。

        ★ 只清理「回放抓取」自己的产物（playback_raw 下的 PS，
          以及正在写的 mp4）。正常的 media/video/<id>.mp4 由调用方的
          delete_alarm_files 统一处理 —— 这里不要抢着删，
          否则调用方统计不到它，也会让「取消」这个动作有超出语义的副作用。

        返回 None；是否真的在抓取中可通过 is_active 判断。
        """
        if not self.is_active(alarm_id):
            # 没有正在进行的抓取任务，没有半成品需要清理
            return

        with self._active_lock:
            self._cancelled.add(alarm_id)

        # 只删抓取中途的原始流；正在写的 mp4 由 worker 在收尾时自行清理
        raw = RAW_DIR / f"{alarm_id}.mpegps"
        with contextlib.suppress(OSError):
            if raw.is_file():
                raw.unlink()
        logger.info("已请求取消告警 %s 的回放任务", alarm_id)

    def _is_cancelled(self, alarm_id: str) -> bool:
        with self._active_lock:
            return alarm_id in self._cancelled

    # ------------------------------------------------------------ worker
    def _worker(self) -> None:
        while self._running:
            try:
                alarm_id = self._queue.get()
            except Exception:
                continue
            if not alarm_id or not self._running:
                break
            try:
                self._run_job(alarm_id)
            except Exception:
                logger.exception("回放任务异常 alarm=%s", alarm_id)
            finally:
                with self._active_lock:
                    self._active.discard(alarm_id)
                    self._cancelled.discard(alarm_id)
                self._notify(alarm_id)

    def _notify(self, alarm_id: str) -> None:
        """通知主循环：某条告警的回放状态变了（由 server 层负责广播）。"""
        if self._loop is None:
            return
        handler = getattr(self, "_on_done", None)
        if handler is None:
            return
        with contextlib.suppress(RuntimeError):
            asyncio.run_coroutine_threadsafe(handler(alarm_id), self._loop)

    _on_done = None

    def set_done_callback(self, coro_factory) -> None:
        """注册「任务完成」回调（async 函数，接收 alarm_id）。"""
        self._on_done = coro_factory

    # ------------------------------------------------------------ 核心流程
    def _run_job(self, alarm_id: str) -> None:
        """在 worker 线程里执行一次抓取 + 转码。

        ⚠️ 这里不碰数据库 —— 状态变更全部通过 _on_done 回调交给
           asyncio 侧的 server 层处理，避免跨线程用 async session。
        """
        from server.services.playback_registry import (
            get_alarm_snapshot,
            set_playback_failed,
            set_playback_ready,
            set_playback_starting,
        )

        # ★ 立刻置「抓取中」：用户点完就能在界面上看到进度，
        #   而不是等 worker 真正开跑（队列有积压时可能等几十秒）。
        set_playback_starting(alarm_id)

        snap = get_alarm_snapshot(alarm_id)
        if snap is None:
            logger.warning("回放任务: 告警 %s 不存在（可能已被删除）", alarm_id)

            return

        device_id, channel, alarm_time_raw = snap

        try:
            alarm_dt = parse_alarm_time(alarm_time_raw)
        except ValueError as exc:
            logger.warning("回放任务: 告警 %s 时间解析失败: %s", alarm_id, exc)
            set_playback_failed(alarm_id, f"告警时间无法解析: {alarm_time_raw!r}")
            return

        if not self._isapi_enabled():
            logger.warning("回放任务: ISAPI 未配置，无法抓取")
            set_playback_failed(alarm_id, "ISAPI 未配置 host/password")
            self._fail_plan_peers(device_id, channel, alarm_dt, "ISAPI 未配置")
            return

        # ★ 抓取区间：告警时刻 **前 N 秒 ~ 后 M 秒**
        #
        #   甲方明确要求「前后 30 秒的视频片段」，所以默认各 30 秒。
        #   可通过 ISUP_VIDEO_PRE_SECONDS / ISUP_VIDEO_POST_SECONDS 调整。
        #
        #   ⚠️ 与旧实现的差异：旧代码是「告警前 1 分钟」到「告警时刻」，
        #      只有前段、没有后段 —— 不符合甲方"前后30秒"的要求。
        pre = max(0, int(getattr(self._settings, "video_pre_seconds", 30)))
        post = max(0, int(getattr(self._settings, "video_post_seconds", 30)))

        # ★★★ 2026-10-23 关键修复：**延迟 post 秒后再抓**，否则拿不到后段。
        #
        #   问题（现场实测）：
        #     告警在 t 时刻产生，我们立刻去抓 [t-30, t+30]。
        #     但 **t+30 那一刻的画面还没录出来** —— 设备只能返回
        #     [t-30, now]，实测视频时长普遍只有 28~30 秒，缺后段。
        #
        #   甲方要求「前后各 30 秒」，缺后段等于没满足需求。
        #
        #   解决：报警到达后先等 post 秒，让设备把后段录完，再去抓。
        #     等待期间任务仍在队列里（不影响告警入库和推送）。
        #
        #   代价：
        #     · 视频 ready 的时间推后约 30 秒（总耗时 60~120 秒）
        #     · 队列占用时间变长（回放是串行资源）
        #   但换来「视频时长完整」，这是甲方明确要求的指标。
        #
        #   可配置：ISUP_VIDEO_CAPTURE_DELAY_SECONDS
        #     · 负数（默认 -1）→ **自动计算**（见下）
        #     · 0 → 立即抓取（后段会缺）
        #     · 正数 → 固定值（不推荐，容易不够）
        #
        #   ★★★ 2026-10-26 关键修复：延迟必须覆盖到**最晚报警 + post**，
        #       不能只等 post 秒。
        #
        #   现场复现（09:24 那批）：
        #     3 条报警 09:24:22 / :25 / :29（设备时钟），合并区间
        #     [09:24:02, 09:24:49] 共 47 秒 —— 计算是对的。
        #     但第一条报警到达平台是 09:23:02，只等了 20 秒就下载
        #     → 此时设备时钟才到 09:24:40
        #     → 09:24:49 那段还没录完，只拿到 38 秒（差 9 秒）
        #
        #   所以延迟 = post + (最晚报警 - 本条报警)，
        #   即「等到 end_dt（最晚报警+post）那一刻」再下载。
        #   对 owner 来说，本条报警是最早的，所以要等满整个跨度 + post。
        #
        # ★★ 2026-10-26：**必须先读 plan 再等待**。
        #    登记已在 submit() 完成，此刻 plan 反映的是「截至现在」的合并跨度。
        #    先读 plan 才能算出要等多久（跨度越长等越久）。
        plan = None
        if self._plan_enabled:
            plan = self._current_plan(device_id, channel, alarm_dt)

        raw_delay = float(
            getattr(self._settings, "video_capture_delay_seconds", -1.0)
        )
        span_s = 0.0
        if raw_delay < 0:
            # 等 end_dt（= 最晚报警 + post）录完。
            # ★ 延迟 = post + 合并跨度（span）
            if plan is not None and plan.alarm_ids:
                span_s = max(0.0, plan.span_seconds - pre - post)
            delay = float(post) + span_s
        else:
            delay = raw_delay
        if delay > 0:
            logger.info(
                "回放抓取 alarm=%s 延迟 %.0f 秒后再抓"
                "（等设备录完 最晚报警+%d 秒 的后段，合并跨度 %.0f 秒）",
                alarm_id,
                delay,
                post,
                span_s if raw_delay < 0 else 0,
            )
            # ★ 分片 sleep，便于及时响应取消
            remaining = delay
            while remaining > 0:
                if self._is_cancelled(alarm_id):
                    logger.info("回放任务在延迟等待中被取消 alarm=%s", alarm_id)
                    return
                step = min(1.0, remaining)
                time.sleep(step)
                remaining -= step

        start_dt = alarm_dt - timedelta(seconds=pre)
        end_dt = alarm_dt + timedelta(seconds=post)

        # ★★ 片段合并：登记已在 submit() 完成（入队前），
        #   这里用**等待后重新读一次**的 plan（等待期间可能又有新报警并入）。
        #
        # ★★★ 2026-10-26 竞态保护：
        #   如果等待期间又来了新报警，跨度变长 → 我们原本等的时长不够，
        #   需要**补等**差额，否则后段仍会缺。
        #   实测复现：09:24 那批就是等 20 秒后区间已扩到 47 秒，
        #   但只等了 20 秒，导致视频只有 38 秒。
        if self._plan_enabled:
            fresh = self._current_plan(device_id, channel, alarm_dt)
            if fresh is not None:
                # 如果新 plan 的 end 比我们原本等的更晚，补等
                if raw_delay < 0 and fresh.end > end_dt:
                    extra = (fresh.end - end_dt).total_seconds()
                    if extra > 0.5:
                        logger.info(
                            "回放抓取 alarm=%s 等待期间有新报警并入，"
                            "补等 %.0f 秒（区间延到 %s）",
                            alarm_id,
                            extra,
                            fresh.end.strftime("%H:%M:%S"),
                        )
                        remain = extra
                        while remain > 0:
                            if self._is_cancelled(alarm_id):
                                logger.info(
                                    "回放任务在补等期间被取消 alarm=%s", alarm_id
                                )
                                return
                            step = min(1.0, remain)
                            time.sleep(step)
                            remain -= step
                plan = fresh
            else:
                plan = None

        if plan is not None:
            start_dt = plan.start
            end_dt = plan.end
            logger.info(
                "回放抓取 alarm=%s 片段区间 %s ~ %s（%.0f 秒，服务 %d 条报警）"
                " channel=%s device=%s",
                alarm_id, start_dt, end_dt, plan.span_seconds,
                len(plan.alarm_ids), channel, device_id,
            )

        RAW_DIR.mkdir(parents=True, exist_ok=True)
        MEDIA_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
        raw_path = RAW_DIR / f"{alarm_id}.mpegps"
        out_path = MEDIA_VIDEO_DIR / f"{alarm_id}.mp4"

        # 清掉上次失败留下的残留
        for stale in (raw_path, out_path):
            with contextlib.suppress(OSError):
                if stale.is_file():
                    stale.unlink()

        logger.info(
            "回放抓取 alarm=%s 区间 %s ~ %s channel=%s device=%s",
            alarm_id, start_dt, end_dt, channel, device_id,
        )

        # ★★★ 2026-10-24：优先走 ISAPI 下载（并发 + 4.5 倍速）。
        #
        #   为什么换：SDK 回放实测同设备只支持 1 路、且 1 倍速，
        #   3 台摄像头的需求缺口 3 倍。ISAPI 下载实测 3 路并发 100% 成功、
        #   4.5 倍速，容量从缺口 3 倍变成余量 33%。
        #   （详见 services/isapi_client.py 顶部的实测数据）
        #
        if self._isapi_enabled():
            try:
                n = self._capture_via_isapi(
                    alarm_id, channel, start_dt, end_dt, raw_path
                )
                if n > 0:
                    logger.info(
                        "ISAPI 下载成功 alarm=%s %.2f MB", alarm_id, n / 1024 / 1024
                    )
                    self._finish_capture(
                        alarm_id, raw_path, out_path, device_id, channel, alarm_dt
                    )
                    return
                logger.warning("ISAPI 下载返回 0 字节 alarm=%s", alarm_id)
            except Exception as exc:
                logger.warning("ISAPI 下载失败（%s）alarm=%s", exc, alarm_id)
        set_playback_failed(alarm_id, "ISAPI 录像下载失败")
        self._fail_plan_peers(device_id, channel, alarm_dt, "ISAPI 录像下载失败")
        return

    def _finish_capture(
        self,
        alarm_id: str,
        raw_path: Path,
        out_path: Path,
        device_id: str,
        channel: int,
        alarm_dt: datetime,
    ) -> None:
        """转码 PS→MP4、标记就绪、共享给同片段其它报警。

        ★ 2026-10-24 提取出来：ISAPI 下载和 SDK 回放两条路径都要走这段，
          避免逻辑重复（也避免两处行为不一致）。
        """
        from server.services.playback_registry import (
            set_playback_failed,
            set_playback_ready,
        )

        # ---- 转码 PS → MP4 ----
        try:
            logger.info("回放转码 alarm=%s", alarm_id)
            transcode_ps_to_mp4(raw_path, out_path)
        except Exception as exc:
            logger.exception("回放转码失败 alarm=%s", alarm_id)
            with contextlib.suppress(OSError):
                if out_path.is_file():
                    out_path.unlink()
            set_playback_failed(alarm_id, f"转码失败: {exc}")
            self._fail_plan_peers(device_id, channel, alarm_dt, f"转码失败: {exc}")
            return
        finally:
            # ★ 原始 PS 一定要删，不然每次抓取都留一份大文件
            with contextlib.suppress(OSError):
                if raw_path.is_file():
                    raw_path.unlink()

        if _file_has_data(out_path):
            # ★ 告警可能在抓取过程中被删除 —— set_playback_ready 会检测到
            #   并自动删掉这个产物，不会留下孤儿文件
            dur = probe_duration_seconds(out_path)
            logger.info("回放就绪 alarm=%s -> %s（时长 %s 秒）", alarm_id, out_path, dur)
            set_playback_ready(alarm_id, out_path, duration=dur)
            # ★★ 同片段的其它报警共享这段视频（自然分钟并集合并）
            self._share_with_plan_peers(device_id, channel, alarm_dt, out_path, dur)
        else:
            set_playback_failed(alarm_id, "转码后文件为空")
            self._fail_plan_peers(device_id, channel, alarm_dt, "转码后文件为空")

    # ------------------------------------------------------------ ISAPI 下载
    def _isapi_enabled(self) -> bool:
        """ISAPI 通道是否可用（开关打开 + 配了地址和密码）。"""
        if not getattr(self._settings, "video_use_isapi", False):
            return False
        host = getattr(self._settings, "isapi_host", "")
        password = getattr(self._settings, "isapi_password", "")
        return bool(host and password)

    def _capture_via_isapi(
        self,
        alarm_id: str,
        channel: int,
        start_dt: datetime,
        end_dt: datetime,
        raw_path: Path,
    ) -> int:
        """用 ISAPI 下载录像片段。返回字节数（0 表示失败）。

        ★ 与 SDK 回放的关键差异（实测 2026-10-24）：
          · 支持并发（3 路 100% 成功），SDK 只支持 1 路
          · 约 4.5 倍速（15 秒录像 3.7 秒下完）
          · 不占用 SDK 回放会话，可以和 SDK 路径并存

        ★ 时间语义：ISAPI 用**设备本地时间**，而 alarm_dt 正是设备时钟，
          所以直接传即可（不需要额外换算）。
        """
        from server.services.isapi_client import IsapiError, get_client

        max_seg = int(getattr(self._settings, "isapi_max_segment_seconds", 180))
        if (end_dt - start_dt).total_seconds() > max_seg:
            logger.warning(
                "片段 %.0f 秒超过上限 %d，截断 alarm=%s",
                (end_dt - start_dt).total_seconds(),
                max_seg,
                alarm_id,
            )
            end_dt = start_dt + timedelta(seconds=max_seg)

        client = get_client(
            getattr(self._settings, "isapi_host", ""),
            int(getattr(self._settings, "isapi_port", 80)),
            getattr(self._settings, "isapi_username", "admin"),
            getattr(self._settings, "isapi_password", ""),
        )

        try:
            n = client.download_by_time(
                channel=channel,
                start=start_dt,
                end=end_dt,
                out_path=raw_path,
                timeout=float(
                    getattr(self._settings, "isapi_download_timeout", 60.0)
                ),
            )
            return n
        except IsapiError as exc:
            msg = str(exc)
            if "500" in msg:
                # 该时段确实没录像 —— 这是正常业务情况，不是故障
                logger.info("ISAPI: 该时段无录像 alarm=%s（%s~%s）",
                            alarm_id, start_dt, end_dt)
            raise

# 进程级单例（由 main.py 的 lifespan 启动）
playback_service = PlaybackService()
