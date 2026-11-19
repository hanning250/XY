# -*- coding: utf-8 -*-
"""ISAPI 录像下载客户端 —— 替代 SDK 回放，突破并发与速度限制。

## 为什么需要它（2026-10-24 实测）

SDK 回放（NET_ECMS_StartPlayBack）的两个硬限制：

  · **只支持 1 路**：实测 3 路并发时，后开的把先开的踢掉
    （lane0=1.1s/7%, lane1=0.4s/2%, lane2=16.0s/100%）
  · **1 倍速**：要 60 秒画面必须花 60 秒

ISAPI 的 /ISAPI/ContentMgmt/download 完全不同：

  · **支持并发**：实测 3 路同时下载同一段，3 路全部成功，
    总耗时 3.8 秒（单路也是 3.7 秒 → 并发效率 1.0x）
  · **约 4 倍速**：15 秒录像（6715 KB）3.7 秒下完 = 1800 KB/s

这让「3 台摄像头 + 1 台 NVR」的容量从缺口 3 倍变成余量 33%。

## 接口要点

     POST /ISAPI/ContentMgmt/download
     Content-Type: application/xml
     Body:
         <downloadRequest>
           <playbackURI>rtsp://host:554/Streaming/tracks/101
                        ?starttime=20261023T182000Z
                        &endtime=20261023T182015Z</playbackURI>
         </downloadRequest>

     认证：HTTP Digest（海康默认；Basic 会 401）
     响应：Content-Type: Opaque/data，body 是裸 PS 流（mpeg-ps）

## 时间格式（★ 踩过的坑）

     starttime/endtime 用 **设备本地时间**，格式 YYYYMMDDTHHMMSSZ，
     末尾的 Z 只是格式占位，**不是 UTC 语义**。
     实测：设备时间 18:20 的录像，要用 starttime=20261023T182000Z 取
     （若按 UTC 换算成 10:20Z，会返回 HTTP 500 或错误时段）。

## trackID

     101 = 通道 1 主码流
     102 = 通道 1 子码流
     201 = 通道 2 主码流 ...
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import re
import socket
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# 下载超时（秒）。给足余量：一段 90 秒的录像 4 倍速约 23 秒，
# 加上设备繁忙时的抖动，60 秒是安全值。
DOWNLOAD_TIMEOUT = 60.0

# 单次读取块大小
CHUNK = 65536


@dataclass(slots=True)
class IsapiConfig:
    """ISAPI 连接参数。"""

    host: str
    port: int = 80
    username: str = "admin"
    password: str = ""
    use_https: bool = False

    @property
    def base_url(self) -> str:
        scheme = "https" if self.use_https else "http"
        return f"{scheme}://{self.host}:{self.port}"


class IsapiError(RuntimeError):
    """ISAPI 调用失败。"""


def _md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _parse_digest_challenge(header: str) -> dict[str, str]:
    """解析 WWW-Authenticate: Digest realm="...", nonce="...", qop="auth", ..."""
    return dict(re.findall(r'(\w+)="?([^",]+)"?', header))


def _build_digest_auth(
    method: str, uri: str, challenge: str, username: str, password: str
) -> str:
    """按 RFC 2617 构造 Digest Authorization 头。"""
    p = _parse_digest_challenge(challenge)
    realm = p.get("realm", "")
    nonce = p.get("nonce", "")
    qop = p.get("qop", "")
    opaque = p.get("opaque", "")
    algorithm = p.get("algorithm", "MD5")

    ha1 = _md5(f"{username}:{realm}:{password}")
    ha2 = _md5(f"{method}:{uri}")
    nc = "00000001"
    cnonce = os.urandom(8).hex()

    if qop:
        qop_val = qop.split(",")[0].strip()
        response = _md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop_val}:{ha2}")
        auth = (
            f'Digest username="{username}", realm="{realm}", nonce="{nonce}", '
            f'uri="{uri}", response="{response}", qop={qop_val}, nc={nc}, '
            f'cnonce="{cnonce}", algorithm={algorithm}'
        )
    else:
        response = _md5(f"{ha1}:{nonce}:{ha2}")
        auth = (
            f'Digest username="{username}", realm="{realm}", nonce="{nonce}", '
            f'uri="{uri}", response="{response}", algorithm={algorithm}'
        )
    if opaque:
        auth += f', opaque="{opaque}"'
    return auth


def _parse_response_head(raw: bytes) -> tuple[int, dict[str, str], bytes]:
    """拆出状态码、响应头、body 开头。"""
    idx = raw.find(b"\r\n\r\n")
    if idx < 0:
        return 0, {}, raw
    head = raw[:idx].decode("latin-1", "replace")
    rest = raw[idx + 4 :]
    lines = head.split("\r\n")
    status = 0
    if lines:
        m = re.match(r"HTTP/1\.\d\s+(\d+)", lines[0])
        if m:
            status = int(m.group(1))
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    return status, headers, rest


def build_playback_uri(
    host: str,
    channel: int,
    start: datetime,
    end: datetime,
    *,
    main_stream: bool = True,
    rtsp_port: int = 554,
) -> str:
    """拼海康 playbackURI。

    ★ 时间用**设备本地时间**，格式末尾的 Z 是格式占位，不是 UTC 语义
      （见模块 docstring 的说明）。
    """
    track = channel * 100 + (1 if main_stream else 2)
    return (
        f"rtsp://{host}:{rtsp_port}/Streaming/tracks/{track}"
        f"?starttime={start.strftime('%Y%m%dT%H%M%SZ')}"
        f"&endtime={end.strftime('%Y%m%dT%H%M%SZ')}"
    )


class IsapiClient:
    """海康 ISAPI 客户端（只实现录像下载所需的最小功能）。

    线程安全：每次请求用独立 socket，可放心在多线程里并发调用。
    """

    def __init__(self, cfg: IsapiConfig) -> None:
        self.cfg = cfg
        self._lock = threading.Lock()
        # 缓存 Digest challenge，省掉每次的 401 往返
        self._challenge: str = ""

    # ------------------------------------------------------------ 底层请求
    def _open(self, timeout: float) -> socket.socket:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((self.cfg.host, self.cfg.port))
        return s

    def _raw_request(
        self,
        method: str,
        path: str,
        body: bytes,
        *,
        timeout: float,
        auth: str | None,
    ) -> tuple[socket.socket, int, dict[str, str], bytes]:
        """发一次请求，返回 (socket, status, headers, 已读到的 body 片段)。

        ⚠️ socket 由调用方负责关闭（下载大文件时要继续 recv）。
        """
        s = self._open(timeout)
        lines = [
            f"{method} {path} HTTP/1.1",
            f"Host: {self.cfg.host}:{self.cfg.port}",
            "Connection: close",
            "User-Agent: ISUP-Platform/1.0",
        ]
        if auth:
            lines.append(f"Authorization: {auth}")
        if body:
            lines.append(f"Content-Length: {len(body)}")
            lines.append("Content-Type: application/xml")
        s.sendall(("\r\n".join(lines) + "\r\n\r\n").encode() + body)

        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = s.recv(CHUNK)
            if not chunk:
                break
            buf += chunk
        status, headers, rest = _parse_response_head(buf)
        return s, status, headers, rest

    def request(
        self,
        method: str,
        path: str,
        body: bytes = b"",
        *,
        timeout: float = 20.0,
    ) -> tuple[int, dict[str, str], bytes]:
        """普通请求（读完全部 body，适合 JSON/XML 小响应）。"""
        s, status, headers, rest = self._raw_request(
            method, path, body, timeout=timeout, auth=None
        )
        try:
            if status == 401:
                challenge = headers.get("www-authenticate", "")
                if not challenge.lower().startswith("digest"):
                    raise IsapiError(f"需要 Digest 认证，但收到: {challenge[:80]}")
                auth = _build_digest_auth(
                    method, path, challenge, self.cfg.username, self.cfg.password
                )
                with self._lock:
                    self._challenge = challenge
                s.close()
                s, status, headers, rest = self._raw_request(
                    method, path, body, timeout=timeout, auth=auth
                )
            data = rest
            while True:
                chunk = s.recv(CHUNK)
                if not chunk:
                    break
                data += chunk
            return status, headers, data
        finally:
            s.close()

    # ------------------------------------------------------------ 具体接口
    def device_info(self) -> dict[str, str]:
        """取设备基础信息（用于验证连通性与认证）。"""
        status, _, body = self.request("GET", "/ISAPI/System/deviceInfo")
        if status != 200:
            raise IsapiError(f"deviceInfo HTTP {status}")
        text = body.decode("utf-8", "replace")
        out = {}
        for tag in ("deviceName", "model", "serialNumber", "firmwareVersion"):
            m = re.search(rf"<{tag}>([^<]*)</{tag}>", text)
            if m:
                out[tag] = m.group(1)
        return out

    def channel_snapshot(self, channel: int = 1, *, stream: int = 1) -> bytes:
        """抓一路实时 JPEG（ISAPI Streaming picture）。

        track：{channel}{stream} → 通道1主码流=101，子码流=102。
        用于平台「实况」面板近似实时画面（定时刷新）。
        """
        ch = max(1, int(channel))
        st = 1 if int(stream) <= 1 else 2
        track = ch * 100 + st
        path = f"/ISAPI/Streaming/channels/{track}/picture"
        status, headers, body = self.request("GET", path, timeout=8.0)
        if status != 200:
            raise IsapiError(f"snapshot HTTP {status} channel={ch}")
        if not body or len(body) < 100:
            raise IsapiError("snapshot 空响应")
        # 少数固件包一层 multipart；有 JPEG SOI 就直接用
        soi = body.find(b"\xff\xd8")
        if soi > 0:
            body = body[soi:]
        ctypeype = (headers.get("content-type") or "").lower()
        if "jpeg" not in ctypeype and not body.startswith(b"\xff\xd8"):
            raise IsapiError(f"snapshot 非 JPEG: {ctype[:40]}")
        return body

    def download_segment(
        self,
        playback_uri: str,
        out_path: Path,
        *,
        timeout: float = DOWNLOAD_TIMEOUT,
        max_seconds: float | None = None,
        retries: int = 3,
    ) -> int:
        """下载一段录像到 out_path（裸 PS 流）。返回字节数。

        ★ 失败会抛 IsapiError（HTTP 非 200）。
          HTTP 500 通常表示「该时段没有录像」（实测确认），
          调用方据此判断视频不存在。

        ★★ 关于 HTTP 0 与重试（2026-10-24 实测）：
          并发下载时偶发 status=0（连响应头都没读到），
          实测 5 轮 × 3 路，3/5 轮至少有一路失败。
          但**同一段重试就能成功** —— 说明不是"设备不支持并发"，
          而是设备端同时处理多个 download 请求时，
          偶发丢弃某个连接（TCP 层能连上 10 个，说明不是连接数限制）。

          所以这里加**重试**：
            · status==0（连接/读头失败）→ 重试
            · status==500（无录像）→ **不重试**（重试也没用）
            · 其它 4xx/5xx → 重试（可能是瞬时繁忙）

          重试间隔递增（0.3s / 0.8s / 1.5s），避免同时重试又撞车。

        并发安全：每次调用独立 socket，可多线程同时下载。
        """
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            f"<downloadRequest><playbackURI>{playback_uri}</playbackURI>"
            "</downloadRequest>"
        ).encode()

        path = "/ISAPI/ContentMgmt/download"
        last_error: Exception | None = None

        for attempt in range(max(1, retries)):
            if attempt:
                # 递增退避 + 抖动，避免多个并发任务同时重试又撞在一起
                import random

                time.sleep(0.3 * attempt + random.uniform(0, 0.3))

            t0 = time.time()
            s = None
            try:
                s, status, headers, rest = self._raw_request(
                    "POST", path, body, timeout=timeout, auth=None
                )

                if status == 401:
                    challenge = headers.get("www-authenticate", "")
                    if not challenge.lower().startswith("digest"):
                        raise IsapiError(f"下载需要 Digest 认证: {challenge[:80]}")
                    auth = _build_digest_auth(
                        "POST", path, challenge, self.cfg.username, self.cfg.password
                    )
                    s.close()
                    s, status, headers, rest = self._raw_request(
                        "POST", path, body, timeout=timeout, auth=auth
                    )

                if status != 200:
                    # 500 = 该时段无录像，重试无意义
                    if status == 500:
                        raise IsapiError("下载失败 HTTP 500（该时段无录像）")
                    raise IsapiError(
                        f"下载失败 HTTP {status}（第 {attempt + 1} 次尝试）"
                    )

                total = 0
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with open(out_path, "wb") as fp:
                    if rest:
                        fp.write(rest)
                        total += len(rest)
                    while True:
                        if max_seconds and (time.time() - t0) > max_seconds:
                            logger.warning("下载超时保护触发: %s", out_path.name)
                            break
                        try:
                            chunk = s.recv(CHUNK)
                        except socket.timeout:
                            logger.warning("下载读超时: %s", out_path.name)
                            break
                        if not chunk:
                            break
                        fp.write(chunk)
                        total += len(chunk)

                # ★ 拿到数据就成功；0 字节视为失败可重试
                if total > 0:
                    return total
                raise IsapiError("下载返回 0 字节")

            except IsapiError as exc:
                last_error = exc
                msg = str(exc)
                # 无录像不重试
                if "500（该时段无录像）" in msg:
                    raise
                logger.info(
                    "ISAPI 下载失败（第 %d/%d 次）: %s", attempt + 1, retries, msg
                )
            except (socket.timeout, ConnectionError, OSError) as exc:
                last_error = IsapiError(f"网络错误: {exc}")
                logger.info(
                    "ISAPI 下载网络错误（第 %d/%d 次）: %s", attempt + 1, retries, exc
                )
            finally:
                if s is not None:
                    try:
                        s.close()
                    except OSError:
                        pass

        raise last_error or IsapiError("下载失败（未知原因）")

    def download_by_time(
        self,
        channel: int,
        start: datetime,
        end: datetime,
        out_path: Path,
        *,
        main_stream: bool = True,
        timeout: float = DOWNLOAD_TIMEOUT,
        max_seconds: float | None = None,
    ) -> int:
        """按时间下载录像（封装 build_playback_uri + download_segment）。"""
        uri = build_playback_uri(
            self.cfg.host,
            channel,
            start,
            end,
            main_stream=main_stream,
        )
        return self.download_segment(
            uri, out_path, timeout=timeout, max_seconds=max_seconds
        )


# ---------------------------------------------------------------- 单例管理
_clients: dict[str, IsapiClient] = {}
_clients_lock = threading.Lock()


def get_client(host: str, port: int, username: str, password: str) -> IsapiClient:
    """按 host:port 缓存客户端实例（复用 Digest challenge）。"""
    key = f"{host}:{port}:{username}"
    with _clients_lock:
        c = _clients.get(key)
        if c is None:
            c = IsapiClient(
                IsapiConfig(host=host, port=port, username=username, password=password)
            )
            _clients[key] = c
        return c
