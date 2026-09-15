# -*- coding: utf-8 -*-
import asyncio
from typing import Set


class AlarmNotifier:
    """线程安全的告警广播器，供 ISUP 回调线程推送 SSE 事件。"""

    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
        self._loop = None

    def set_loop(self, loop):
        self._loop = loop

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        self._subscribers.discard(queue)

    def publish_sync(self, payload: dict):
        if self._loop is None:
            print("[notifier] SSE 未就绪（事件循环未绑定），告警仅入库")
            return
        if not self._subscribers:
            print(f"[notifier] 无 SSE 客户端连接，告警 id={payload.get('id')} 已入库，等待页面刷新")
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(payload), self._loop)
        print(f"[notifier] SSE 推送告警 id={payload.get('id')} -> {len(self._subscribers)} 个客户端")

    async def _broadcast(self, payload: dict):
        message = {"type": "alarm", "data": payload}
        dead = []
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(message)
            except Exception:
                dead.append(queue)
        for queue in dead:
            self._subscribers.discard(queue)
