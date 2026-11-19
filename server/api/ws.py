# -*- coding: utf-8 -*-
"""内部 API：WebSocket 实时推送（★ 按车间分房间）。

★★ 为什么必须分房间：

    原来 bus 是**全局广播** —— 所有订阅者都收到所有消息。
    这意味着即使 HTTP 接口做了车间隔离，**B 车间仍然能在 WebSocket 里
    实时收到 A 车间的告警**。这是**数据泄露**，不是体验问题。

    所以这里在连接建立时就确定该身份的可见车间，
    只把它加进对应房间；推送时按房间投递。

鉴权方式：
    WebSocket 无法自定义请求头，所以 token 走 query 参数：
        ws://host/api/ws/alarms?token=<jwt>
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.auth.base import Principal
from server.auth.tokens import TokenError, decode_token
from server.config import get_settings
from server.services.bus import bus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["内部-实时"])

# ⚠️ /auth/* 接口已迁移到 server/api/auth.py（登录 + 身份 + 车间权限）。

ws_router = APIRouter()


async def _principal_from_ws(websocket: WebSocket) -> Principal | None:
    """从 query 参数解析 WebSocket 身份。

    返回 None 表示鉴权失败（调用方应关闭连接）。
    """
    settings = get_settings()
    token = websocket.query_params.get("token", "").strip()
    if not token:
        return None
    try:
        claims = decode_token(token, secret=settings.jwt_secret)
    except TokenError as exc:
        logger.info("WS 鉴权失败: %s", exc)
        return None

    # ★ 统一走 principal_from_claims：含「账号已停用/删除即拒绝」校验
    from server.auth.jwt_auth import principal_from_claims

    return await principal_from_claims(claims)


@ws_router.websocket("/ws/alarms")
async def ws_alarms(websocket: WebSocket):
    """★ 告警实时推送（按车间隔离）。

    鉴权：query 参数 ?token=<jwt>
    房间：按该身份可见的车间订阅，**只收本车间的消息**
    """
    principal = await _principal_from_ws(websocket)
    if principal is None:
        # 1008 = policy violation
        await websocket.close(code=1008, reason="未认证")
        logger.info("WS 连接被拒：未携带有效 token")
        return

    await websocket.accept()

    # ★ 该连接可见的车间（None = 全部）
    visible = principal.visible_workshops()

    queue = bus.subscribe(workshops=visible)
    logger.info(
        "WS 客户端接入: %s（车间=%s），当前订阅数 %d",
        principal.subject,
        visible if visible is not None else "全部",
        bus.subscriber_count,
    )

    try:
        await websocket.send_json(
            {
                "type": "hello",
                "data": {
                    "ok": True,
                    "subject": principal.subject,
                    "workshops": visible,
                    "superuser": principal.superuser,
                },
            }
        )

        # 同时监听客户端消息（心跳）与事件队列
        async def _reader():
            while True:
                await websocket.receive_text()

        reader = asyncio.create_task(_reader())
        try:
            while True:
                getter = asyncio.create_task(queue.get())
                done, pending = await asyncio.wait(
                    {getter, reader}, return_when=asyncio.FIRST_COMPLETED
                )
                if reader in done:
                    getter.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await getter
                    break
                message = getter.result()
                await websocket.send_json(message)
        finally:
            reader.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await reader

    except WebSocketDisconnect:
        logger.info("WS 客户端断开")
    except Exception:
        logger.exception("WS 处理异常")
    finally:
        bus.unsubscribe(queue)
        with contextlib.suppress(Exception):
            await websocket.close()
