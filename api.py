# -*- coding: utf-8 -*-
import asyncio
import json
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Tuple

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from alarm_ingest import persist_alarm, to_alarm_record
from schemas import AlarmRecord, AlarmStatsResponse, HealthResponse, StatusResponse


def _parse_http_event_body(body: bytes, content_type: str = "") -> Tuple[bytes, List[bytes]]:
    """解析海康 HTTP 事件（multipart 或纯 XML/JSON）。"""
    pictures: List[bytes] = []
    if not body:
        return b"", pictures

    content_type = (content_type or "").lower()
    if "multipart" not in content_type:
        if body[:3] == b"\xff\xd8\xff" or body[:8] == b"\x89PNG\r\n\x1a\n":
            return b"", [body]
        return body, pictures

    match = re.search(r"boundary=([^;\s]+)", content_type, flags=re.IGNORECASE)
    if not match:
        return body, pictures

    delimiter = ("--" + match.group(1).strip('"')).encode("ascii")
    text_parts: List[bytes] = []
    for part in body.split(delimiter):
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        header_end = part.find(b"\r\n\r\n")
        if header_end < 0:
            continue
        headers = part[:header_end].decode("utf-8", errors="ignore").lower()
        payload = part[header_end + 4 :]
        if payload.endswith(b"\r\n"):
            payload = payload[:-2]
        if "image/jpeg" in headers or "image/png" in headers or "application/octet-stream" in headers:
            if len(payload) > 128:
                pictures.append(payload)
        elif "xml" in headers or "json" in headers or "text/" in headers:
            text_parts.append(payload)

    for chunk in text_parts:
        if not chunk:
            continue
        text = chunk.decode("utf-8", errors="ignore").strip()
        if text.startswith("<") or text.startswith("{") or text.startswith("["):
            return chunk, pictures
    return (text_parts[0] if text_parts else b""), pictures


def create_app(storage, config, notifier=None):
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    http_cfg = config.get("http_notify", {})
    event_path = http_cfg.get("path", "/api/hikvision/event")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if notifier is not None:
            notifier.set_loop(asyncio.get_running_loop())
        yield

    app = FastAPI(
        title="海康 HTTP ISAPI 告警后端",
        description="通过 HTTP ISAPI 接收设备告警，提供查询与 SSE 实时推送",
        version="3.0.0",
        lifespan=lifespan,
    )

    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    def dashboard():
        index_path = os.path.join(static_dir, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        return {"message": "HTTP ISAPI 告警后端运行中，访问 /docs 查看 API 文档"}

    @app.get("/health", response_model=HealthResponse)
    def health():
        return HealthResponse(
            status="ok",
            time=datetime.now().isoformat(timespec="seconds"),
        )

    @app.get("/api/status", response_model=StatusResponse)
    def status():
        api_cfg = config.get("api", {})
        return StatusResponse(
            platform_ip=http_cfg.get("platform_ip"),
            api_port=int(api_cfg.get("port", 8080)),
            event_path=event_path,
        )

    @app.get("/api/alarms", response_model=list[AlarmRecord])
    def list_alarms(
        limit: int = Query(50, ge=1, le=500),
        ppe_only: bool = False,
    ):
        rows = storage.list_alarms(limit=limit, ppe_only=ppe_only)
        return [to_alarm_record(row) for row in rows]

    @app.get("/api/alarms/stream")
    async def alarm_stream(request: Request):
        if notifier is None:
            raise HTTPException(status_code=503, detail="SSE notifier not available")

        async def event_generator():
            queue = notifier.subscribe()
            try:
                yield ": connected\n\n"
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        message = await asyncio.wait_for(queue.get(), timeout=30.0)
                        yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
                    except asyncio.TimeoutError:
                        yield ": heartbeat\n\n"
            finally:
                notifier.unsubscribe(queue)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/api/alarms/{alarm_id}", response_model=AlarmRecord)
    def get_alarm(alarm_id: int):
        alarm = storage.get_alarm(alarm_id)
        if not alarm:
            raise HTTPException(status_code=404, detail="alarm not found")
        return to_alarm_record(alarm)

    @app.get("/api/stats", response_model=AlarmStatsResponse)
    def stats():
        return AlarmStatsResponse(**storage.count_alarms())

    @app.get("/api/pictures/{filename}")
    def get_picture(filename: str):
        safe_name = os.path.basename(filename)
        full_path = os.path.join(storage.picture_dir, safe_name)
        if not os.path.isfile(full_path):
            raise HTTPException(status_code=404, detail="picture not found")
        return FileResponse(full_path)

    @app.post(event_path)
    async def receive_hikvision_event(request: Request):
        """接收海康 HTTP 事件上报（NVR/摄像头联动上传中心）。"""
        client_ip = request.client.host if request.client else ""
        content_type = request.headers.get("content-type", "")
        body = await request.body()
        raw_bytes, pictures = _parse_http_event_body(body, content_type)
        if not raw_bytes and pictures:
            raw_bytes = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                "<EventNotificationAlert>"
                "<eventType>AIOP_Polling_Snap</eventType>"
                f"<channelID>1</channelID>"
                f"<eventDescription>HTTP抓拍 from {client_ip}</eventDescription>"
                "</EventNotificationAlert>"
            ).encode("utf-8")
        if not raw_bytes and not pictures:
            print(f"[http-event] 空请求 from {client_ip}")
            return {"ok": True, "ignored": True}

        print(
            f"[http-event] 收到事件 from {client_ip}, "
            f"body={len(body)}B, xml/json={len(raw_bytes)}B, pics={len(pictures)}"
        )
        alarm_id, _, _ = persist_alarm(
            storage,
            notifier,
            config,
            raw_bytes,
            command_label="HTTP_ISAPI",
            device_serial="",
            device_ip=client_ip,
            embedded_pictures=pictures,
        )
        return {"ok": True, "alarm_id": alarm_id}

    return app
