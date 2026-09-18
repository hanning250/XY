# -*- coding: utf-8 -*-
"""WebSocket connection manager for real-time alarm broadcast."""
import asyncio
import json
from typing import Any

from fastapi import WebSocket


class AlarmWebSocketManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        message = json.dumps(payload, ensure_ascii=False)
        async with self._lock:
            dead: list[WebSocket] = []
            for websocket in self._connections:
                try:
                    await websocket.send_text(message)
                except Exception:
                    dead.append(websocket)
            for websocket in dead:
                self._connections.discard(websocket)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


ws_manager = AlarmWebSocketManager()
