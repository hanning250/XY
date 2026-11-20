# -*- coding: utf-8 -*-
"""媒体 URL 组装 + 图片归档路径生成。

★ 关键背景（docs §2.1）：
   实测 storage/ 下的图片文件名是 32 位十六进制哈希（如 02C91C96...jpg），
   甲方说「哈希 + .jpg 就能看」是成立的。但 §2.2② 指出：
   那个哈希很可能是云存储服务端生成的，**不一定等于 SS 回调给的 pFileName**。
   所以这里两者都保留：
     · file_hash  → 对外 URL 用的键
     · source_name → SS 回调原始文件名（排查 / P0 验证用）
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path

from server.config import PROJECT_ROOT, STORAGE_DIR, get_settings

_SAFE_NAME = re.compile(r"[^0-9A-Za-z._\-]+")


def sanitize_filename(name: str) -> str:
    """把 SS 回调给的文件名清洗成安全的文件名。"""
    name = name.strip().replace("\\", "/").split("/")[-1]
    name = _SAFE_NAME.sub("_", name)
    return name or "unnamed.jpg"


def probe_jpeg_size(data: bytes) -> tuple[int | None, int | None]:
    """从 JPEG 字节流里读出宽高（不解码，只扫 SOF 段）。

    这样入库的 width/height 就是真实值，前端能按比例布局、避免 CLS。
    """
    try:
        if len(data) < 4 or data[:2] != b"\xff\xd8":
            return None, None
        i = 2
        n = len(data)
        while i < n - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            # SOF0..SOF15（排除 DHT=0xC4, JPG=0xC8, DAC=0xCC）
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                height = int.from_bytes(data[i + 5 : i + 7], "big")
                width = int.from_bytes(data[i + 7 : i + 9], "big")
                return (width or None), (height or None)
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            seg_len = int.from_bytes(data[i + 2 : i + 4], "big")
            if seg_len < 2:
                break
            i += 2 + seg_len
    except Exception:
        pass
    return None, None


def decide_file_hash(source_name: str, content: bytes) -> str:
    """决定这张图对外用的哈希键。

    优先用文件名里的哈希（甲方预期能直接 `.jpg` 打开）；
    文件名不是哈希形态时，退回用内容 sha256，保证键稳定且唯一。
    """
    stem = Path(source_name).stem
    if re.fullmatch(r"[0-9A-Fa-f]{16,64}", stem):
        return stem.upper()
    match = re.match(r"^(?P<hash>[0-9A-Fa-f]{16,64})\s*(?:\(\d+\))?$", stem)
    if match:
        return match.group("hash").upper()
    # 兜底：内容哈希
    return hashlib.sha256(content).hexdigest()[:32].upper()


def build_storage_path(
    *, file_hash: str, source_name: str, when: datetime | None = None
) -> Path:
    """生成图片归档路径。

    原实现是 storage/ 平铺（实测已 37 个文件），文件多后目录会卡。
    这里改为 storage/yyyy/mm/dd/ 分层（可由配置关闭）。
    """
    settings = get_settings()
    when = when or datetime.now()

    if settings.storage_date_partition:
        target_dir = STORAGE_DIR / f"{when:%Y}" / f"{when:%m}" / f"{when:%d}"
    else:
        target_dir = STORAGE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    safe = sanitize_filename(source_name)
    if not safe.lower().endswith((".jpg", ".jpeg", ".png")):
        safe = f"{safe}.jpg"

    path = target_dir / safe
    # 防覆盖：同名时补哈希后缀；后缀名也被占（同内容重复上传/哈希前缀撞车）
    # 就继续追加序号，绝不覆盖已有文件 —— 覆盖会让已入库图片指向被调包的内容。
    if path.exists():
        stem, suffix = Path(safe).stem, Path(safe).suffix
        candidate = target_dir / f"{stem}_{file_hash[:8]}{suffix}"
        n = 1
        while candidate.exists():
            candidate = target_dir / f"{stem}_{file_hash[:8]}_{n}{suffix}"
            n += 1
        path = candidate
    return path


def relative_to_project(path: Path) -> str:
    """转成相对项目根的 POSIX 风格路径，写进数据库便于迁移。"""
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def image_urls(file_path: str) -> tuple[str, str, str]:
    """由存储相对路径生成 (相对URL, 绝对URL, 缩略图URL)。

    存储路径形如 storage/2026/09/17/xxx.jpg
    对外 URL 形如 /media/2026/09/17/xxx.jpg
    """
    settings = get_settings()
    rel = Path(file_path)
    # 去掉 storage/ 前缀
    parts = rel.parts
    if parts and parts[0] == "storage":
        parts = parts[1:]
    sub = "/".join(parts)

    url = f"/media/{sub}"
    absolute = f"{settings.public_base_url.rstrip('/')}{url}"
    return url, absolute, f"{url}?w=400"


def video_public_url(filename: str) -> str:
    """生成视频的对外**绝对** URL。

    ★ 统一入口：所有写 alarm.video_url 的地方都必须用它。
      历史上 playback_registry 自己拼了相对路径 "/media/video/x.mp4"，
      而 video_provider 写的是绝对 URL，同一字段两种语义，
      前端 <video src> 表现不一致 —— 一定要走这里。
    """
    settings = get_settings()
    return f"{settings.public_base_url.rstrip('/')}/media/video/{filename}"
