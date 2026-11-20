# -*- coding: utf-8 -*-
"""★ JWT 鉴权（登录注册）。

实现要点：
  · token 里携带 **workshops 列表** —— 这是多车间隔离的依据
  · admin（is_superuser）带 superuser=true，可查看全部车间
  · 用标准库自研的 HS256（见 tokens.py），**零第三方依赖**，
    便于离线一键部署（现场内网无外网，少一个依赖少一份打包负担）

安全原则：
  · 解析出的车间列表决定可见范围，**默认拒绝**：
    车间列表为空的普通账号什么都看不到
"""

from __future__ import annotations

import logging

from fastapi import Request

from server.auth.base import ALL_SCOPES, Principal
from server.auth.tokens import TokenError, create_token, decode_token
from server.config import get_settings
from server.models import PrincipalKind, User

logger = logging.getLogger(__name__)

JWT_PREFIX = "Bearer "


def create_access_token(
    subject: str,
    scopes: set[str] | None = None,
    *,
    workshops: list[str] | None = None,
    superuser: bool = False,
    user_id: int | None = None,
    password_version: int | None = None,
) -> str:
    """签发访问令牌。

    ★ workshops 与 superuser 是车间隔离的核心载荷：
        · 普通账号：workshops=["A"] → 只能看 A 车间
        · admin    ：superuser=True  → 可看全部
    ★ pwdv（2026-XX）：签发时刻的密码版本号 —— 任何一方改密后版本 +1，
      旧 token 立即失效（校验见 principal_from_claims）。
    """
    settings = get_settings()
    claims = {
        "sub": subject,
        "scopes": sorted(scopes) if scopes else sorted(ALL_SCOPES),
        "workshops": list(workshops or []),
        "superuser": bool(superuser),
    }
    if user_id is not None:
        claims["uid"] = user_id
    if password_version is not None:
        claims["pwdv"] = int(password_version)
    return create_token(
        claims,
        secret=settings.jwt_secret,
        expires_in=settings.jwt_expire_minutes * 60,
        algorithm=settings.jwt_algorithm,
    )


def verify_access_token(token: str) -> dict:
    """校验并解析令牌。失败抛 TokenError。"""
    settings = get_settings()
    return decode_token(token, secret=settings.jwt_secret)


class JwtProvider:
    """从 Authorization: Bearer <token> 解析用户身份。"""

    name = "jwt"

    async def authenticate(self, request: Request) -> Principal | None:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith(JWT_PREFIX):
            return None
        token = auth[len(JWT_PREFIX):].strip()
        if not token:
            return None
        try:
            claims = verify_access_token(token)
        except TokenError:
            return None
        except Exception:
            logger.exception("JWT 解析异常")
            return None
        return await principal_from_claims(claims)


# --------------------------------------------------------------------------
# ★ 密码版本号（2026-XX：任何一方改密后旧 token 立即失效）
#
# JWT 无状态、签出去收不回。轻量吊销：
#   · User.password_version 整型计数器，set_password 时 +1；
#   · 登录签发时把当前版本写进 claims["pwdv"]；
#   · principal_from_claims 里与数据库当前值比对，不一致 → 拒绝。
# 无 pwdv 的旧 token（升级前签发的）按匹配处理，由 enabled 校验兜底。
# --------------------------------------------------------------------------


async def principal_from_claims(claims: dict) -> Principal | None:
    """★ 由 JWT claims 构造身份，并校验账号当前状态（2026-XX 安全审查新增）。

    所有接受 token 的入口（HTTP / WebSocket / 媒体 / 内部文档页）
    统一走这里，保证行为一致。

    吊销语义（无状态 JWT 的轻量补偿）：
      · 账号已被删除，或已被管理员停用（enabled=False）→ 返回 None（401）
        —— 停用账号后旧 token 立即失效，而不是等它自然过期（最长 12h）。

    代价：每个带 token 的请求多一次主键查询（SQLite 本地、索引命中，
    实测 <1ms），换来「停用/删除即刻生效」，值得。
    """
    from server.db import SessionLocal

    workshops = claims.get("workshops") or []
    if isinstance(workshops, str):
        workshops = [workshops]

    subject = str(claims.get("sub", ""))
    uid = claims.get("uid")

    async with SessionLocal() as db:
        user = None
        if uid is not None:
            user = await db.get(User, uid)
        if user is None and subject:
            # uid 缺失（旧 token）时按用户名兜底
            from server.crud.user import get_by_username

            user = await get_by_username(db, subject)
        if user is None or not user.enabled:
            logger.info("token 拒绝：账号不存在或已停用 sub=%s uid=%s", subject, uid)
            return None
        # ★ 密码版本号比对：改密（自助/管理员重置）后旧 token 立即失效
        token_pwdv = claims.get("pwdv")
        if token_pwdv is not None and int(token_pwdv) != int(
            getattr(user, "password_version", 0) or 0
        ):
            logger.info("token 拒绝：密码已变更 sub=%s uid=%s", subject, uid)
            return None
        # 以数据库当前状态为准（停用前的车间授权变更也应生效）
        effective_user_id = user.id

    # ★★ 2026-10-27 安全修复：scopes 兜底不能是 ALL_SCOPES
    #
    #   原来 `or ALL_SCOPES`：token 里没有 scopes（旧 token）或
    #   scopes 为空时，直接给**全部权限**（含 admin）。
    #   如果登录时按角色裁剪后普通账号的 scope 集为空，
    #   这个兜底会把它升级成管理员。
    #
    #   改为按 superuser 标记推导：admin 给全量，普通账号给只读。
    _is_super = bool(claims.get("superuser"))
    _raw_scopes = claims.get("scopes")
    if _raw_scopes:
        _scopes = set(_raw_scopes)
    else:
        # 旧 token / 空 scope：按角色给默认权限集
        from server.auth.base import scopes_for_role

        _scopes = scopes_for_role(superuser=_is_super)
        logger.debug(
            "token 无 scopes，按角色推导: sub=%s superuser=%s → %s",
            subject,
            _is_super,
            sorted(_scopes),
        )

    return Principal(
        kind=PrincipalKind.USER.value,
        subject=subject,
        scopes=_scopes,
        # tenant 保留为「主车间」（兼容既有代码），
        # tenants 是完整列表（admin 可多车间）
        tenant=(workshops[0] if workshops else None),
        tenants=[str(w) for w in workshops],
        superuser=bool(claims.get("superuser")),
        user_id=effective_user_id,
    )
