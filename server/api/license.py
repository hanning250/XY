# -*- coding: utf-8 -*-
"""★ 授权接口：查询授权状态 + 续期码核销 + 服务器时间展示。

## 关键设计（2026-10-26 重做）

授权基准是**服务器时间**。到期后客户需要：
  1. 在前端看到「当前服务器时间」
  2. 把这个时间报给供应商
  3. 供应商按这个时间算出一个 **10 分钟窗口有效** 的续期码
  4. 客户输入续期码 → 立刻恢复

`GET /api/license` **不要求登录**：
  到期拦截页要能显示状态和服务器时间，而那时用户可能连登录都没做。
  这些信息只有时间，不敏感。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from server.auth.base import Principal
from server.auth.deps import require
from server.services import license as lic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/license", tags=["授权"])


class LicenseOut(BaseModel):
    """授权状态（前端直接用这些字段）。"""

    # ---- 授权期 ----
    activated_at: str | None = None
    expires_on: str | None = None
    days_left: int = 0
    expired: bool = False
    enforced: bool = True
    customer: str = ""

    # ---- ★ 服务器时间（客户端要报给供应商的）----
    server_now: str = Field(
        "", description="服务器当前时间（授权基准，客户需报给供应商）"
    )
    server_window: str = Field(
        "", description="服务器当前所在的 10 分钟窗口（续期码按此校验）"
    )
    window_minutes: int = Field(10, description="续期码有效窗口（分钟）")
    renew_hint: str = Field("", description="到期时给客户的提示文案")


class RenewIn(BaseModel):
    code: str = Field(
        ...,
        description="续期码，形如 ISUP2-xxxx.yyyy（10 分钟内有效）",
    )


@router.get("", response_model=LicenseOut, summary="查询授权状态与服务器时间")
async def get_license():
    """★ 无需登录。

    到期页要能看到：
      · 到期日 / 剩余天数
      · **服务器当前时间**（客户抄给供应商）
      · 提示文案
    """
    return lic.status()


@router.post("/renew", response_model=LicenseOut, summary="用续期码续期（仅管理员）")
async def renew(
    payload: RenewIn,
    principal: Principal = Depends(require("admin")),
):
    """核销续期码。

    码里的时间窗口必须等于**此刻**服务器的 10 分钟窗口，
    否则报「已失效，请重新报时间」。
    """
    try:
        return lic.apply_renew_code(payload.code)
    except lic.LicenseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/server-time",
    summary="★ 仅返回服务器时间（到期页大字展示用，无需登录）",
)
async def server_time():
    """极简接口：给到期页展示「请把这个时间告诉供应商」。

    单独一个接口是因为到期页可能只想大字号显示时间，
    不想拉整个授权对象。
    """
    now = lic.server_now()
    return {
        "server_now": now.isoformat(timespec="seconds"),
        "server_now_text": now.strftime("%Y-%m-%d %H:%M:%S"),
        "server_window": lic.window_of(now).isoformat(timespec="seconds"),
        "window_minutes": lic.WINDOW_MINUTES,
    }
