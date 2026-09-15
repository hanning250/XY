# -*- coding: utf-8 -*-
import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from alarm_helpers import TEST_ALARM_JPEG, serialize_alarm, to_alarm_record
from alarm_ingest import persist_alarm
from isapi_receiver import parse_http_event_body
from labels_zh import (
    enrich_service_status,
    label_health_status,
    label_isup_enabled,
)
from notifier import AlarmNotifier
from schemas import (
    AlarmRecord,
    AlarmStatsResponse,
    HealthResponse,
    StatusResponse,
)


def create_app(storage, config, alarm_service=None, notifier=None):
    static_dir = os.path.join(os.path.dirname(__file__), "static")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if notifier is not None:
            notifier.set_loop(asyncio.get_running_loop())
        yield

    app = FastAPI(
        title="海康 ISUP 告警后端",
        description="通过 ISUP 协议接收多设备告警，提供查询与 SSE 实时推送",
        version="2.0.0",
        lifespan=lifespan,
    )

    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    def dashboard():
        index_path = os.path.join(static_dir, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        return {"message": "ISUP 告警后端运行中，访问 /docs 查看 API 文档"}

    @app.get("/health", response_model=HealthResponse)
    def health():
        status = "ok"
        return HealthResponse(
            status=status,
            status_label=label_health_status(status),
            time=datetime.now().isoformat(timespec="seconds"),
        )

    @app.get("/api/status", response_model=StatusResponse)
    def status():
        isup_cfg = config.get("isup", {})
        isup_enabled = isup_cfg.get("enabled", True)
        service_status = enrich_service_status(
            alarm_service.status if alarm_service is not None else {"state": "disabled"}
        )
        return StatusResponse(
            isup_enabled=isup_enabled,
            isup_enabled_label=label_isup_enabled(isup_enabled),
            platform_ip=isup_cfg.get("platform_ip"),
            cms_port=isup_cfg.get("cms", {}).get("port", 7660),
            ams_port=isup_cfg.get("ams", {}).get("port", 7200),
            api_port=config.get("api", {}).get("port", 8080),
            alarm_service=service_status,
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
        data = storage.count_alarms()
        total = data["total"]
        ppe_related = data["ppe_related"]
        return AlarmStatsResponse(
            total=total,
            ppe_related=ppe_related,
            total_label=f"共 {total} 条告警",
            ppe_related_label=f"防护服相关 {ppe_related} 条",
            summary=f"总计 {total} 条，其中防护服相关 {ppe_related} 条",
        )

    @app.get("/api/pictures/{filename}")
    def get_picture(filename: str):
        safe_name = os.path.basename(filename)
        full_path = os.path.join(storage.picture_dir, safe_name)
        if not os.path.isfile(full_path):
            raise HTTPException(status_code=404, detail="picture not found")
        return FileResponse(full_path)

    async def _handle_http_event(request: Request):
        """接收海康 HTTP 事件上报（NVR/摄像头联动上传中心）。"""
        client_ip = request.client.host if request.client else ""
        content_type = request.headers.get("content-type", "")
        body = await request.body()
        raw_bytes, pictures = parse_http_event_body(body, content_type)
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
            remote_urls=[],
        )
        return {"ok": True, "alarm_id": alarm_id}

    @app.post("/api/isapi/event")
    async def receive_isapi_event(request: Request):
        return await _handle_http_event(request)

    @app.post("/api/hikvision/event")
    async def receive_hikvision_event(request: Request):
        return await _handle_http_event(request)

    @app.post("/api/alarms/test")
    def inject_test_alarm():
        """注入测试告警并触发 SSE 推送。"""
        raw_payload = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<EventNotificationAlert>"
            "<eventType>AIOP_Polling_Snap</eventType>"
            "<channelID>1</channelID>"
            "<dateTime>2026-09-14T16:00:00+08:00</dateTime>"
            "<eventDescription>测试告警-未穿防护服</eventDescription>"
            "</EventNotificationAlert>"
        ).encode("utf-8")

        alarm_id, _, paths = persist_alarm(
            storage,
            notifier,
            config,
            raw_payload,
            command_label="TEST_INJECT",
            device_serial="GU0986479",
            device_ip="192.168.1.64",
            embedded_pictures=[TEST_ALARM_JPEG],
        )
        return {
            "ok": True,
            "alarm_id": alarm_id,
            "picture_urls": [f"/api/pictures/{os.path.basename(p)}" for p in paths],
        }

    return app
