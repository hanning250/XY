# -*- coding: utf-8 -*-
"""★★ 软件授权（基于**服务器时间** + 激活码续期）—— 2026-10-26 重做。

## 设计目标（现场需求）

原来：授权期 = 首次启动时间 + N 天，本地文件记录。
问题：客户可以改系统时间 / 删文件重来，且我们无法远程控制。

新方案：**以服务器时间为准，用激活码控制有效期。**

    1. 部署到客户服务器 → 首次启动记录「激活时间」
    2. 有效期 = 激活时间 + N 天（默认 365）
    3. 到期后业务全部 403，只剩「授权页」
    4. ★ 客户在前端看到「当前服务器时间」并报给我们
    5. ★ 我们用它 + 密钥算出一个**续期码**（10 分钟窗口有效）
    6. 客户输入续期码 → 立刻恢复

## 为什么用「服务器时间 + 10 分钟窗口」而不是纯日期

客户报的时间可能有几分钟误差（抄错、时区、延迟）。
如果续期码绑定到「精确到秒」，客户抄错一位就废了。

所以续期码绑定的是「**10 分钟窗口**」：
    窗口 = 服务器时间向下取整到 10 分钟
    例如 2026-10-26 16:36:13 → 窗口 2026-10-26 16:30

我们按客户报的时间算窗口 → 生成码；
客户在自己机器上输入 → 服务端按**自己的当前时间**算窗口 → 比对。
只要在同一个 10 分钟窗口内，就一定匹配。

★ 这既是安全边界（过期码不能用），也是容错设计（允许几分钟误差）。

## 续期码格式

    ISUP2-<base64url(payload)>.<sig16>

    payload = {"w":"2026-10-26T16:30", "exp":"2027-10-26", "id":"<客户名>"}
        w   = 10 分钟窗口起点（服务器时间）
        exp = 新的到期日（YYYY-MM-DD）
        id  = 客户标识（可选）

    sig16 = HMAC-SHA256(secret, payload_b64)[:16]

## 防篡改

  · 客户改系统时间到过去/未来 → 窗口对不上 → 码无效
  · 客户把码给别人 → 别人机器时间不同 → 无效
  · 客户删 data/license.json → 重新激活（已知取舍：无法完全防重装，
    但足以约束正常客户）

## 与旧版（ISUP1）兼容

旧码 ISUP1-<payload>.<sig> 仍可解析（按到期日直接续期，
不校验时间窗口），避免已发出去的码失效。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path

from server.config import PROJECT_ROOT, get_settings

logger = logging.getLogger(__name__)

CODE_PREFIX_V2 = "ISUP2"
CODE_PREFIX_V1 = "ISUP1"

# 续期码的时间窗口（分钟）
WINDOW_MINUTES = 10

_lock = threading.RLock()
_state: dict | None = None


class LicenseError(Exception):
    """授权码非法 / 无法续期。"""


# --------------------------------------------------------------------------
# 时间工具
# --------------------------------------------------------------------------
def server_now() -> datetime:
    """★ 服务器当前时间（本地时区）。

    这是**授权的唯一时间基准**。客户在前端看到的就是它。
    """
    return datetime.now().replace(microsecond=0)


def window_of(dt: datetime, minutes: int = WINDOW_MINUTES) -> datetime:
    """把时刻向下取整到 N 分钟窗口。

    ★ 客户报时间可能抄错/延迟几分钟。用窗口比对，
      只要在同一个窗口内就通过 —— 容错但不失安全。
    """
    total = dt.hour * 60 + dt.minute
    bucket = (total // minutes) * minutes
    return dt.replace(
        hour=bucket // 60, minute=bucket % 60, second=0, microsecond=0
    )


def _window_key(dt: datetime) -> str:
    """窗口的可读字符串（写进码里）。"""
    return window_of(dt).strftime("%Y-%m-%dT%H:%M")


# --------------------------------------------------------------------------
# 签名
# --------------------------------------------------------------------------
def _secret() -> bytes:
    s = get_settings()
    return (s.license_secret or "isup-license-change-me").encode()


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64d(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def _sign(payload_b64: str) -> str:
    """HMAC-SHA256 前 16 位（短、够用、便于人工抄）。"""
    return hmac.new(
        _secret(), payload_b64.encode(), hashlib.sha256
    ).hexdigest()[:16]


# --------------------------------------------------------------------------
# 状态文件
# --------------------------------------------------------------------------
def _path() -> Path:
    s = get_settings()
    if s.license_file:
        p = Path(s.license_file)
        return p if p.is_absolute() else PROJECT_ROOT / p
    return PROJECT_ROOT / "data" / "license.json"


def _write(st: dict) -> None:
    """原子写：先写临时文件再替换，避免断电留下半个 JSON。"""
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _read() -> dict | None:
    path = _path()
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("授权文件损坏，将重新激活: %s", path)
        return None


# --------------------------------------------------------------------------
# 激活 / 读取
# --------------------------------------------------------------------------
def _activate() -> dict:
    """首次启动即激活：激活日 = 服务器当前时间。"""
    s = get_settings()
    now = server_now()
    days = max(1, int(s.license_days or 365))
    st = {
        "v": 2,
        "activated_at": now.isoformat(timespec="seconds"),
        "expires_on": (now + timedelta(days=days)).strftime("%Y-%m-%d"),
        "days": days,
        "customer": "",
        "history": [],
        "note": "首次启动自动激活，有效期以服务器时间为准",
    }
    _write(st)
    logger.info(
        "★ 授权已激活：%s 起，%s 到期（%d 天，基准=服务器时间）",
        st["activated_at"],
        st["expires_on"],
        days,
    )
    return st


def get_state() -> dict:
    """取授权状态（首次调用会激活）。"""
    global _state
    with _lock:
        if _state is not None:
            return _state
        st = _read()
        if st is None or not st.get("expires_on"):
            st = _activate()
        _state = st
        return st


def reload_state() -> dict:
    """强制从文件重读（续期后调用）。"""
    global _state
    with _lock:
        _state = None
    return get_state()


# --------------------------------------------------------------------------
# 状态计算
# --------------------------------------------------------------------------
def status() -> dict:
    """当前授权状态（给前端展示）。

    字段：
      activated_at  激活时间
      expires_on    到期日
      days_left     剩余天数（可为负）
      expired       是否已过期
      server_now    服务器当前时间（★ 客户要报给我们的那个）
      server_window 服务器当前所在的 10 分钟窗口（便于我们对齐）
      renew_hint    给客户的提示
    """
    st = get_state()
    now = server_now()
    try:
        exp = datetime.strptime(st["expires_on"], "%Y-%m-%d")
    except (KeyError, ValueError):
        exp = now

    # 到期日当天 23:59:59 之前都算有效
    end = exp.replace(hour=23, minute=59, second=59)
    delta = end - now
    days_left = delta.days
    expired = delta.total_seconds() < 0
    enforce = bool(get_settings().license_enforce)

    return {
        "activated_at": st.get("activated_at"),
        "expires_on": st.get("expires_on"),
        "days_left": days_left,
        "expired": expired,
        "enforced": enforce,
        "customer": st.get("customer", ""),
        # ★ 客户需要报给我们的字段
        "server_now": now.isoformat(timespec="seconds"),
        "server_window": window_of(now).isoformat(timespec="seconds"),
        "window_minutes": WINDOW_MINUTES,
        "renew_hint": (
            f"授权已到期。请把「服务器时间」"
            f"{now.strftime('%Y-%m-%d %H:%M')} 告诉供应商，"
            f"我们会给您一个续期码（{WINDOW_MINUTES} 分钟内有效）。"
            if expired
            else ""
        ),
    }


def is_expired() -> bool:
    """业务接口是否该拦截。"""
    s = get_settings()
    if not s.license_enforce:
        return False
    return bool(status()["expired"])


# --------------------------------------------------------------------------
# 续期码：生成（供应商侧）与核销（客户侧）
# --------------------------------------------------------------------------
def make_renew_code(
    *,
    server_time: datetime,
    expire_on: str = "",
    customer: str = "",
    days: int | None = None,
) -> str:
    """★ 供应商侧：根据客户报的服务器时间，生成续期码。

    参数：
        server_time  客户报的服务器时间（窗口内即可，不必精确）
        expire_on    新的到期日 "YYYY-MM-DD"；不传则按 days 往后推
        customer     客户标识（写进码里，便于留痕）
        days         从 server_time 起再加多少天

    返回：ISUP2-xxxx.yyyy
    """
    st = get_state()
    base_days = int(days if days is not None else (st.get("days") or 365))
    if not expire_on:
        expire_on = (server_time + timedelta(days=base_days)).strftime("%Y-%m-%d")

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", expire_on):
        raise LicenseError(f"到期日格式应为 YYYY-MM-DD，收到: {expire_on}")

    payload = {
        "w": _window_key(server_time),
        "exp": expire_on,
    }
    if customer:
        payload["id"] = customer

    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    b64 = _b64e(raw.encode())
    sig = _sign(b64)
    return f"{CODE_PREFIX_V2}-{b64}.{sig}"


def _parse_v2(code: str) -> dict:
    """解析并校验 ISUP2 码（含时间窗口校验）。"""
    body = code[len(CODE_PREFIX_V2) + 1 :]
    if "." not in body:
        raise LicenseError("续期码格式错误（缺少签名分隔符）")
    b64, sig = body.rsplit(".", 1)

    if not hmac.compare_digest(_sign(b64), sig):
        raise LicenseError("续期码签名不匹配（可能抄错了，或不是本系统的码）")

    try:
        payload = json.loads(_b64d(b64))
    except Exception as exc:
        raise LicenseError(f"续期码内容无法解析: {exc}") from exc

    # ★ 时间窗口校验：只能用「当前这 10 分钟」的码
    now_win = _window_key(server_now())
    code_win = str(payload.get("w", ""))
    if code_win != now_win:
        raise LicenseError(
            f"续期码已失效（码要求窗口 {code_win}，当前 {now_win}）。"
            f"请重新报一次服务器时间，我们会给您新的码。"
        )
    return payload


def _parse_v1(code: str) -> dict:
    """旧版 ISUP1 码（不校验时间窗口，只按到期日续期）。"""
    body = code[len(CODE_PREFIX_V1) + 1 :]
    if "." not in body:
        raise LicenseError("授权码格式错误")
    b64, sig = body.rsplit(".", 1)
    if not hmac.compare_digest(_sign(b64), sig):
        raise LicenseError("授权码签名不匹配")

    payload = json.loads(_b64d(b64))
    exp = payload.get("exp") or payload.get("expires_on")
    if not exp:
        raise LicenseError("授权码缺少到期日")
    return {"exp": str(exp)[:10], "w": None, "id": payload.get("id", "")}


def apply_renew_code(code: str, *, customer: str = "") -> dict:
    """★ 客户侧：核销续期码，写入新的到期日。

    兼容 ISUP1（旧码）与 ISUP2（新码）。
    成功后立即 reload，业务接口恢复。
    """
    code = (code or "").strip()
    if not code:
        raise LicenseError("请输入续期码")

    if code.startswith(CODE_PREFIX_V2):
        payload = _parse_v2(code)
    elif code.startswith(CODE_PREFIX_V1):
        payload = _parse_v1(code)
    else:
        raise LicenseError(
            f"无法识别的码（应以 {CODE_PREFIX_V2}- 或 {CODE_PREFIX_V1}- 开头）"
        )

    new_exp = str(payload.get("exp", ""))[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", new_exp):
        raise LicenseError(f"码里的到期日非法: {new_exp!r}")

    # 只能往后延，不能缩短
    st = get_state()
    old_exp = st.get("expires_on") or ""
    if old_exp and new_exp < old_exp:
        raise LicenseError(
            f"新到期日 {new_exp} 早于当前 {old_exp}，不允许缩短授权"
        )

    st["expires_on"] = new_exp
    st["v"] = 2
    if payload.get("id"):
        st["customer"] = payload["id"]
    elif customer:
        st["customer"] = customer
    st.setdefault("history", []).append(
        {
            "at": server_now().isoformat(timespec="seconds"),
            "code_prefix": code[:12],
            "new_expires_on": new_exp,
            "window": payload.get("w"),
        }
    )
    _write(st)
    reload_state()
    logger.info("★ 授权已续期：%s → %s", old_exp or "(未设)", new_exp)
    return status()
