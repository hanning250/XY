# -*- coding: utf-8 -*-
"""★ 无依赖的 JWT (HS256) 与密码哈希实现。

为什么不用 PyJWT / passlib（重要）：

    本项目的交付要求是「**一键离线安装**」（给视觉工程师 + 硬件工程师现场部署），
    而现场内网**没有外网**。每多一个第三方依赖，就多一份离线 wheel 要打包、
    多一个版本冲突风险。

    JWT 的 HS256 本质就是 `HMAC-SHA256 + base64url`，
    密码哈希用标准库 `hashlib.pbkdf2_hmac` 即可（NIST 认可的方案）。
    两者都在标准库里，**零依赖、零打包负担、跨平台一致**。

    因此这里自己实现，而不是引入 PyJWT / passlib / bcrypt。

安全要点：
    · 密钥必须来自配置（ISUP_JWT_SECRET），生产环境**必须改掉默认值**
    · 密码用 PBKDF2-HMAC-SHA256，20 万轮，每用户独立随机 salt
    · 校验用 hmac.compare_digest（防时序攻击）
    · JWT 带 exp，过期即失效
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

# --------------------------------------------------------------------------
# base64url（无 padding，JWT 规范）
# --------------------------------------------------------------------------
def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


# --------------------------------------------------------------------------
# 密码哈希（PBKDF2-HMAC-SHA256）
# --------------------------------------------------------------------------
PBKDF2_ROUNDS = 200_000
PBKDF2_PREFIX = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    """生成密码哈希。

    格式：pbkdf2_sha256$<轮数>$<salt_hex>$<hash_hex>
    自带算法与轮数，将来升级轮数时旧密码仍可校验。
    """
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return f"{PBKDF2_PREFIX}${PBKDF2_ROUNDS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    """校验密码。格式非法一律返回 False（不抛异常）。"""
    if not stored:
        return False
    try:
        algo, rounds_s, salt_hex, hash_hex = stored.split("$")
        if algo != PBKDF2_PREFIX:
            return False
        rounds = int(rounds_s)
        salt = bytes.fromhex(salt_hex)
        expect = bytes.fromhex(hash_hex)
    except (ValueError, AttributeError):
        return False

    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    # 必须用 compare_digest，避免时序侧信道
    return hmac.compare_digest(dk, expect)


# --------------------------------------------------------------------------
# JWT (HS256)
# --------------------------------------------------------------------------
class TokenError(Exception):
    """token 无效/过期。"""


def _sign(msg: bytes, secret: str) -> bytes:
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).digest()


def create_token(
    claims: dict[str, Any],
    *,
    secret: str,
    expires_in: int = 720 * 60,
    algorithm: str = "HS256",
) -> str:
    """签发 JWT。"""
    if algorithm != "HS256":
        raise ValueError(f"仅支持 HS256，收到 {algorithm}")

    now = int(time.time())
    payload = dict(claims)
    payload.setdefault("iat", now)
    payload["exp"] = now + int(expires_in)

    header = {"alg": "HS256", "typ": "JWT"}
    seg = (
        _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        + "."
        + _b64url_encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    )
    sig = _b64url_encode(_sign(seg.encode("ascii"), secret))
    return f"{seg}.{sig}"


def decode_token(token: str, *, secret: str, leeway: int = 0) -> dict[str, Any]:
    """校验并解析 JWT。失败抛 TokenError。"""
    if not token or token.count(".") != 2:
        raise TokenError("格式非法")

    seg, _, sig = token.rpartition(".")
    expect = _b64url_encode(_sign(seg.encode("ascii"), secret))
    if not hmac.compare_digest(sig, expect):
        raise TokenError("签名不匹配")

    try:
        payload = json.loads(_b64url_decode(seg.split(".", 1)[1]).decode("utf-8"))
    except Exception as exc:
        raise TokenError(f"载荷解析失败: {exc}") from exc

    exp = payload.get("exp")
    if exp is not None and int(time.time()) > int(exp) + leeway:
        raise TokenError("已过期")

    return payload
