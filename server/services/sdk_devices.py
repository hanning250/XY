# -*- coding: utf-8 -*-
"""★ SDK 在线设备表 —— 不依赖 IP 的在线判定权威来源。

## 为什么需要它

`device.ip` 可能为空（很多现场设备不填、或者从 NVR 转发时根本没有
独立 IP）。之前在线判定只能靠：
  · `device.online` 标记（SDK 回调维护，可能残留）
  · `last_seen` 兜底（窗口长，不敏感）

两者都可能错。而 SDK 内部有一份**实时维护的设备表**：

    glo.deviceUserMap = { device_id: lUserID }

这份表由 SDK 的注册/注销回调直接维护（见 src/Common/glo.py 的
`register_device` / `unregister_device`），是「设备此刻是否连着平台」
最准确的证据，而且**完全不需要 IP**。

## 本模块做什么

把这份表包装成进程内的稳定接口：
  · `online_device_ids()`  → 当前在线的 device_id 集合（快照，线程安全）
  · `is_device_online(dev)` → 单个判定
  · `online_snapshot()`     → {device_id: user_id}

## 线程安全

SDK 回调线程会改这个字典，直接遍历会抛
「dictionary changed size during iteration」。
所以统一用 `dict(...)` 做浅拷贝快照再遍历（glo.get_value 本身返回引用）。
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def online_snapshot() -> dict[str, int]:
    """当前在线的 {device_id: lUserID} 快照。

    ★ 拷贝一次再返回：SDK 回调线程随时可能增删，直接暴露引用会炸。
    """
    try:
        from src.Common import glo

        raw = glo.get_value("deviceUserMap", None)
        if not isinstance(raw, dict):
            return {}
        return dict(raw)
    except Exception:
        logger.debug("读取 SDK 在线设备表失败", exc_info=True)
        return {}


def online_device_ids() -> set[str]:
    """当前在线设备的 device_id 集合。"""
    return set(online_snapshot().keys())


def is_device_online(device_id: str) -> bool:
    """该 device_id 是否在 SDK 的在线表里。

    ★ 这是「设备真的连着平台」的最强证据：
      SDK 只在收到设备的 ISUP 注册时登记，设备断开（回调或超时）时注销。
    """
    if not device_id:
        return False
    return device_id in online_snapshot()


def sdk_available() -> bool:
    """SDK 是否可用（能用它的在线表）。

    如果服务是以「无 SDK 模式」启动的（sdk_available() 为 False），
    这份表永远是空的，此时调用方应该退回数据库标记。

    ★ 2026-10-26 修正：原来取的是 `isup_runtime`，但模块里导出的
      实例名是 `runtime`（见 isup_runtime.py:478），
      导致 getattr 永远拿不到 → 一直返回 False →
      实时设备接口显示「SDK 未启动」，明明 SDK 正常运行。
    """
    try:
        from server.adapters.isup_runtime import runtime

        return bool(getattr(runtime, "started", False))
    except Exception:
        logger.debug("判断 SDK 可用性失败", exc_info=True)
        return False
