# -*- coding: utf-8 -*-
"""回放状态读写桥 —— 让 worker 线程安全地读告警、写回放状态。

为什么需要这一层：
    抓取回放跑在**普通线程**里（SMS SDK 是阻塞的），
    而本项目用的是 async SQLAlchemy。跨线程直接用 async session 会炸。

    所以这里统一用 sqlite3 同步连接做两件事：
      1. get_alarm_snapshot() —— worker 读告警的必要字段
      2. set_playback_ready/failed() —— worker 写回放结果

    ★ 所有写操作都检查 rowcount：
      如果告警在抓取过程中被删除了，UPDATE 影响 0 行，
      这时要把已经产出的 mp4 删掉，避免留下无人引用的孤儿文件。
"""

from __future__ import annotations

import contextlib
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from server.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

DB_PATH = PROJECT_ROOT / "data" / "alarm.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    # 与主库的 WAL 模式配合，避免读写互锁
    with contextlib.suppress(sqlite3.Error):
        conn.execute("PRAGMA journal_mode=WAL")
    return conn


def get_alarm_snapshot(alarm_id: str) -> tuple[str, int, str] | None:
    """读告警的 (device_id, channel, alarm_time)。

    返回 None 表示告警不存在（或已被删除）。

    ★ 2026-XX 时钟校正：报文里的 dateTime 由**设备时钟**决定，实测现场
      设备比服务器快约 60 秒（报文 14:30:29，服务器入库 14:29:29）。
      回放按 alarm_time 去设备取录像，若直接用报文时间，请求窗口会整体
      超前 1 分钟 —— 抓到的画面偏后，刚发生的报警甚至请求到"未来"。

      这里同时取出 created_at（服务器时钟），两个都在时按
      **服务器时间**作为抓取基准（created_at 是平台收到报文的时刻，
      比设备时钟可信；正常情况两者只差不到 1 秒，说明设备时钟准）。
    """
    if not DB_PATH.is_file():
        return None
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT device_id, channel, alarm_time, created_at "
                "FROM alarm WHERE id = ?",
                (alarm_id,),
            ).fetchone()
    except sqlite3.Error:
        logger.exception("读取告警快照失败 alarm=%s", alarm_id)
        return None

    if row is None:
        return None

    alarm_time = row["alarm_time"]
    created_at = row["created_at"]
    if isinstance(alarm_time, datetime):
        alarm_time = alarm_time.isoformat(sep=" ")
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat(sep=" ")

    base = _pick_capture_time(str(alarm_time or ""), str(created_at or ""))
    base = _correct_utc_naive_wall(base, str(created_at or ""))
    return (
        str(row["device_id"] or ""),
        int(row["channel"] or 1),
        base,
    )


# 设备时钟与服务器偏差超过这个秒数时的处理 —— 见下面 _pick_capture_time
_CLOCK_SKEW_TOLERANCE = 5.0


def _correct_utc_naive_wall(alarm_time: str, created_at: str) -> str:
    """纠正「设备 +08:00 被按 UTC astimezone 存成早上」的历史数据。

    服务器时区是 UTC 时：dateTime=15:00+08:00 → 库里 07:00，created_at 仍是 15:00。
    两者差约 8 小时就把 alarm_time 加回 8 小时，按设备 OSD 去抓。
    """
    from server.services.timeutil import parse_any

    at = parse_any(alarm_time)
    ct = parse_any(created_at)
    if at is None:
        return alarm_time
    if ct is None:
        return at.strftime("%Y-%m-%d %H:%M:%S")
    skew = (ct - at).total_seconds()
    if 7 * 3600 <= skew <= 9 * 3600:
        fixed = at + timedelta(hours=8)
        logger.info(
            "抓取时间纠正 UTC 墙钟 %s → 本地 %s（created_at=%s）",
            at, fixed, ct,
        )
        return fixed.strftime("%Y-%m-%d %H:%M:%S")
    return at.strftime("%Y-%m-%d %H:%M:%S")


def _pick_capture_time(alarm_time: str, created_at: str) -> str:
    """★ 选抓取基准时间：**始终用设备时钟（alarm_time）**。

    ## 2026-10-23 现场实测修正（这条改动直接决定视频能否抓到）

    原逻辑：设备时钟与服务器差 > 5 秒时，改用**服务器时间** created_at。
    看上去合理（"服务器时钟更可信"），但**与设备录像的时间轴不一致**。

    设备上的录像索引是**按设备自己的时钟**打时间戳的。
    用服务器时间去查设备录像，窗口整体偏移，SDK 必然返回 3505
    （找不到该时段录像）。

    实测数据（box001 / LE5676358 都验证过）：
        报文 dateTime 18:44:19（设备时钟）
        平台 created_at 18:42:58（服务器时钟）
        偏差 +81 秒
        用服务器时间 → 3505 失败
        用设备时间   → ✅ 成功，抓到 60 秒视频，OSD 时间戳完全对齐

    现场所有设备的时钟都偏（实测 +59 ~ +81 秒，且会漂移），
    所以任何"用服务器时间推算"的做法都不可行 ——
    只有设备自己的时间，才和它自己的录像索引一致。

    ★ 15:43 复现：回滚到旧逻辑后，box001 的 4 条报警视频全部 failed(3505)。
      恢复本逻辑后即可正常抓取。
    """
    return alarm_time or created_at


def _update(
    alarm_id: str,
    status: str,
    video_url: str | None,
    duration: int | None = None,
    error: str | None = None,
) -> bool:
    """写回放状态。返回 False 表示告警已不存在 → 调用方需要清理产物。

    ★ error（2026-XX）：把失败原因**落库**而不是只写日志 ——
      用户点「获取视频」失败时必须知道为什么（设备离线 / 该时段无录像 /
      转码失败），否则界面只会默默变回按钮，看起来像"点了没反应"。
    """
    if not DB_PATH.is_file():
        return False
    try:
        with _connect() as conn:
            cur = conn.execute(
                """
                UPDATE alarm
                   SET video_status = ?, video_url = ?, video_provider = ?,
                       video_duration = COALESCE(?, video_duration),
                       video_error = ?
                 WHERE id = ?
                """,
                (status, video_url, "sms-playback", duration, error, alarm_id),
            )
            return cur.rowcount > 0
    except sqlite3.Error:
        logger.exception("写回放状态失败 alarm=%s status=%s", alarm_id, status)
        return False


def set_playback_ready(alarm_id: str, mp4_path: Path, duration: int | None = None) -> bool:
    """标记回放就绪。若告警已被删除，删掉产物并返回 False。

    duration：视频时长（秒）。★ 对甲方很有用 —— 他们据此确认
    片段确实是「前后 30 秒」（约 60 秒），不用下载完才知道。
    """
    from server.services.media import video_public_url

    # ★ 必须与其他 Provider 用同一套 URL 生成逻辑（绝对 URL）。
    #   之前这里写的是 "/media/video/xxx.mp4" 相对路径，
    #   与 MockProvider/FileProvider 写入的绝对 URL 格式不一致，
    #   导致前端 <video src> 解析行为不同 —— 表现为「视频已获取但不播放」。
    url = video_public_url(mp4_path.name)
    if _update(alarm_id, "ready", url, duration, None):
        return True

    # ★ 告警在抓取过程中被删掉了 —— 产出的 mp4 没有任何记录引用，必须删掉
    logger.warning("告警 %s 已被删除，清理其回放产物 %s", alarm_id, mp4_path)
    with contextlib.suppress(OSError):
        if mp4_path.is_file():
            mp4_path.unlink()
    return False


def set_playback_failed(alarm_id: str, reason: str) -> None:
    """标记回放失败，并把**原因写进库**供前端展示。

    失败原因分类（前端会按前缀给不同提示）：
      · 设备未在线 / 设备不在线  → 等设备上线后重试
      · 无录像 / 空流            → 该时段确实没有录像
      · 抓取超时                 → 设备忙或网络慢
      · 转码失败                 → 录像格式问题
    """
    logger.info("回放失败 alarm=%s: %s", alarm_id, reason)
    # 原因截断，避免异常堆栈把整列塞满
    _update(alarm_id, "failed", None, None, (reason or "")[:500] or "未知原因")


def set_playback_starting(alarm_id: str) -> bool:
    """标记为「抓取中」——用户点完立刻置位，前端能马上看到进度。"""
    return _update(alarm_id, "starting", None, None, None)


def delete_alarm_files(alarm_id: str, *, file_paths: list[str]) -> tuple[int, int]:
    """删除一条告警关联的磁盘文件。

    file_paths 是相对项目根的路径（如 storage/2026/09/17/x.jpg、
    media/video/xxx.mp4），以及回放原始产物。

    返回 (删除成功数, 失败数)。

    ★ 计数按**去重后的实际文件**统计：video_url 收集出的路径可能与
      下面按 alarm_id 约定的内置路径重复，去重后再计数才不会少报。
    """
    ok = 0
    bad = 0

    candidates: list[Path] = [PROJECT_ROOT / p for p in file_paths if p]
    # 抓取回放的原始 PS / 转码产物 / HLS（文件名或目录就是 alarm_id）
    video_dir = PROJECT_ROOT / "media" / "video"
    raw_dir = PROJECT_ROOT / "data" / "playback_raw"
    candidates.append(video_dir / f"{alarm_id}.mp4")
    candidates.append(raw_dir / f"{alarm_id}.mpegps")
    candidates.append(PROJECT_ROOT / "media" / "hls" / alarm_id)
    if video_dir.is_dir():
        candidates.extend(video_dir.glob(f"{alarm_id}.*"))
    if raw_dir.is_dir():
        candidates.extend(raw_dir.glob(f"{alarm_id}.*"))

    for path in _dedupe_paths(candidates):
        if _path_still_referenced(path):
            logger.info("媒体仍被其它告警引用，跳过删除: %s", path)
            continue
        try:
            if path.is_file():
                path.unlink()
                ok += 1
            elif path.is_dir():
                import shutil

                shutil.rmtree(path)
                ok += 1
        except OSError as exc:
            logger.warning("删除文件失败 %s: %s", path, exc)
            bad += 1
    return ok, bad


def _path_still_referenced(path: Path) -> bool:
    """同分钟合并后多条告警会共用一个 mp4；其它记录还在时不能真删文件。"""
    if not DB_PATH.is_file():
        return False
    try:
        rel = path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return False
    like = f"%{rel}%"
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM alarm_image WHERE file_path = ? LIMIT 1", (rel,)
            ).fetchone()
            if row:
                return True
            row = conn.execute(
                "SELECT 1 FROM alarm WHERE video_url LIKE ? LIMIT 1", (like,)
            ).fetchone()
            if row:
                return True
            row = conn.execute(
                "SELECT 1 FROM pending_image WHERE file_path = ? LIMIT 1", (rel,)
            ).fetchone()
            return bool(row)
    except sqlite3.Error:
        logger.exception("检查媒体引用失败: %s", rel)
        return False


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    """去重 + 安全护栏：只返回项目目录内的唯一路径。"""
    root = PROJECT_ROOT.resolve()
    out: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        try:
            resolved.relative_to(root)
        except ValueError:
            # 项目目录之外 —— 拒绝删除
            logger.warning("拒绝删除项目目录之外的文件: %s", resolved)
            continue
        out.append(resolved)
    return out


def now_utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


_MEDIA_SUFFIX = {".jpg", ".jpeg", ".png", ".mp4", ".mpegps", ".ps", ".ts", ".m3u8"}


def purge_orphan_media_dirs() -> int:
    """告警记录已全部删光时，清掉 storage / 录像 / 原始流里残留文件。"""
    import shutil

    n = 0
    dirs = [
        PROJECT_ROOT / "storage",
        PROJECT_ROOT / "media" / "video",
        PROJECT_ROOT / "data" / "playback_raw",
        PROJECT_ROOT / "media" / "hls",
    ]
    for d in dirs:
        if not d.is_dir():
            continue
        for path in d.rglob("*"):
            try:
                if path.is_file() and path.suffix.lower() in _MEDIA_SUFFIX:
                    path.unlink()
                    n += 1
                elif path.is_dir() and d.name == "hls" and path != d:
                    shutil.rmtree(path)
                    n += 1
            except OSError as exc:
                logger.warning("清理残留媒体失败 %s: %s", path, exc)
    return n
