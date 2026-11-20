# -*- coding: utf-8 -*-
"""★ 主动探测设备在线：不依赖 SDK 标记，直接问设备。

## 现有逻辑的问题（实测）

`device.online` 完全依赖 SDK 回调：
  · 注册回调 → True
  · 离线回调 → False

但 ISUP 的离线事件是「尽力而为」——实测踩过的坑：
  · 设备拔电、SDK 未必回调（尤其网络闪断）
  · 进程被强杀 → 上次的 True 残留
  · 设备静默断开（不发离线包）
后果：界面上的「在线」可能长时间是错的。

现有兜底只有 `last_seen` 超 3 天（`device_offline_after_minutes=4320`），
意味着设备真断电了，**3 天内都显示在线**。

## 解法：主动探测

对每台设备做一次「真的还活着吗」的检查，按可靠性排序：

  ① 端口层：平台与设备之间是否还有 ESTABLISHED 连接
     （ISUP 设备连 7661 注册、7663 报警，任何一条还在就说明在线）

  ② ISAPI HTTP 探测（如果设备支持）
     GET http://<ip>/ISAPI/System/deviceInfo
     有响应 = 在线；超时/拒绝 = 离线
     ★ 这需要知道设备 IP，且设备开了 ISAPI

  ③ 兜底：last_seen 在 N 分钟内

## 用法

    await probe_online(device)  # 返回 True/False/None

    None = 无法判定（既没端口证据也没 IP），此时退回 SDK 标记
"""
from __future__ import annotations

import logging
import socket
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def _cfg_float(name: str, default: float) -> float:
    try:
        from server.config import get_settings

        return float(getattr(get_settings(), name, default))
    except Exception:
        return default


def _cfg_int(name: str, default: int) -> int:
    try:
        from server.config import get_settings

        return int(getattr(get_settings(), name, default))
    except Exception:
        return default


def _timeout() -> float:
    return _cfg_float("device_online_probe_timeout", 1.5)


def _probe_port() -> int:
    return _cfg_int("device_online_probe_port", 80)


# 平台对外服务的本机端口（用于判断"谁连着平台"）
_LISTEN_PORTS = (7661, 7663, 6011)


def _established_peers() -> dict[str, int]:
    """返回 {对端IP: 连接数}，只统计与本平台 ISUP 端口建立的连接。

    用 netstat 而不是 psutil，是因为 netstat 在所有 Windows 上都可用，
    且不需要额外依赖。
    """
    out: dict[str, int] = {}
    try:
        r = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (subprocess.SubprocessError, OSError):
        return out

    for line in (r.stdout or "").splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        if "ESTABLISHED" not in line:
            continue
        local, remote = parts[1], parts[2]
        # 只看本地端口是本平台 ISUP 端口的连接
        try:
            local_port = int(local.rsplit(":", 1)[1])
        except (IndexError, ValueError):
            continue
        if local_port not in _LISTEN_PORTS:
            continue
        remote_ip = remote.rsplit(":", 1)[0]
        out[remote_ip] = out.get(remote_ip, 0) + 1
    return out


def _tcp_alive(ip: str, port: int, timeout: float | None = None) -> bool:
    """TCP 端口能否连通（ISAPI 80 端口探测）。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout if timeout is not None else _timeout())
    try:
        s.connect((ip, port))
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False
    finally:
        s.close()


@dataclass(slots=True)
class ProbeResult:
    online: bool | None
    """True/False = 有明确证据；None = 无法判定（退回 SDK 标记）"""

    reason: str
    """给人看的判定依据"""


def probe_device(
    device_id: str, ip: str | None, isapi_port: int | None = None
) -> ProbeResult:
    """同步探测一台设备是否在线。

    ★ 走「证据优先」策略：
      1. 端口层有 ESTABLISHED → 在线（最可信，ISUP 长连接还在）
      2. 有 IP 且 ISAPI 端口能连 → 在线（HTTP 服务活着）
      3. 有 IP 但连不上 → 离线（明确证据）
      4. 既无端口证据也无 IP → None（无法判定）
    """
    port = isapi_port if isapi_port is not None else _probe_port()

    # ① 端口层：ISUP 长连接还在吗
    peers = _established_peers()
    if ip and ip in peers:
        return ProbeResult(True, f"ISUP 连接活跃（{ip}，{peers[ip]} 条）")

    # 设备没登记 IP 时，按 device_id 无法反查 —— 只能看有没有任何连接
    # （多条设备共用一个 NAT 出口时无法区分，这种情况返回 None 更诚实）
    if not ip:
        if peers:
            return ProbeResult(
                None,
                f"设备未登记 IP，平台侧有 {len(peers)} 个活跃连接但无法对应到本设备",
            )
        return ProbeResult(None, "设备未登记 IP，且平台侧无活跃连接")

    # ② ISAPI 探测
    if _tcp_alive(ip, port):
        return ProbeResult(True, f"ISAPI 可达（{ip}:{port}）")

    # ③ ISAPI 不通：再确认一次端口层（可能是别的端口）
    if ip in _established_peers():
        return ProbeResult(True, f"ISUP 连接活跃（{ip}）")

    return ProbeResult(False, f"ISAPI {port} 不可达且无 ISUP 连接（{ip}）")
