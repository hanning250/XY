# -*- coding: utf-8 -*-
"""事件总线：把 SDK 回调线程与 asyncio 世界隔开。

★ 设计要点（docs 风险 R7）：
   C 回调运行在 SDK 自己的线程里，不能 await、不能碰 DB。
   回调里只做 memcpy + call_soon_threadsafe 丢队列，
   真正的解析/IO 由 Correlator 的消费协程处理。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self, maxsize: int = 10000) -> None:
        self._raw: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=maxsize)
        self._loop: asyncio.AbstractEventLoop | None = None
        # ★ 每个 WS 连接一个队列，并记录它可见的车间（房间）
        #   workshops=None 表示「全部可见」（admin / 开发模式）
        self._subscribers: dict[asyncio.Queue, list[str] | None] = {}

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """绑定主事件循环。必须在 SDK 回调启动前调用。"""
        self._loop = loop

    # -------------------------------------------------- SDK 线程 → asyncio
    def emit_from_thread(self, event: dict[str, Any]) -> None:
        """★ 由 SDK 回调线程调用。绝不阻塞、绝不抛异常到 C 层。"""
        loop = self._loop
        if loop is None or loop.is_closed():
            logger.warning("事件总线未绑定事件循环，丢弃事件: %s", event.get("kind"))
            return
        try:
            loop.call_soon_threadsafe(self._put_raw_nowait, event)
        except RuntimeError:
            # 循环正在关闭
            pass

    def _put_raw_nowait(self, event: dict[str, Any]) -> None:
        try:
            self._raw.put_nowait(event)
        except asyncio.QueueFull:
            logger.error("原始事件队列已满，丢弃事件: %s", event.get("kind"))

    async def get_raw_event(self) -> dict[str, Any]:
        return await self._raw.get()

    # -------------------------------------------------- 告警推送（WS）
    async def publish_alarm(self, payload: dict[str, Any]) -> None:
        await self._fanout({"type": "alarm", "data": payload})

    async def publish(self, message: dict[str, Any]) -> None:
        """推送任意控制消息（如告警被删除、回放状态变化）。"""
        await self._fanout(message)

    async def _fanout(self, message: dict[str, Any]) -> None:
        """★ 按车间分房间投递（这是防「实时串数据」的关键）。

        消息里的 workshop 决定投给谁：
          · workshop = 'A'  → 投给「可见 A」的订阅者 + 「全部可见」的订阅者
          · workshop = None → **只**投给「全部可见」者（admin）
                              —— 不给普通车间账号，避免泄露无归属数据
        """
        ws = self._workshop_of(message)

        dead: list[asyncio.Queue] = []
        for q, visible in list(self._subscribers.items()):
            if not self._visible(ws, visible):
                continue
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._subscribers.pop(q, None)

    @staticmethod
    def _workshop_of(message: dict[str, Any]) -> str | None:
        data = message.get("data")
        if isinstance(data, dict):
            w = data.get("workshop")
            if w:
                return str(w)
        return None

    @staticmethod
    def _visible(ws: str | None, visible: list[str] | None) -> bool:
        """该订阅者能否收到这条消息。"""
        if visible is None:
            return True  # 订阅者可看全部
        if ws is None:
            return False  # 消息无归属 → 只给可看全部的人（默认拒绝）
        return ws in visible

    def subscribe(self, *, workshops: list[str] | None = None) -> asyncio.Queue[dict[str, Any]]:
        """订阅。workshops=None 表示可看全部（admin）。"""
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
        self._subscribers[q] = list(workshops) if workshops is not None else None
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.pop(q, None)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


# 全局单例，由 main.py 在启动时 bind_loop
bus = EventBus()
