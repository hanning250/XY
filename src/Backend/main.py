# -*- coding: utf-8 -*-
"""FastAPI backend: alarm persistence + WebSocket broadcast."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.Backend.alarm_bridge import get_alarm_queue
from src.Backend.alarm_mapper import to_client_view
from src.Backend.config import FRONTEND_DIR, HOST, PORT
from src.Backend.database import delete_alarm, get_alarm, get_stats, init_db, insert_alarm, list_alarms
from src.Backend.schemas import AlarmClientListResponse, AlarmStats

from src.Backend.websocket_manager import ws_manager

_consumer_task: Optional[asyncio.Task] = None


async def _consume_alarm_queue() -> None:
    loop = asyncio.get_running_loop()
    alarm_queue = get_alarm_queue()

    while True:
        event = await loop.run_in_executor(None, alarm_queue.get)
        try:
            saved = insert_alarm(event)
            client_payload = to_client_view(saved).model_dump(by_alias=True)
            await ws_manager.broadcast(client_payload)
        except Exception as exc:
            print(f"[告警平台] 入库或推送失败: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _consumer_task
    init_db()
    _consumer_task = asyncio.create_task(_consume_alarm_queue())
    yield
    if _consumer_task:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="XY Alarm Platform", lifespan=lifespan)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
async def index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Frontend not found. Place index.html in src/Frontend/"}


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "websocket_clients": ws_manager.connection_count,
    }


@app.get("/api/alarms", response_model=AlarmClientListResponse)
async def api_list_alarms(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    device_id: Optional[str] = None,
    event_type: Optional[str] = None,
    event_state: Optional[str] = None,
):
    items, total = list_alarms(
        limit=limit,
        offset=offset,
        device_id=device_id,
        event_type=event_type,
        event_state=event_state,
    )
    return AlarmClientListResponse(
        total=total,
        items=[to_client_view(item) for item in items],
    )


@app.get("/api/alarms/stats", response_model=AlarmStats)
async def api_alarm_stats():
    return get_stats()


@app.delete("/api/alarms/{alarm_id}")
async def api_delete_alarm(alarm_id: int):
    if not delete_alarm(alarm_id):
        raise HTTPException(status_code=404, detail="Alarm not found")
    await ws_manager.broadcast({"type": "deleted", "id": alarm_id})
    return {"ok": True, "id": alarm_id}


@app.get("/api/alarms/{alarm_id}/image")
async def api_get_alarm_image(alarm_id: int):
    alarm = get_alarm(alarm_id)
    if alarm is None:
        raise HTTPException(status_code=404, detail="Alarm not found")
    if not alarm.image_path:
        raise HTTPException(status_code=404, detail="Alarm image not found")

    image_path = Path(alarm.image_path)
    if not image_path.is_file():
        raise HTTPException(status_code=404, detail="Alarm image file missing")

    media_type = "image/jpeg"
    if image_path.suffix.lower() == ".png":
        media_type = "image/png"
    return FileResponse(image_path, media_type=media_type)


@app.websocket("/ws/alarms")
async def websocket_alarms(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)


def run_server(app_instance=None, host: str = HOST, port: int = PORT) -> None:
    target_app = app_instance or app
    uvicorn.run(
        target_app,
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    run_server()
