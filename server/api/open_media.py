# -*- coding: utf-8 -*-
"""★ 对外开放的媒体文件服务（**不鉴权**）。

## 为什么单独开一条路径

内部前端用的是 `/media/*`，我们给它加了**车间隔离鉴权**（`?token=<jwt>`）。
甲方 IT 部门**不登录**，拿到那个 URL 会 401。

所以这里另开 `/openapi/v1/media/*`：
    · 指向**同一批文件**
    · 但**不做鉴权**（甲方明确要求）

## ⚠️ 安全边界（必须知道）

这条路径不鉴权，意味着**内网里任何能访问本服务的人都能下载任何图片/视频**。
这是甲方明确要求的（他们要定时批量拉取，加鉴权会增加对接复杂度）。

因此：
    ① **只在内网暴露本服务**，不要直接挂公网
    ② 如果将来要加白名单，在反向代理层（nginx）按来源 IP 限制
    ③ 内部管理接口 `/api/*` 仍然强制鉴权，两套互不影响

## 为什么文件在我们后端，而不是盒子里

    · 盒子是**单台共享**的，其 URL 无法区分车间（正是要解决的问题）
    · 盒子存储是**滚动覆盖**的，不是持久存储，昨天的图可能已被覆盖
    · 盒子掉线 → URL 全部失效
    · 甲方 IT 部门不一定能访问盒子的网段
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from sqlalchemy.ext.asyncio import AsyncSession

from server.config import MEDIA_VIDEO_DIR, STORAGE_DIR
from server.db import get_session
from server.services.zip_manifest import alarm_entry, zip_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/openapi/v1/media", tags=["对外开放接口"])

# ★ rate_limit 定义在 open_api.py（限流逻辑共用一份，避免两处实现不一致）
from server.api.open_api import rate_limit  # noqa: E402


def _safe_join(root: Path, rel: str) -> Path | None:
    """安全拼接，阻止 `../` 路径穿越。"""
    try:
        base = root.resolve()
        p = (base / rel.lstrip("/\\")).resolve()
        if base not in p.parents and p != base:
            return None
        return p
    except Exception:
        return None


# ---------------------------------------------------------------------------
# ★★ 批量下载接口（2026-10-27）
#
# 甲方要「直接传文件」而不是给 URL。媒体规模决定了两种做法：
#   · 图片平均 0.07 MB → 可以 base64 内联
#   · 视频平均 32.7 MB → 只能打包流式下载，绝不能内联
# ---------------------------------------------------------------------------


def _media_path(root: Path, rel: str) -> Path | None:
    """把数据库里的 file_path 归一化后拼到 root 上。

    ★ file_path 存的是相对**项目根**的路径（如 ``storage/2026/09/28/x.jpg``），
      而 root 已经指向 ``<项目根>/storage``。直接拼会变成
      ``storage/storage/...``（多一层）。

    这里剥掉冗余前缀：
      · ``storage/``
      · ``media/``
      · 开头的 ``/`` 或 ``\\``
    """
    if not rel:
        return None
    s = str(rel).replace("\\", "/").lstrip("/")
    for prefix in ("storage/", "media/"):
        while s.lower().startswith(prefix):
            s = s[len(prefix) :]
    return _safe_join(root, s)

@router.get(
    "/batch/images",
    summary="★ 批量下载图片（ZIP 流式，一次拿一批）",
)
async def download_images_zip(
    alarm_ids: str = Query(
        ...,
        description="告警 ID 列表，逗号分隔（最多 200 个）",
    ),
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(rate_limit),
):
    """把指定告警的图片打包成 ZIP 流式返回。

    包内 manifest.json 记录每个请求告警对应的文件及跳过原因。

    ZIP 内结构：
        <alarm_id>/<seq>_<原文件名>.jpg
    """
    ids = [x.strip() for x in (alarm_ids or "").split(",") if x.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="alarm_ids 不能为空")
    if len(ids) > 200:
        raise HTTPException(
            status_code=400,
            detail=f"一次最多 200 条，收到 {len(ids)} 条。请分批拉取。",
        )

    from sqlalchemy import select

    from server.models import Alarm

    rows = list(
        (
            await db.execute(select(Alarm).where(Alarm.id.in_(ids)))
        )
        .scalars()
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="这些告警都不存在")

    # 保留请求顺序；重复请求 ID 只登记一次。
    by_id = {a.id: a for a in rows}
    entries = []
    items: list[tuple[str, Path]] = []
    for alarm_id in dict.fromkeys(ids):
        a = by_id.get(alarm_id)
        entry = alarm_entry(alarm_id, a)
        entries.append(entry)
        if a is None:
            continue
        if not a.images:
            entry["reason"] = "no_images"
        for img in sorted(a.images, key=lambda x: x.seq):
            fp = img.file_path
            if not fp:
                entry["skipped_files"].append({"seq": img.seq, "reason": "no_file_path"})
                continue
            abs_path = _media_path(STORAGE_DIR, str(fp))
            if abs_path is None or not abs_path.is_file():
                entry["skipped_files"].append({"seq": img.seq, "reason": "file_missing"})
                continue
            arcname = f"{a.id}/{img.seq}_{abs_path.name}"
            items.append((arcname, abs_path))
            entry["files"].append({"seq": img.seq, "path": arcname})

    if not items:
        raise HTTPException(status_code=404, detail="这些告警没有可下载的图片")

    import time as _t

    fname = f"images_{_t.strftime('%Y%m%d_%H%M%S')}.zip"
    return await zip_response(items, entries, "images", fname)


@router.get(
    "/batch/videos",
    summary="★★ 批量下载视频（ZIP 流式，建议 ≤20 条/次）",
)
async def download_videos_zip(
    alarm_ids: str = Query(
        ...,
        description="告警 ID 列表，逗号分隔（建议 ≤20，最多 50）",
    ),
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(rate_limit),
):
    """把指定告警的视频打包成 ZIP 流式返回。

    ## ⚠️ 重要：请控制批量大小

    实测单个视频平均 **32.7 MB**：
        · 10 条 ≈ 327 MB
        · 20 条 ≈ 654 MB
        · 50 条 ≈ 1.6 GB

    **建议 ≤20 条/次**。超过 50 条会被拒绝。

    ## ZIP 内结构

        <原视频文件名>.mp4
        manifest.json

    只包含 **status=ready** 的视频；共用文件只写入一次，清单保留全部告警映射。
    """
    ids = [x.strip() for x in (alarm_ids or "").split(",") if x.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="alarm_ids 不能为空")
    if len(ids) > 50:
        raise HTTPException(
            status_code=400,
            detail=(
                f"一次最多 50 条视频（平均 32 MB/条，50 条约 1.6 GB）。"
                f"收到 {len(ids)} 条，请分批拉取。"
            ),
        )

    from sqlalchemy import select

    from server.models import Alarm

    rows = list(
        (
            await db.execute(select(Alarm).where(Alarm.id.in_(ids)))
        )
        .scalars()
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="这些告警都不存在")

    items: list[tuple[str, Path]] = []
    missing: list[str] = []
    by_id = {a.id: a for a in rows}
    entries = []
    for alarm_id in dict.fromkeys(ids):
        a = by_id.get(alarm_id)
        entry = alarm_entry(alarm_id, a)
        entries.append(entry)
        if a is None:
            missing.append(f"{alarm_id}(alarm_not_found)")
            continue
        entry["video_status"] = str(getattr(a, "video_status", "") or "not_requested")
        # 只收 ready 的
        if str(getattr(a, "video_status", "")) != "ready":
            entry["reason"] = "video_not_ready"
            missing.append(f"{a.id}({getattr(a, 'video_status', '?')})")
            continue
        url = getattr(a, "video_url", None)
        if not url:
            entry["reason"] = "no_file_path"
            missing.append(f"{a.id}(no_url)")
            continue
        # video_url 形如 /media/video/<file>.mp4 或 <file>.mp4
        name = str(url).split("/")[-1]
        abs_path = _media_path(MEDIA_VIDEO_DIR, name)
        if abs_path is None or not abs_path.is_file():
            entry["reason"] = "file_missing"
            missing.append(f"{a.id}(file_missing)")
            continue
        items.append((name, abs_path))
        entry["files"].append({"path": name})

    if not items:
        raise HTTPException(
            status_code=404,
            detail=(
                "没有可下载的视频。"
                f"跳过原因: {', '.join(missing[:10])}"
                if missing
                else "没有可下载的视频"
            ),
        )

    import time as _t

    fname = f"videos_{_t.strftime('%Y%m%d_%H%M%S')}.zip"
    return await zip_response(
        items, entries, "videos", fname,
        headers={"X-Skipped": ",".join(missing[:5])} if missing else None,
    )


@router.get("/video/{file_path:path}", summary="★ 告警视频片段（前后 30 秒，不鉴权）")
async def get_open_video(file_path: str):
    """视频 MP4 文件。

    URL 形如：/openapi/v1/media/video/<alarm_id>.mp4
    """
    # ⚠️ 路由顺序：video 必须声明在通用 {file_path} 之前，
    #    否则 "video/xxx.mp4" 会被当成图片路径。
    abs_path = _safe_join(MEDIA_VIDEO_DIR, file_path)
    if abs_path is None or not abs_path.is_file():
        raise HTTPException(status_code=404, detail="视频不存在或尚未生成")

    return FileResponse(
        abs_path,
        media_type="video/mp4",
        # 让甲方可以直接用播放器/浏览器打开，或 inline 播放
        headers={"Content-Disposition": f'inline; filename="{abs_path.name}"'},
    )


@router.get("/{file_path:path}", summary="★ 告警图片（不鉴权）")
async def get_open_image(file_path: str):
    """图片文件。

    URL 形如：/openapi/v1/media/2026/09/28/ABC123.jpg
    """
    abs_path = _safe_join(STORAGE_DIR, file_path)
    if abs_path is None or not abs_path.is_file():
        raise HTTPException(status_code=404, detail="图片不存在")

    suffix = abs_path.suffix.lower()
    media_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }.get(suffix, "application/octet-stream")

    return FileResponse(abs_path, media_type=media_type)
