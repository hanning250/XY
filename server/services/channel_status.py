# -*- coding: utf-8 -*-
"""★ 摄像头（通道）真实状态采集 —— 不借用 NVR 状态。

## 之前的错误

通道在线状态直接抄父设备（NVR）：
    box001 在线 → 它下面 5 个通道**全部**显示在线

这导致运维看到「5 个摄像头都在线」，实际只有 1 个真的接了摄像头。
用户明确要求：**要能看到哪些摄像头设备在线**，才能据此做后续自定义。

## 正确的数据来源

海康 NVR 的 ISAPI 提供了每个通道的真实状态：

    GET /ISAPI/ContentMgmt/InputProxy/channels/<id>

返回示例（实测 box001）：

    <InputProxyChannel>
      <id>1</id>
      <name>测试</name>
      <online>true</online>                     ← ★ 这就是摄像头的真实在线状态
      <sourceInputPortDescriptor>
        <ipAddress>192.168.1.10</ipAddress>     ← 摄像头自己的 IP（不是 NVR 的）
        <model>DS-2CD7T4KY-LSW</model>          ← 摄像头型号
        <serialNumber>DS-2CD7T4KY-LSW2022...</serialNumber>
        <firmwareVersion>V5.8.0 build 220504</firmwareVersion>
      </sourceInputPortDescriptor>
    </InputProxyChannel>

实测结果（box001 5 个通道）：
    ch1: online=true   ip=192.168.1.10    model=DS-2CD7T4KY-LSW   ← 真的接了
    ch2: online=false  ip=192.168.1.101   model=(空)               ← 没接/掉线
    ch3~ch5: online=false                                          ← 空通道

## 本模块提供

    fetch_channel_states(nvr_ip, port, user, pwd, channels)
        → {channel_id: ChannelState}

    ChannelState 包含：online / ip / model / serial / firmware / name

## 缓存

NVR 状态变化不频繁，且每次要发 N 个 HTTP 请求（N=通道数）。
默认缓存 30 秒，避免每次刷页面都扫一遍。
"""
from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ChannelState:
    """一个通道（摄像头）的真实状态。"""

    channel_id: int
    online: bool
    name: str = ""
    ip: str = ""
    model: str = ""
    serial: str = ""
    firmware: str = ""
    error: str = ""
    """采集失败时的原因（此时 online 不可信，应回退到父设备状态）"""


# 缓存：key = (host, port, channel_id) → (时间戳, ChannelState)
_CACHE: dict[tuple[str, int, int], tuple[float, ChannelState]] = {}
_LOCK = threading.Lock()


def _cache_ttl() -> float:
    try:
        from server.config import get_settings

        return float(
            getattr(get_settings(), "channel_state_cache_seconds", 30.0)
        )
    except Exception:
        return 30.0


def _parse_channel_xml(channel_id: int, xml: str) -> ChannelState:
    """解析 InputProxyChannel XML。"""

    def grab(tag: str, default: str = "") -> str:
        m = re.search(rf"<{tag}>([^<]*)</{tag}>", xml)
        return m.group(1).strip() if m else default

    online_raw = grab("online", "").lower()
    # 只认明确的 true；空/解析失败都算无法判定（error 非空让调用方回退）
    if online_raw in ("true", "1"):
        online = True
    elif online_raw in ("false", "0"):
        online = False
    else:
        return ChannelState(
            channel_id=channel_id,
            online=False,
            error=f"响应里没有 online 字段（raw={online_raw!r}）",
        )

    return ChannelState(
        channel_id=channel_id,
        online=online,
        name=grab("name"),
        ip=grab("ipAddress"),
        model=grab("model"),
        serial=grab("serialNumber"),
        firmware=grab("firmwareVersion"),
    )


def fetch_channel_states(
    host: str,
    port: int,
    username: str,
    password: str,
    channels: list[int],
    *,
    timeout: float = 5.0,  # ★ 2026-11-09：60 → 5 秒。NVR 不通时 60 秒太长，甲方接口会超时
) -> dict[int, ChannelState]:
    """批量取通道真实状态（带缓存）。

    ★ 单个通道失败不影响其它通道：失败的那条 error 非空，
      调用方应回退到父设备状态，而不是直接判离线。
    """
    if not host or not channels:
        return {}

    ttl = _cache_ttl()
    now = time.time()
    out: dict[int, ChannelState] = {}
    todo: list[int] = []

    for ch in channels:
        key = (host, port, ch)
        with _LOCK:
            hit = _CACHE.get(key)
        if hit and now - hit[0] < ttl:
            out[ch] = hit[1]
        else:
            todo.append(ch)

    if not todo:
        return out

    from server.services.isapi_client import IsapiError, get_client

    client = get_client(host, port, username, password)

    # ★ 2026-11-09：串行改并发。
    #   原来每个通道串行等待，NVR 慢或不通时，
    #   5 个通道要累计 5×超时秒，甲方调用 /channels 会直接超时。
    #   改成并发后，总耗时 ≈ 单个通道超时，不再累积。
    def _fetch_one(ch: int) -> ChannelState:
        path = f"/ISAPI/ContentMgmt/InputProxy/channels/{ch}"
        try:
            status, _, body = client.request("GET", path, timeout=timeout)
            if status != 200:
                return ChannelState(channel_id=ch, online=False, error=f"HTTP {status}")
            return _parse_channel_xml(ch, body.decode("utf-8", "replace"))
        except IsapiError as exc:
            return ChannelState(channel_id=ch, online=False, error=str(exc))
        except Exception as exc:
            logger.debug("取通道 %s 状态失败", ch, exc_info=True)
            return ChannelState(
                channel_id=ch, online=False, error=f"{type(exc).__name__}: {exc}"
            )

    from concurrent.futures import ThreadPoolExecutor

    # 并发上限 8，不会把 NVR 打死
    with ThreadPoolExecutor(max_workers=min(8, len(todo))) as pool:
        futures = {pool.submit(_fetch_one, ch): ch for ch in todo}
        for fut in futures:
            ch = futures[fut]
            try:
                out[ch] = fut.result()
            except Exception as exc:
                out[ch] = ChannelState(
                    channel_id=ch, online=False, error=f"{type(exc).__name__}: {exc}"
                )
            with _LOCK:
                _CACHE[(host, port, ch)] = (now, out[ch])

    return out
