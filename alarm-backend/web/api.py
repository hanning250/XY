# -*- coding: utf-8 -*-
import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from common.alarm_view import notify_alarm, serialize_alarm
from common.event_parser import is_ppe_related, make_picture_name, parse_isapi_payload
from web.notifier import AlarmNotifier
from web.schemas import (
    AlarmRecord,
    AlarmStatsResponse,
    EventPushResponse,
    HealthResponse,
    StatusResponse,
    to_alarm_record,
)


def create_app(storage, config, alarm_service=None, notifier=None):
    static_dir = os.path.join(os.path.dirname(__file__), "static")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if notifier is not None:
            notifier.set_loop(asyncio.get_running_loop())
        yield

    app = FastAPI(
        title="海康 ISUP 防护服告警后端",
        description=(
            "通过 ISUP（EHome）协议接收设备主动上报的告警与图片，"
            "提供查询、WebSocket 推送与 ISAPI HTTP 备用入口"
        ),
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
        return {"message": "告警后端运行中，访问 /docs 查看 API 文档"}

    @app.get("/health", response_model=HealthResponse)
    def health():
        return HealthResponse(
            status="ok",
            time=datetime.now().isoformat(timespec="seconds"),
        )

    @app.get("/api/status", response_model=StatusResponse)
    def status():
        service_status = (
            alarm_service.status
            if alarm_service is not None
            else {"state": "disabled", "devices": []}
        )
        return StatusResponse(
            sdk_enabled=alarm_service is not None,
            alarm_mode="isup",
            api_port=config.get("api", {}).get("port", 8080),
            alarm_service=service_status,
        )

    @app.get("/api/devices")
    def list_devices():
        """当前通过 ISUP 注册上来的设备。"""
        if alarm_service is None:
            return {"devices": [], "online": 0, "message": "ISUP 监听未启用"}
        status_data = alarm_service.status
        devices = status_data.get("devices", [])
        return {
            "devices": devices,
            "online": sum(1 for d in devices if d.get("state") == "online"),
            "total": len(devices),
            "register_port": status_data.get("register_port"),
            "alarm_port": status_data.get("alarm_port"),
            "protocol": status_data.get("protocol"),
        }

    @app.get("/api/alarms", response_model=list[AlarmRecord])
    def list_alarms(
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
        ppe_only: bool = False,
        start_time: str | None = Query(None, description="起始时间，ISO 格式，如 2026-09-11T00:00:00"),
        end_time: str | None = Query(None, description="结束时间，ISO 格式"),
        channel_no: int | None = Query(None, description="按通道号过滤"),
    ):
        rows = storage.list_alarms(
            limit=limit,
            offset=offset,
            ppe_only=ppe_only,
            start_time=start_time,
            end_time=end_time,
            channel_no=channel_no,
        )
        return [to_alarm_record(row) for row in rows]

    @app.get("/api/alarms/{alarm_id}", response_model=AlarmRecord)
    def get_alarm(alarm_id: int):
        alarm = storage.get_alarm(alarm_id)
        if not alarm:
            raise HTTPException(status_code=404, detail="alarm not found")
        return to_alarm_record(alarm)

    @app.get("/api/stats", response_model=AlarmStatsResponse)
    def stats():
        data = storage.count_alarms()
        return AlarmStatsResponse(**data)

    @app.get("/api/pictures/{filename}")
    def get_picture(filename: str):
        safe_name = os.path.basename(filename)
        full_path = os.path.join(storage.picture_dir, safe_name)
        if not os.path.isfile(full_path):
            raise HTTPException(status_code=404, detail="picture not found")
        return FileResponse(full_path, media_type="image/jpeg")

    @app.get("/api/aiop-json/{filename}")
    def get_aiop_json(filename: str):
        """原始 AIOP JSON（算法透传结果），便于甲方 IT 自行解析。"""
        safe_name = os.path.basename(filename)
        full_path = os.path.join(storage.picture_dir, safe_name)
        if not os.path.isfile(full_path):
            raise HTTPException(status_code=404, detail="aiop json not found")
        return FileResponse(full_path, media_type="application/json")

    @app.websocket("/ws/alarms")
    async def alarms_websocket(websocket: WebSocket):
        if notifier is None:
            await websocket.close(code=1011)
            return
        await notifier.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            notifier.disconnect(websocket)

    @app.post("/api/hikvision/event", response_model=EventPushResponse)
    async def receive_isapi_push(request: Request):
        content_type = request.headers.get("Content-Type", "")
        picture_paths = []
        raw_body = b""

        if "multipart/form-data" in content_type:
            form = await request.form()
            text_parts = []
            for index, (_, value) in enumerate(form.items()):
                if hasattr(value, "filename") and value.filename:
                    pic_name = make_picture_name("http_push", index)
                    pic_path = os.path.join(storage.picture_dir, pic_name)
                    content = await value.read()
                    with open(pic_path, "wb") as fp:
                        fp.write(content)
                    picture_paths.append(pic_path)
                elif hasattr(value, "read"):
                    text_parts.append((await value.read()).decode("utf-8", errors="ignore"))
                else:
                    text_parts.append(str(value))
            raw_body = "\n".join(text_parts).encode("utf-8")
        else:
            raw_body = await request.body()

        parsed = parse_isapi_payload(raw_body)
        keywords = config.get("event_filter_keywords", [])
        ppe_flag = is_ppe_related(
            parsed["event_type"],
            parsed["raw_text"] or raw_body.decode("utf-8", errors="ignore"),
            keywords,
            parsed=parsed,
        )

        client_host = request.client.host if request.client else "unknown"
        alarm_id = storage.save_alarm(
            device_ip=client_host,
            device_serial="http_push",
            command_type="HTTP_ISAPI_PUSH",
            event_type=parsed["event_type"],
            channel_no=parsed["channel_no"],
            event_time=parsed["event_time"],
            raw_payload=parsed["raw_text"] or raw_body.decode("utf-8", errors="ignore"),
            picture_paths=picture_paths,
            is_ppe_related=ppe_flag,
        )
        notify_alarm(notifier, storage, alarm_id)
        return EventPushResponse(
            accepted=True,
            alarm_id=alarm_id,
            content_type=content_type,
            event_type=parsed["event_type"],
            is_ppe_related=ppe_flag,
        )

    return app
