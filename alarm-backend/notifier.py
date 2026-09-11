# -*- coding: utf-8 -*-
import asyncio
from typing import Set

from fastapi import WebSocket


class AlarmNotifier:
    """线程安全的告警广播器，供 SDK 回调线程推送 WebSocket 消息。"""

    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._loop = None

    def set_loop(self, loop):
        self._loop = loop

    @property
    def client_count(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self._connections.discard(websocket)

    def publish_sync(self, payload: dict):
        if self._loop is None or not self._connections:
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(payload), self._loop)

    async def _broadcast(self, payload: dict):
        message = {"type": "alarm", "data": payload}
        dead = []
        for websocket in list(self._connections):
            try:
                await websocket.send_json(message)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self._connections.discard(websocket)
