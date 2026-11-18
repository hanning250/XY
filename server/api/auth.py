# -*- coding: utf-8 -*-
"""★ 登录 / 身份 接口。"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.base import Principal
from server.auth.deps import current_principal, require
from server.auth.jwt_auth import create_access_token
from server.auth.tokens import verify_password
from server.config import get_settings
from server.crud import user as user_crud
from server.db import get_session
from server.schemas import LoginIn, PasswordChangeIn, PrincipalOut, TokenOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["鉴权"])

# ★ 媒体鉴权 Cookie 名（登录时签发，媒体路由从 Cookie 取 token）
MEDIA_TOKEN_COOKIE = "isup_media_token"

# --------------------------------------------------------------------------
# ★ 登录失败限流（2026-XX 安全审查新增，内存版、单进程足够——本项目必须单 worker）
#   同一 (IP, 用户名) 在窗口内失败超过阈值 → 429，防在线爆破。
#   PBKDF2 20 万轮下每次失败约烧 100ms CPU，限流同时也是一种 DoS 防护。
# --------------------------------------------------------------------------
_FAIL_WINDOW_SECONDS = 300.0   # 5 分钟窗口
_FAIL_MAX = 10                 # 窗口内最多失败次数
_fail_log: dict[tuple[str, str], list[float]] = {}


def _register_login_failure(ip: str, username: str) -> None:
    key = (ip, username)
    now = time.monotonic()
    bucket = [t for t in _fail_log.get(key, []) if now - t < _FAIL_WINDOW_SECONDS]
    bucket.append(now)
    _fail_log[key] = bucket
    if len(_fail_log) > 5000:  # 防止字典被恶意刷大
        cutoff = now - _FAIL_WINDOW_SECONDS
        for k in [k for k, v in _fail_log.items() if not v or v[-1] < cutoff]:
            _fail_log.pop(k, None)


def _login_throttled(ip: str, username: str) -> bool:
    bucket = _fail_log.get((ip, username), [])
    return len(bucket) >= _FAIL_MAX


@router.get("/config", summary="前端启动时拉取鉴权配置")
async def auth_config():
    """前端据此决定是否显示登录页，以及整页缩放（现场大屏适配）。"""
    settings = get_settings()
    mode = settings.auth_mode.lower()
    return {
        "auth_mode": mode,
        "login_enabled": mode == "jwt",
        "workshop_isolation": mode == "jwt",
        # ★ 大屏适配：前端启动时写进 <html style="zoom">，改配置不用重新构建前端
        "ui_scale": settings.ui_scale,
    }


@router.post("/login", response_model=TokenOut, summary="★ 登录")
async def login(payload: LoginIn, request: Request, db: AsyncSession = Depends(get_session)):
    """用户名密码登录，返回 JWT。

    token 里带 workshops 列表 → 决定该账号能看哪些车间。
    """
    settings = get_settings()
    if settings.auth_mode.lower() != "jwt":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "登录未启用。请在 server/.env 里设置 ISUP_AUTH_MODE=jwt 后重启服务。"
            ),
        )

    client_ip = request.client.host if request.client else "-"
    if _login_throttled(client_ip, payload.username):
        logger.warning("登录已被限流: %s from %s", payload.username, client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="失败次数过多，请 5 分钟后再试",
            headers={"Retry-After": "300"},
        )

    user = await user_crud.authenticate(
        db, username=payload.username, password=payload.password
    )
    if user is None:
        _register_login_failure(client_ip, payload.username)
        logger.warning("登录失败: %s from %s", payload.username, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    workshops = await user_crud.list_user_workshops(db, user.id)
    token = create_access_token(
        user.username,
        workshops=workshops,
        superuser=bool(user.is_superuser),
        user_id=user.id,
        password_version=int(getattr(user, "password_version", 0) or 0),
    )
    logger.info(
        "登录成功: %s (superuser=%s, 车间=%s)",
        user.username,
        user.is_superuser,
        workshops or "-",
    )

    # ★ 响应体必须是 {access_token, token_type, expires_in} ——
    #   这是前端 LoginView 依赖的既有契约，不能改。
    #   （2026-XX 曾误加 {code,data} 信封导致前端拿到 undefined，
    #     登录后立刻失效 —— 已还原。）
    payload = TokenOut(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
    )
    response = JSONResponse(content=payload.model_dump(mode="json"))
    # ★ 同时把 token 写进 HttpOnly Cookie（2026-XX 安全审查）：
    #   <img>/<video> 带不了 Authorization 头，原来只能把 JWT 拼进 URL
    #   query —— 会进浏览器历史 / Referer / 代理日志。Cookie 方案下
    #   浏览器对同源媒体请求自动携带，前端不再需要 withToken()。
    #   HttpOnly → JS 读不到，防 XSS 偷 token；SameSite=Lax → CSRF 面
    #   最小（媒体是 GET 只读；写操作仍走 Authorization 头）。
    response.set_cookie(
        key=MEDIA_TOKEN_COOKIE,
        value=token,
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        samesite="lax",
        # 内网 http 部署，secure=False；若上 https 建议改为 True
        secure=False,
        path="/",
    )
    return response


@router.get("/me", response_model=PrincipalOut, summary="当前身份")
async def me(
    principal: Principal = Depends(current_principal),
    db: AsyncSession = Depends(get_session),
):
    workshops = await user_crud.list_user_workshops(db, principal.user_id or -1)
    return PrincipalOut(
        kind=principal.kind,
        subject=principal.subject,
        scopes=sorted(principal.scopes),
        workshops=workshops,
        superuser=principal.superuser,
    )


@router.put("/password", summary="★ 修改自己的密码")
async def change_password(
    payload: PasswordChangeIn,
    response: JSONResponse,
    principal: Principal = Depends(current_principal),
    db: AsyncSession = Depends(get_session),
):
    """任何登录用户自助修改密码；旧密码校验失败返回 400。"""
    if not principal.user_id:
        raise HTTPException(status_code=400, detail="当前身份不支持修改密码")
    u = await user_crud.get_by_id(db, principal.user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    if not verify_password(payload.old_password, u.password_hash):
        raise HTTPException(status_code=400, detail="旧密码不正确")
    await user_crud.set_password(db, user=u, password=payload.new_password)
    logger.info("用户 %s 已修改自己的密码", u.username)
    # ★ 密码变了 → 旧 token 全部失效，媒体 Cookie 也一并清掉
    response.delete_cookie(key=MEDIA_TOKEN_COOKIE, path="/")
    return {"code": 0, "message": "密码已修改，请使用新密码重新登录"}
