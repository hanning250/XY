# -*- coding: utf-8 -*-
"""★ 受车间隔离保护的媒体文件服务。

★★ 为什么必须替换 StaticFiles：

    原来 `app.mount("/media", StaticFiles(...))` 是**完全公开**的 ——
    任何人只要知道 URL（形如 /media/2026/09/28/ABC123.jpg）就能下载图片，
    **绕过所有接口鉴权**。这是比查询泄露更直接的泄露：
    B 车间的人拿到 A 车间的图片 URL 就能看图。

    所以改成带鉴权的路由：按 file_path 反查 alarm_image → alarm.workshop，
    再用 Principal 校验可见性。

★ 两种鉴权方式都支持：
    ① Authorization: Bearer <jwt>   （前端 img 请求带不了头，所以主要靠②）
    ② ?token=<jwt>                  （前端 <img src> 用这个）

    ⚠️ 注意：<img> 标签无法自定义请求头，所以前端展示图片时
       必须把 token 拼进 query。前端 api.ts 里已按此约定实现。
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.base import Principal
from server.api.auth import MEDIA_TOKEN_COOKIE
from server.auth.tokens import TokenError, decode_token
from server.config import MEDIA_VIDEO_DIR, STORAGE_DIR, get_settings
from server.db import SessionLocal
from server.models import Alarm, AlarmImage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["媒体"])


async def _principal_from_request(
    request: Request, token: str | None, cookie_token: str | None = None
) -> Principal | None:
    """从 header / Cookie / query 解析身份（优先级从高到低）。

    ★ 主路径：**HttpOnly Cookie**（登录时签发）；
      query ?token= 仅作兼容兜底。
    """
    settings = get_settings()

    raw = ""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        raw = auth[7:].strip()
    if not raw and cookie_token:
        raw = cookie_token.strip()
    if not raw and token:
        raw = token.strip()

    if not raw:
        return None
    try:
        claims = decode_token(raw, secret=settings.jwt_secret)
    except TokenError:
        return None

    from server.auth.jwt_auth import principal_from_claims

    return await principal_from_claims(claims)


def _safe_join(root: Path, rel: str) -> Path | None:
    """把相对路径安全地拼到 root 下，阻止 ../ 穿越。"""
    try:
        p = (root / rel.lstrip("/\\")).resolve()
        root_r = root.resolve()
        if root_r not in p.parents and p != root_r:
            return None
        return p
    except Exception:
        return None


async def _can_access_image(
    db: AsyncSession, *, rel_path: str, principal: Principal
) -> bool:
    """判断该身份能否访问这个图片文件。

    ★ 默认拒绝：查不到归属的图片，只有可看全部的身份能访问。
    """
    visible = principal.visible_workshops()

    # 查这张图挂在哪个告警上
    stmt = (
        select(Alarm.workshop)
        .join(AlarmImage, AlarmImage.alarm_id == Alarm.id)
        .where(AlarmImage.file_path == rel_path)
        .limit(1)
    )
    row = (await db.execute(stmt)).first()

    if row is None:
        # 未入库的图片（等待配对 / 孤儿）：只有全部可见者能看
        return visible is None

    ws = row[0]
    if visible is None:
        return True
    if not visible:
        return False
    return ws in visible


@router.get("/media/video/{file_path:path}", summary="★ 告警视频（按车间隔离）")
async def get_video(
    file_path: str,
    request: Request,
    token: str | None = Query(None, description="兼容兜底；新前端走 HttpOnly Cookie"),
):
    """受保护的视频文件。视频通过告警的 video_url 关联到车间。

    ⚠️ 路由顺序：本路由必须声明在下方 `/media/{file_path:path}` 之前 ——
    Starlette 按声明顺序匹配，path 参数会吞掉一切前缀，
    若图片路由在前，`/media/video/x.mp4` 会被当成
    file_path="video/x.mp4" 的**图片**去找 storage/video/x.mp4 → 永远 404。
    （open_media.py 同一处也有一模一样的注释，两个文件要一起改。）
    """
    principal = await _principal_from_request(
        request, token, cookie_token=request.cookies.get(MEDIA_TOKEN_COOKIE)
    )
    if principal is None:
        raise HTTPException(status_code=401, detail="未认证")

    abs_path = _safe_join(MEDIA_VIDEO_DIR, file_path)
    if abs_path is None or not abs_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")

    visible = principal.visible_workshops()
    if visible is not None:
        marker = f"/media/video/{file_path}"
        async with SessionLocal() as db:
            stmt = (
                select(Alarm.workshop)
                .where(Alarm.video_url.like(f"%{marker}%"))
                .limit(1)
            )
            row = (await db.execute(stmt)).first()
        ws = row[0] if row else None
        if not visible or ws not in visible:
            raise HTTPException(status_code=404, detail="文件不存在")

    # ★ 缓存策略：`no-cache` = 每次都带 ETag 向服务器确认（文件没变 → 304，零流量；
    #   文件被转码替换 → 立即拿到新字节）。
    #   ⚠️ 不能用 max-age 强缓存：2026-10 把存量 HEVC 批量转成 H.264 后发现，
    #   同一 URL 的旧（播不了）响应被浏览器缓存 1 天，转码完用户点开还是旧字节，
    #   表现为「修复了还是报没有找到支持的视频格式」。播放中拖动进度条的
    #   Range 请求本来就会命中已下载的字节，无需靠强缓存。
    return FileResponse(
        abs_path,
        headers={"Cache-Control": "private, no-cache"},
    )


@router.get("/media/{file_path:path}", summary="★ 告警图片（按车间隔离）")
async def get_media(
    file_path: str,
    request: Request,
    token: str | None = Query(
        None, description="兼容兜底；新前端走 HttpOnly Cookie"
    ),
):
    """受保护的告警图片。

    相对路径形如 2026/09/28/ABC123.jpg，对应 storage/ 下的同名文件。
    鉴权优先级：Authorization 头 > HttpOnly Cookie > ?token=（兜底）。
    """
    principal = await _principal_from_request(
        request, token, cookie_token=request.cookies.get(MEDIA_TOKEN_COOKIE)
    )
    if principal is None:
        raise HTTPException(status_code=401, detail="未认证")

    abs_path = _safe_join(STORAGE_DIR, file_path)
    if abs_path is None or not abs_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")

    rel = f"storage/{file_path}".replace("\\", "/")
    async with SessionLocal() as db:
        if not await _can_access_image(db, rel_path=rel, principal=principal):
            # 用 404 而非 403：不泄露「文件存在但不属于你」
            raise HTTPException(status_code=404, detail="文件不存在")

    # ★ 内容不可变（告警图不会改写），强缓存 1 天 + 7 天 stale-while-revalidate。
    #   没有它，浏览器每次回到列表都要重新下载 24 张缩略图 —— 返回列表
    #   时图片逐张刷新，视觉上就是「加载一会」。媒体 URL 带 token，
    #   同一 URL 换 token 会重新拉一次，影响可忽略（token 有效期 12h）。
    return FileResponse(
        abs_path,
        headers={
            "Cache-Control": "private, max-age=86400, stale-while-revalidate=604800"
        },
    )
