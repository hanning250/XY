# -*- coding: utf-8 -*-
"""解析海康 HTTP / ISAPI 事件上报（multipart 或纯 XML/JSON）。"""
import re
from typing import List, Tuple


def _extract_xml_or_json(chunks: List[bytes]) -> bytes:
    for chunk in chunks:
        if not chunk:
            continue
        text = chunk.decode("utf-8", errors="ignore").strip()
        if text.startswith("<") or text.startswith("{") or text.startswith("["):
            return chunk
    if chunks:
        return chunks[0]
    return b""


def parse_http_event_body(body: bytes, content_type: str = "") -> Tuple[bytes, List[bytes]]:
    """返回 (事件文本, 图片二进制列表)。"""
    pictures: List[bytes] = []
    if not body:
        return b"", pictures

    content_type = (content_type or "").lower()
    if "multipart" not in content_type:
        if body[:3] == b"\xff\xd8\xff" or body[:8] == b"\x89PNG\r\n\x1a\n":
            return b"", [body]
        return body, pictures

    boundary = None
    match = re.search(r"boundary=([^;\s]+)", content_type, flags=re.IGNORECASE)
    if match:
        boundary = match.group(1).strip('"')

    if not boundary:
        return body, pictures

    delimiter = ("--" + boundary).encode("ascii")
    parts = body.split(delimiter)
    text_parts: List[bytes] = []

    for part in parts:
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

    return _extract_xml_or_json(text_parts), pictures
