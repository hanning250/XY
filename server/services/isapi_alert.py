# -*- coding: utf-8 -*-
"""ISAPI 报警长连接 —— 不走 ISUP AMS，直接从 NVR 收事件。

    GET /ISAPI/Event/notification/alertStream
    Digest 认证，multipart XML 持续推送。

默认关：告警走 HCNetSDK 布防。本模块仅作 HTTP 长连接兜底。
"""

from __future__ import annotations

import logging
import re
import threading
import time

from server.services.bus import bus
from server.services.isapi_client import IsapiError, get_client
from server.services.timeutil import now_local, parse_any

logger = logging.getLogger(__name__)

class IsapiAlertListener:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._th: threading.Thread | None = None
        self._online_emitted = False

    def start(self) -> None:
        if self._th and self._th.is_alive():
            return
        self._stop.clear()
        self._th = threading.Thread(target=self._run, name="isapi-alert", daemon=True)
        self._th.start()
        logger.info("ISAPI 报警监听已启动")

    def stop(self) -> None:
        self._stop.set()
        if self._th and self._th.is_alive():
            self._th.join(timeout=3)
        logger.info("ISAPI 报警监听已停止")

    def _run(self) -> None:
        from server.config import get_settings

        while not self._stop.is_set():
            settings = get_settings()
            host = (getattr(settings, "isapi_host", "") or "").strip()
            password = getattr(settings, "isapi_password", "") or ""
            if not host or not password:
                logger.warning("ISAPI 未配置 host/password，报警监听空转")
                self._stop.wait(10)
                continue
            try:
                self._session(settings)
            except (IsapiError, OSError) as exc:
                logger.warning("ISAPI alertStream 断开: %s", exc)
                self._emit_device(settings, False)
                self._online_emitted = False
            except Exception:
                logger.exception("ISAPI 报警监听异常")
            if not self._stop.is_set():
                self._stop.wait(3)

    def _session(self, settings) -> None:
        client = get_client(
            settings.isapi_host,
            int(settings.isapi_port or 80),
            settings.isapi_username or "admin",
            settings.isapi_password,
        )
        path = "/ISAPI/Event/notification/alertStream"
        sock, headers, rest = client.open_get_stream(
            path,
            extra_headers=[
                "Accept: multipart/mixed, multipart/x-mixed-replace, application/xml, */*"
            ],
            timeout=15.0,
        )
        ctype = (headers.get("content-type") or "").lower()
        boundary = _boundary_of(ctype)
        logger.info("ISAPI alertStream 已连接 %s (%s)", settings.isapi_host, ctype)
        self._emit_device(settings, True)
        self._online_emitted = True
        buf = rest
        try:
            sock.settimeout(90.0)
            while not self._stop.is_set():
                try:
                    chunk = sock.recv(65536)
                except TimeoutError:
                    continue
                if not chunk:
                    raise IsapiError("alertStream 对端关闭")
                buf += chunk
                buf = self._drain(buf, boundary, client, settings)
        finally:
            try:
                sock.close()
            except OSError:
                pass

    def _drain(self, buf: bytes, boundary: str | None, client, settings) -> bytes:
        if boundary:
            token = b"--" + boundary.encode("ascii", "ignore")
            while True:
                i = buf.find(token)
                if i < 0:
                    return buf[-8192:] if len(buf) > 1_000_000 else buf
                j = buf.find(token, i + len(token))
                if j < 0:
                    return buf[i:]
                part = buf[i + len(token) : j]
                buf = buf[j:]
                body = _part_body(part)
                if body:
                    self._on_payload(body, client, settings)
            return buf
        # 非 multipart：按完整 XML 文档切
        while True:
            start = buf.find(b"<EventNotificationAlert")
            if start < 0:
                start = buf.find(b"{")
                if start < 0:
                    return b""
            end = buf.find(b"</EventNotificationAlert>", start)
            if end >= 0:
                xml = buf[start : end + len(b"</EventNotificationAlert>")]
                buf = buf[end + len(b"</EventNotificationAlert>") :]
                self._on_payload(xml, client, settings)
                continue
            if buf.strip().startswith(b"{"):
                # 简单 JSON：收到换行即一条
                nl = buf.find(b"\n")
                if nl < 0:
                    return buf
                self._on_payload(buf[:nl], client, settings)
                buf = buf[nl + 1 :]
                continue
            return buf[start:] if start >= 0 else buf

    def _on_payload(self, raw: bytes, client, settings) -> None:
        text = raw.decode("utf-8", "replace").strip()
        if not text or len(text) < 20:
            return
        if "<heartbeat" in text.lower() or "heartbeat" == _xml_tag(text, "eventType").lower():
            return
        event_type = (_xml_tag(text, "eventType") or _json_field(text, "eventType")).lower()
        if event_type in ("videoloss", "heartbeat", "upload"):
            return
        event_state = (_xml_tag(text, "eventState") or _json_field(text, "eventState")).lower()
        if event_state in ("inactive", "end"):
            return
        channel = _int_field(text, ("channelID", "dynChannelID", "channelNo", "channel")) or 1
        device_id = (
            _xml_tag(text, "deviceID")
            or _json_field(text, "deviceID")
            or (getattr(settings, "isapi_device_id", "") or "box001")
        )
        dt_raw = _xml_tag(text, "dateTime") or _json_field(text, "dateTime")
        alarm_time = parse_any(dt_raw) or now_local()
        pics = []
        try:
            jpeg = client.channel_snapshot(channel, stream=1)
            if jpeg:
                pics.append({"name": f"isapi_{channel}.jpg", "data": jpeg})
        except Exception:
            logger.debug("ISAPI 报警抓拍失败 ch=%s", channel, exc_info=True)
        bus.emit_from_thread(
            {
                "kind": "alarm",
                "alarm_type": 13,
                "device_id": device_id,
                "channel": channel,
                "alarm_time": alarm_time,
                "alarm_time_explicit": True,
                "content_raw": text,
                "content_json": None,
                "inline_pictures": pics,
            }
        )
        logger.info(
            "ISAPI 报警 %s ch=%s type=%s time=%s",
            device_id,
            channel,
            event_type,
            alarm_time,
        )

    def _emit_device(self, settings, online: bool) -> None:
        device_id = getattr(settings, "isapi_device_id", "") or "box001"
        bus.emit_from_thread(
            {
                "kind": "device",
                "device_id": device_id,
                "online": online,
            }
        )


def _boundary_of(ctype: str) -> str | None:
    m = re.search(r'boundary="?([^";\s]+)"?', ctype, re.I)
    return m.group(1) if m else None


def _part_body(part: bytes) -> bytes:
    idx = part.find(b"\r\n\r\n")
    if idx < 0:
        idx = part.find(b"\n\n")
        if idx < 0:
            return part.strip(b"-\r\n")
        return part[idx + 2 :].strip()
    return part[idx + 4 :].strip()


def _xml_tag(text: str, tag: str) -> str:
    m = re.search(rf"<{tag}>([^<]*)</{tag}>", text, re.I)
    return (m.group(1) if m else "").strip()


def _json_field(text: str, key: str) -> str:
    if not text.lstrip().startswith("{"):
        return ""
    m = re.search(rf'"{key}"\s*:\s*"([^"]*)"', text)
    return (m.group(1) if m else "").strip()


def _int_field(text: str, keys: tuple[str, ...]) -> int:
    for k in keys:
        v = _xml_tag(text, k) or _json_field(text, k)
        if v.isdigit():
            return int(v)
    return 0


isapi_alert_listener = IsapiAlertListener()
