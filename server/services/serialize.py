# -*- coding: utf-8 -*-
"""ORM 对象 → API Schema 的转换。"""

from __future__ import annotations

import json

from server.models import Alarm, AlarmImage, VideoStatus
from server.schemas import AlarmBrief, AlarmOut, ImageOut, VideoOut
from server.services import media as media_svc


def image_out(img: AlarmImage) -> ImageOut:
    url, absolute, thumb = media_svc.image_urls(img.file_path)
    return ImageOut(
        id=img.id,
        file_hash=img.file_hash,
        seq=img.seq,
        width=img.width,
        height=img.height,
        file_size=img.file_size,
        linked_by=img.linked_by,
        url=url,
        absolute_url=absolute,
        thumbnail_url=thumb,
        created_at=img.created_at,
    )


def _relative_media_url(url: str | None) -> str | None:
    """把绝对媒体 URL 压成相对路径（内部前端专用）。

    ★★ 为什么必须这么做（2026-10 修复「视频播不了」）：
        video_url 在库里存的是**绝对地址**（public_base_url 拼的，
        如 http://192.168.1.118:8088/media/video/x.mp4）。内部前端
        页面跑在 Vite(5173)/静态托管源上，<video src> 用绝对地址会
        **跨源直连 8088** —— SameSite=Lax 的 isup_media_token Cookie
        不随跨源请求携带，服务端返回 401 {"detail":"未认证"}
        （22 字节 JSON），浏览器表现成
        「没有找到支持的视频格式和 MIME 类型」。

        图片本来就是相对路径（走 Vite /media 代理、同源带 Cookie），
        所以症状一直是「图片正常、视频 401」。
        甲方用的 /openapi/v1 在 open_api.py 里另拼绝对地址，不受影响。
    """
    if not url:
        return url
    for marker in ("/media/video/", "/media/"):
        idx = url.find(marker)
        if idx != -1:
            return url[idx:]
    return url


def video_out(alarm: Alarm) -> VideoOut:
    """★ 未点击时 status=not_requested, url=None —— 视频是挂起的。

    ★ 媒体已过期时，即使曾经生成过视频，也不再给出 url（文件已被删）。
    ★ 失败时带上 error 原因，前端据此给出可操作的提示（如"设备未在线，稍后重试"）。
    ★ url 统一给相对路径 —— 见 _relative_media_url 的跨源 Cookie 说明。
    """
    err = getattr(alarm, "video_error", None)
    if getattr(alarm, "media_expired", False):
        return VideoOut(
            status=VideoStatus.UNAVAILABLE.value,
            url=None,
            duration=alarm.video_duration,
            provider=alarm.video_provider,
            error=None,
        )
    return VideoOut(
        status=alarm.video_status or VideoStatus.NOT_REQUESTED.value,
        url=_relative_media_url(alarm.video_url),
        duration=alarm.video_duration,
        provider=alarm.video_provider,
        error=err,
    )


def _type_text_and_summary(alarm: Alarm) -> tuple[str, str, dict]:
    """从 content_json + 冗余列取业务类型文本、摘要与 AIOP 附加信息。"""
    c: dict = {}
    if alarm.content_json:
        try:
            c = json.loads(alarm.content_json) or {}
        except (ValueError, TypeError):
            c = {}

    # 冗余列优先（筛选/统计同源），没有再回退 JSON
    col_rule = (getattr(alarm, "rule_name", None) or "").strip()
    type_text = col_rule or str(c.get("typeText") or c.get("ruleName") or "")
    summary = str(c.get("summary") or "")
    repeat = int(c.get("repeatCount") or 1)
    person = int(getattr(alarm, "person_count", 0) or c.get("personCount") or 0)
    alarmed = int(getattr(alarm, "alarmed_count", 0) or c.get("alarmedCount") or 0)

    extra: dict = {"repeat_count": repeat}
    if c.get("isAiop") or col_rule or person or alarmed:
        extra.update(
            {
                "is_aiop": bool(c.get("isAiop") or col_rule),
                "rule_name": col_rule or str(c.get("ruleName") or ""),
                "mp_name": c.get("mpName") or "",
                "person_count": person,
                "alarmed_count": alarmed,
                # ★ 甲方口径：人次来自设备算法估算，非平台复核
                "person_count_source": "device_estimate",
            }
        )
    elif c.get("channelName"):
        extra["channel_name"] = c.get("channelName")
    return type_text, summary, extra


def alarm_brief(alarm: Alarm) -> AlarmBrief:
    images = sorted(alarm.images, key=lambda i: i.seq)
    thumb = media_svc.image_urls(images[0].file_path)[2] if images else None
    type_text, summary, extra = _type_text_and_summary(alarm)
    return AlarmBrief(
        id=alarm.id,
        device_id=alarm.device_id,
        channel=alarm.channel,
        alarm_type=alarm.alarm_type,
        alarm_time=alarm.alarm_time,
        status=alarm.status,
        # ★ 车间：列表要能一眼看出是哪条产线的报警（名字由调用方补全）
        workshop=getattr(alarm, "workshop", None),
        image_count=len(images),
        thumbnail_url=thumb,
        video=video_out(alarm),
        type_text=type_text,
        summary=summary,
        extra=extra,
        media_expired=bool(getattr(alarm, "media_expired", False)),
        media_expired_at=getattr(alarm, "media_expired_at", None),
        handled=bool(getattr(alarm, "handled", False)),
        handled_at=getattr(alarm, "handled_at", None),
    )


def alarm_out(alarm: Alarm) -> AlarmOut:
    content = None
    if alarm.content_json:
        try:
            content = json.loads(alarm.content_json)
        except (ValueError, TypeError):
            content = None
    type_text, summary, extra = _type_text_and_summary(alarm)
    return AlarmOut(
        id=alarm.id,
        device_id=alarm.device_id,
        channel=alarm.channel,
        alarm_type=alarm.alarm_type,
        alarm_time=alarm.alarm_time,
        status=alarm.status,
        content=content,
        images=[image_out(i) for i in sorted(alarm.images, key=lambda x: x.seq)],
        video=video_out(alarm),
        created_at=alarm.created_at,
        type_text=type_text,
        summary=summary,
        extra=extra,
        media_expired=bool(getattr(alarm, "media_expired", False)),
        media_expired_at=getattr(alarm, "media_expired_at", None),
        handled=bool(getattr(alarm, "handled", False)),
        handled_at=getattr(alarm, "handled_at", None),
    )
