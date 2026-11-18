# -*- coding: utf-8 -*-
"""★ 视频来源抽象层（docs §6）。

因为同事的解码服务形态还没定，所以**不能把调用方式写死**在业务代码里。
业务代码只依赖 VideoProvider 协议，将来换实现类即可。

已内置实现：
  · MockProvider  —— 返回内置样例视频，让前端在同事服务未就绪时也能跑通
  · FileProvider  —— 同事产出 MP4 文件，我方只托管 URL（★最理想）
  · HttpProvider  —— 同事提供 HTTP 接口，我方代理/透传
"""

from __future__ import annotations

import abc
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from server.config import MEDIA_VIDEO_DIR, PROJECT_ROOT, get_settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class VideoRequest:
    alarm_id: str
    device_id: str
    channel: int
    # 期望的视频时间段
    start_time: datetime
    end_time: datetime


@dataclass(slots=True)
class VideoHandle:
    """Provider 返回的句柄。"""

    ready: bool
    url: str | None = None
    handle: str | None = None
    duration: int | None = None
    status: str = "starting"
    error: str | None = None


class VideoProvider(abc.ABC):
    """视频来源抽象。三种形态都只实现这个接口，业务代码不变。"""

    name: str = "base"

    @abc.abstractmethod
    async def request(self, req: VideoRequest) -> VideoHandle:
        """为一条告警申请视频。**必须快速返回**，不能阻塞等出流。"""

    async def poll(self, handle: VideoHandle) -> VideoHandle:
        """查询进度。默认实现：request 时已就绪则直接返回。"""
        return handle

    async def release(self, handle: VideoHandle) -> None:
        """释放资源（停流、删临时文件）。默认无操作。"""
        return None


class MockProvider(VideoProvider):
    """★ 让前端不被同事阻塞的关键。

    返回项目里已有的样例视频（outputFiles/*.mp4），
    前端可以完整跑通「点击 → loading → 播放 → 关闭」全流程。
    等同事的服务好了，把 ISUP_VIDEO_PROVIDER 改成 file/http 即可。
    """

    name = "mock"

    def __init__(self) -> None:
        self._settings = get_settings()

    def _sample_video(self) -> Path | None:
        # 复用仓库里已有的样例 mp4
        for d in (PROJECT_ROOT / "outputFiles", MEDIA_VIDEO_DIR):
            if not d.exists():
                continue
            files = sorted(d.glob("*.mp4"))
            if files:
                return files[0]
        return None

    async def request(self, req: VideoRequest) -> VideoHandle:
        sample = self._sample_video()
        if sample is None:
            return VideoHandle(
                ready=False,
                status="failed",
                error="MockProvider 未找到样例视频。请把任意 mp4 放到 outputFiles/ 或 media/video/ 下。",
            )

        # 复制成以 alarm_id 命名的文件，模拟"该告警的视频产物"
        target = MEDIA_VIDEO_DIR / f"{req.alarm_id}.mp4"
        try:
            if not target.exists():
                shutil.copyfile(sample, target)
        except OSError as exc:
            logger.exception("MockProvider 复制样例视频失败")
            return VideoHandle(ready=False, status="failed", error=str(exc))

        url = f"{self._settings.public_base_url.rstrip('/')}/media/video/{target.name}"
        return VideoHandle(
            ready=True,
            status="ready",
            url=url,
            handle=str(target),
            duration=int((req.end_time - req.start_time).total_seconds()),
        )


class FileProvider(VideoProvider):
    """★ 最理想的形态：同事产出标准 MP4 文件，我方只托管 URL。

    约定：同事把文件写到 MEDIA_VIDEO_DIR，文件名为 <alarm_id>.mp4
         （或通过 manifest 提供映射）。
    这样前端 <video src> 直接播，零依赖、不需要 ffmpeg。
    """

    name = "file"

    def __init__(self) -> None:
        self._settings = get_settings()

    async def request(self, req: VideoRequest) -> VideoHandle:
        target = MEDIA_VIDEO_DIR / f"{req.alarm_id}.mp4"
        if not target.exists():
            # 视频还没生成好 —— 返回 starting，前端继续轮询
            return VideoHandle(
                ready=False,
                status="starting",
                handle=str(target),
            )

        url = f"{self._settings.public_base_url.rstrip('/')}/media/video/{target.name}"
        return VideoHandle(
            ready=True,
            status="ready",
            url=url,
            handle=str(target),
            duration=int((req.end_time - req.start_time).total_seconds()),
        )

    async def poll(self, handle: VideoHandle) -> VideoHandle:
        if handle.handle and Path(handle.handle).exists():
            name = Path(handle.handle).name
            url = f"{self._settings.public_base_url.rstrip('/')}/media/video/{name}"
            return VideoHandle(
                ready=True,
                status="ready",
                url=url,
                handle=handle.handle,
                duration=handle.duration,
            )
        return handle


class HttpProvider(VideoProvider):
    """同事提供 HTTP 接口：我方请求后拿到 URL 或直接代理。

    这是「契约未定」时的通用适配器。约定见 docs §3.1④：
      POST {video_service_base}/decode
        body: {device_id, channel, start_time, end_time}
        resp: {status: "ready"|"starting"|"failed", url?, duration?, session_id?}
    """

    name = "http"

    def __init__(self) -> None:
        self._settings = get_settings()

    async def request(self, req: VideoRequest) -> VideoHandle:
        try:
            import httpx  # 可选依赖：仅 http provider 需要
        except ImportError:
            return VideoHandle(
                ready=False,
                status="failed",
                error="未安装 httpx。请 pip install httpx，或改用 ISUP_VIDEO_PROVIDER=file",
            )

        payload = {
            "device_id": req.device_id,
            "channel": req.channel,
            "start_time": req.start_time.isoformat(),
            "end_time": req.end_time.isoformat(),
        }
        url = f"{self._settings.video_service_base.rstrip('/')}/decode"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.exception("调用同事解码服务失败: %s", url)
            return VideoHandle(ready=False, status="failed", error=str(exc))

        status = data.get("status", "starting")
        return VideoHandle(
            ready=status == "ready",
            status=status,
            url=data.get("url"),
            handle=str(data.get("session_id") or ""),
            duration=data.get("duration"),
            error=data.get("error"),
        )

    async def poll(self, handle: VideoHandle) -> VideoHandle:
        try:
            import httpx
        except ImportError:
            return VideoHandle(
                ready=False,
                status="failed",
                error="未安装 httpx。请 pip install httpx，或改用 ISUP_VIDEO_PROVIDER=file",
            )

        if not handle.handle:
            return handle
        url = f"{self._settings.video_service_base.rstrip('/')}/decode/{handle.handle}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.exception("轮询同事解码服务失败")
            return VideoHandle(ready=False, status="failed", error=str(exc), handle=handle.handle)

        status = data.get("status", "starting")
        return VideoHandle(
            ready=status == "ready",
            status=status,
            url=data.get("url") or handle.url,
            handle=handle.handle,
            duration=data.get("duration"),
        )


_PROVIDERS: dict[str, type[VideoProvider]] = {
    "mock": MockProvider,
    "file": FileProvider,
    "http": HttpProvider,
}


def get_provider() -> VideoProvider:
    """按配置返回 Provider 实例。"""
    name = get_settings().video_provider.lower()
    cls = _PROVIDERS.get(name)
    if cls is None:
        logger.warning("未知的 video_provider=%s，回退到 mock", name)
        cls = MockProvider
    return cls()
