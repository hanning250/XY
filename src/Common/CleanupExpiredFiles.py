# -*- coding: utf-8 -*-
"""按保留天数清理过期文件：仅删除超过时限的文件，未到期一律不动。"""
import os
import time
from datetime import datetime, timedelta

# 与 HCISUPCMS.target_dir 一致：项目根目录
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# 目录名 -> 保留天数（超过该天数才删除）
RETENTION_RULES = {
    'outputFiles': 15,
    'storage': 15,
    'IsupSDKLog': 7,
}


def _is_expired(mtime, retention_days, now_ts):
    """修改时间早于 cutoff 才算过期；等于或晚于 cutoff 的文件不删。"""
    cutoff_ts = now_ts - retention_days * 24 * 60 * 60
    return mtime < cutoff_ts


def cleanup_directory(dir_path, retention_days, now_ts=None):
    """
    清理单个目录下的过期文件（不递归删除子目录本身）。
    返回 (deleted_count, kept_count, errors)
    """
    if now_ts is None:
        now_ts = time.time()

    deleted = 0
    kept = 0
    errors = []

    if not os.path.isdir(dir_path):
        return deleted, kept, errors

    for root, _dirs, files in os.walk(dir_path):
        for name in files:
            file_path = os.path.join(root, name)
            try:
                # 不跟随符号链接，避免误删链接目标
                if os.path.islink(file_path):
                    kept += 1
                    continue
                mtime = os.path.getmtime(file_path)
                if _is_expired(mtime, retention_days, now_ts):
                    os.remove(file_path)
                    deleted += 1
                    print(f'  [删除] {file_path} (mtime={datetime.fromtimestamp(mtime)})')
                else:
                    kept += 1
            except OSError as e:
                errors.append((file_path, str(e)))
                print(f'  [跳过] 无法处理 {file_path}: {e}')

    return deleted, kept, errors


def cleanup_expired_files(project_root=None, rules=None):
    """
    按规则清理项目根下指定目录。
    规则语义：超过 retention_days 天（mtime < now - N天）才删除；未到时限不改动。
    """
    root = project_root or _PROJECT_ROOT
    rules = rules or RETENTION_RULES
    now_ts = time.time()
    now_str = datetime.fromtimestamp(now_ts).strftime('%Y-%m-%d %H:%M:%S')

    print(f'开始清理过期文件 @ {now_str}，根目录: {root}')
    total_deleted = 0
    total_kept = 0

    for dirname, days in rules.items():
        dir_path = os.path.join(root, dirname)
        cutoff = datetime.fromtimestamp(now_ts) - timedelta(days=days)
        print(f'- {dirname}/ 保留 {days} 天（仅删除早于 {cutoff.strftime("%Y-%m-%d %H:%M:%S")} 的文件）')
        deleted, kept, _errors = cleanup_directory(dir_path, days, now_ts)
        total_deleted += deleted
        total_kept += kept
        print(f'  结果: 删除 {deleted} 个, 保留 {kept} 个')

    print(f'清理完成: 共删除 {total_deleted} 个, 保留 {total_kept} 个未到期文件')
    return total_deleted, total_kept


if __name__ == '__main__':
    cleanup_expired_files()
