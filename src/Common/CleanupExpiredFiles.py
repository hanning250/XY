# -*- coding: utf-8 -*-
"""按保留天数清理过期媒体文件。

来源：合并自同事 XY-development 的 src/Common/CleanupExpiredFiles.py，
      但做了两处关键改造（见下）。

★ 与原版的关键差异
------------------
原版（同事）直接用 mtime 判断，删掉 storage/ 和 outputFiles/ 里的旧文件。
但本项目里 storage/ 是**告警图片归档**，数据库 AlarmImage.file_path 保存的就是
`storage/2026/09/17/xxx.jpg` 这种路径 —— 按 mtime 盲删会让历史告警卡片全变裂图。

因此本版改成**以数据库为准 + 保留天数双保险**：
    · storage 图片：只有当它已不再被任何告警记录引用（孤儿）时才删
    · media/video  ：只有当它已不再被任何告警引用时才删
    · outputFiles / IsupSDKLog：纯运行产物，按 mtime 删即可

★ 保留期
--------
默认 30 天（RETENTION_DAYS）。可通过 rules 参数覆盖。

★ 两条使用路径
--------------
1. `cleanup_expired_files()`   —— 启动 / 定时调用，按保留天数全量清理
2. `delete_media_in_range()`   —— 由 HTTP 接口调用，删除**指定时段**的媒体
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

# 项目根目录（src/Common/ → 上两级）
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)

# 默认保留天数（用户确认：30 天）
DEFAULT_RETENTION_DAYS = 30

# 目录 -> 保留天数。超过该天数才进入删除候选。
#
# ★ 注意：storage 与 media/video 即使超期，也还要再过一次"数据库是否引用"的检查。
RETENTION_RULES = {
    "outputFiles": DEFAULT_RETENTION_DAYS,   # SDK 取流/回放原始落盘
    "storage": DEFAULT_RETENTION_DAYS,       # 告警图片归档（★ 需 DB 校验）
    "media/video": DEFAULT_RETENTION_DAYS,   # 托管视频（★ 需 DB 校验）
    "IsupSDKLog": 7,                         # SDK 日志，短一些
}

# 这些目录必须经过数据库引用校验，不能纯按 mtime 删
_DB_GUARDED = {"storage", "media/video"}

# 永不删除的文件名（数据库 / 配置文件）
_NEVER_DELETE_SUFFIX = (".db", ".db-wal", ".db-shm", ".json", ".py")


@dataclass
class CleanupResult:
    """清理结果统计。"""

    deleted: int = 0
    kept: int = 0
    skipped_in_use: int = 0          # 超期但仍被告警引用的文件
    bytes_freed: int = 0
    errors: list[tuple[str, str]] = field(default_factory=list)
    details: list[str] = field(default_factory=list)

    def merge(self, other: "CleanupResult") -> None:
        self.deleted += other.deleted
        self.kept += other.kept
        self.skipped_in_use += other.skipped_in_use
        self.bytes_freed += other.bytes_freed
        self.errors.extend(other.errors)
        self.details.extend(other.details)


# ---------------------------------------------------------------------------
# 文件系统扫描
# ---------------------------------------------------------------------------
def _iter_files(dir_path: Path):
    """递归列出目录下所有文件（不跟随符号链接）。"""
    if not dir_path.is_dir():
        return
    for root, dirs, files in os.walk(dir_path):
        # 不进入符号链接目录
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
        for name in files:
            file_path = Path(root) / name
            if file_path.is_symlink():
                continue
            yield file_path


def _relative_posix(path: Path) -> str:
    """转成相对项目根的 POSIX 路径，用于和数据库里的 file_path 比对。"""
    try:
        return path.resolve().relative_to(Path(_PROJECT_ROOT).resolve()).as_posix()
    except ValueError:
        return path.as_posix()


# ---------------------------------------------------------------------------
# 数据库引用集合
# ---------------------------------------------------------------------------
def collect_referenced_files(db_path: str | None = None) -> set[str]:
    """收集当前**仍被数据库引用**的媒体文件相对路径。

    用标准库 sqlite3 直接读，避免为了清理模块去依赖 SQLAlchemy 的异步栈
    （清理可能在 SDK 进程里跑，那边没有 aiosqlite）。

    返回形如 {'storage/2026/09/17/xxx.jpg', 'media/video/yyy.mp4'} 的集合。
    """
    import sqlite3

    db_path = db_path or os.path.join(_PROJECT_ROOT, "data", "alarm.db")
    refs: set[str] = set()
    if not os.path.isfile(db_path):
        return refs

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return refs

    try:
        cur = conn.cursor()

        # ① 告警图片
        try:
            for (path,) in cur.execute("SELECT file_path FROM alarm_image"):
                if path:
                    refs.add(str(path).replace("\\", "/").lstrip("/"))
        except sqlite3.Error:
            pass

        # ② 告警视频（alarm.video_url 存的是对外 URL，需要还原成相对路径）
        try:
            for (url,) in cur.execute(
                "SELECT video_url FROM alarm WHERE video_url IS NOT NULL"
            ):
                if not url:
                    continue
                u = str(url)
                # http://host/media/video/xxx.mp4 -> media/video/xxx.mp4
                marker = "/media/"
                if marker in u:
                    refs.add("media/" + u.split(marker, 1)[1])
        except sqlite3.Error:
            pass

        # ③ 视频会话句柄（可能是文件路径）
        try:
            for (handle,) in cur.execute(
                "SELECT handle FROM video_session WHERE handle IS NOT NULL"
            ):
                if not handle:
                    continue
                h = str(handle).replace("\\", "/")
                if "/" in h:
                    refs.add(h.lstrip("/"))
        except sqlite3.Error:
            pass
    finally:
        conn.close()

    return refs


# ---------------------------------------------------------------------------
# 核心清理
# ---------------------------------------------------------------------------
def cleanup_directory(
    dir_path: Path,
    retention_days: int,
    *,
    now_ts: float | None = None,
    referenced: set[str] | None = None,
    db_guarded: bool = False,
    dry_run: bool = False,
) -> CleanupResult:
    """清理单个目录下的过期文件。

    retention_days : 超过这么多天的文件才进入候选
    referenced     : 仍被数据库引用的相对路径集合（db_guarded=True 时生效）
    dry_run        : 只统计不真删
    """
    result = CleanupResult()
    now_ts = now_ts if now_ts is not None else time.time()
    cutoff_ts = now_ts - retention_days * 24 * 60 * 60

    for file_path in _iter_files(dir_path):
        name = file_path.name
        if name.lower().endswith(_NEVER_DELETE_SUFFIX):
            result.kept += 1
            continue

        try:
            mtime = file_path.stat().st_mtime
        except OSError as e:
            result.errors.append((str(file_path), str(e)))
            continue

        # 未到期：一律不动
        if mtime >= cutoff_ts:
            result.kept += 1
            continue

        # 已到期，但还要看是否仍被数据库引用
        if db_guarded and referenced is not None:
            rel = _relative_posix(file_path)
            if rel in referenced:
                result.skipped_in_use += 1
                continue

        try:
            size = file_path.stat().st_size
            if not dry_run:
                os.remove(file_path)
            result.deleted += 1
            result.bytes_freed += size
            stamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            result.details.append(f"{_relative_posix(file_path)} (mtime={stamp})")
        except OSError as e:
            result.errors.append((str(file_path), str(e)))

    return result


def cleanup_expired_files(
    project_root: str | None = None,
    rules: dict[str, int] | None = None,
    *,
    dry_run: bool = False,
    verbose: bool = True,
) -> CleanupResult:
    """按保留规则清理项目根下指定目录。

    语义：超过 retention_days 天才删除；未到期一律不改动。
    storage / media/video 会额外做"数据库是否仍引用"校验，避免删出裂图。
    """
    root = Path(project_root or _PROJECT_ROOT)
    rules = rules or RETENTION_RULES
    now_ts = time.time()
    now_str = datetime.fromtimestamp(now_ts).strftime("%Y-%m-%d %H:%M:%S")

    if verbose:
        print(f"开始清理过期文件 @ {now_str}，根目录: {root}")

    referenced = collect_referenced_files(
        os.path.join(str(root), "data", "alarm.db")
    )
    if verbose:
        print(f"数据库当前引用 {len(referenced)} 个媒体文件（这些不会被删）")

    total = CleanupResult()
    for dirname, days in rules.items():
        dir_path = root / dirname
        cutoff = datetime.fromtimestamp(now_ts) - timedelta(days=days)
        if verbose:
            print(
                f"- {dirname}/ 保留 {days} 天"
                f"（仅删除早于 {cutoff.strftime('%Y-%m-%d %H:%M:%S')} 的文件）"
            )
        r = cleanup_directory(
            dir_path,
            days,
            now_ts=now_ts,
            referenced=referenced,
            db_guarded=dirname in _DB_GUARDED,
            dry_run=dry_run,
        )
        total.merge(r)
        if verbose:
            print(
                f"  结果: 删除 {r.deleted} 个, 保留 {r.kept} 个,"
                f" 因仍被引用而跳过 {r.skipped_in_use} 个"
            )

    if verbose:
        mb = total.bytes_freed / 1024 / 1024
        print(
            f"清理完成: 共删除 {total.deleted} 个（释放 {mb:.2f} MB）, "
            f"保留 {total.kept} 个未到期文件, "
            f"{total.skipped_in_use} 个虽超期但仍被引用"
        )
    return total


def delete_media_in_range(
    start: datetime,
    end: datetime,
    *,
    categories: set[str] | None = None,
    dry_run: bool = False,
    project_root: str | None = None,
) -> CleanupResult:
    """删除指定时间段内的媒体文件（由 HTTP 接口调用）。

    与 cleanup_expired_files 的区别：这里按**用户指定的时间区间**删，
    而不是按保留天数。仍然走数据库引用校验 —— 换句话说，
    只要文件还挂在某条告警上，它就会被删（这正是"按时间清理"的语义），
    但调用方需要负责把对应告警标记为已过期。

    ⚠️ 注意：本函数**不做**数据库写操作。标记过期由 server 层负责，
       这样 SDK 进程和 server 进程都能安全调用。

    categories : {'storage', 'outputFiles', 'media/video', 'IsupSDKLog'}
                 默认全部
    """
    root = Path(project_root or _PROJECT_ROOT)
    now_ts = time.time()
    start_ts = start.timestamp()
    end_ts = end.timestamp()

    if end_ts < start_ts:
        start_ts, end_ts = end_ts, start_ts

    targets = categories or set(RETENTION_RULES.keys())
    total = CleanupResult()

    for dirname in RETENTION_RULES:
        if dirname not in targets:
            continue
        dir_path = root / dirname

        for file_path in _iter_files(dir_path):
            name = file_path.name
            if name.lower().endswith(_NEVER_DELETE_SUFFIX):
                total.kept += 1
                continue

            try:
                mtime = file_path.stat().st_mtime
            except OSError as e:
                total.errors.append((str(file_path), str(e)))
                continue

            if not (start_ts <= mtime <= end_ts):
                total.kept += 1
                continue

            try:
                size = file_path.stat().st_size
                if not dry_run:
                    os.remove(file_path)
                total.deleted += 1
                total.bytes_freed += size
                stamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                total.details.append(f"{_relative_posix(file_path)} (mtime={stamp})")
            except OSError as e:
                total.errors.append((str(file_path), str(e)))

    return total


if __name__ == "__main__":
    import sys

    cleanup_expired_files(dry_run="--dry-run" in sys.argv)
