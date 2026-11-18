# -*- coding: utf-8 -*-
"""★ 审计中间件。

现在就挂上，将来接入用户体系后能查「谁在什么时候看了哪条告警」。
对外接口出事要能对账 —— 这是开放 API 的硬要求（docs §8.2）。

★ 2026-XX 并发修复：审计写库改为 **fire-and-forget**。
    原实现直接 await 写库 —— BaseHTTPMiddleware 下这会让每个请求
    在响应返回前多占一个数据库连接并串行等待写入，高并发时
    连接池被审计翻倍占用（正是当年打爆连接池的元凶之一）。
    现在把审计行丢进内存队列，由后台任务统一批量落库：
      · 响应路径零等待、零额外连接占用
      · 队列有界：极端时丢最旧的审计行（审计不比业务数据关键），
        不反压业务
"""

from __future__ import annotations

import asyncio
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from server.models import ApiAuditLog, PrincipalKind

logger = logging.getLogger(__name__)

# 只审计业务接口，避免把静态资源/文档刷爆
_AUDIT_PREFIXES = ("/api/", "/openapi/")
_SKIP_SUFFIXES = ("/auth/me", "/auth/config")

# ★ 不审计的路径（2026-09-30）
#
# 为什么排除这些：
#   ① 审计要**单独占一个数据库连接**。导出接口本身已占 1 个，
#      再叠加审计就是每请求 2 个 —— 甲方并发拉取时会打爆连接池。
#   ② 这些路径要么是只读探活（health），要么是字节流下载（media），
#      审计价值低但调用量极大。
_SKIP_EXACT = ("/openapi/v1/health", "/health")
_SKIP_PREFIXES = ("/openapi/v1/media/", "/openapi/v1/media/video/")

# 审计队列：有界，满了丢最旧（审计可牺牲，业务不可）
_AUDIT_QUEUE_MAX = 10000
_audit_queue: asyncio.Queue[ApiAuditLog] = asyncio.Queue(maxsize=_AUDIT_QUEUE_MAX)
_audit_worker_started = False
_dropped_count = 0


async def _audit_worker() -> None:
    """后台落库任务：攒批写入，失败不影响业务。"""
    from server.db import SessionLocal

    while True:
        rows: list[ApiAuditLog] = []
        try:
            rows.append(await _audit_queue.get())  # 等第一条
            # 10ms 内凑批 —— 高并发时一次事务写 N 条
            while len(rows) < 200:
                rows.append(_audit_queue.get_nowait())
        except asyncio.QueueEmpty:
            pass
        except asyncio.CancelledError:
            raise
        if not rows:
            continue
        try:
            async with SessionLocal() as db:
                db.add_all(rows)
                await db.commit()
        except Exception:
            logger.warning(
                "审计批量落库失败（丢弃 %d 条，不影响业务）", len(rows)
            )


def _ensure_audit_worker() -> None:
    """懒启动后台任务（第一次请求时）。"""
    global _audit_worker_started
    if _audit_worker_started:
        return
    try:
        asyncio.get_running_loop().create_task(_audit_worker())
        _audit_worker_started = True
    except RuntimeError:
        pass  # 没有运行中的事件循环（测试环境），跳过


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        should_audit = (
            path.startswith(_AUDIT_PREFIXES)
            and not path.endswith(_SKIP_SUFFIXES)
            and path not in _SKIP_EXACT
            and not path.startswith(_SKIP_PREFIXES)
        )

        started = time.perf_counter()
        response = await call_next(request)
        latency_ms = (time.perf_counter() - started) * 1000

        if not should_audit:
            return response

        _ensure_audit_worker()
        principal = getattr(request.state, "principal", None)
        # ★ 字段构造统一到 crud/security.build_audit_row()：
        #   过去这里手工 new ApiAuditLog、write_audit() 里再抄一份，
        #   两边字段口径迟早会漂移。
        from server.crud.security import build_audit_row

        row = build_audit_row(
            principal_kind=getattr(principal, "kind", PrincipalKind.ANONYMOUS.value),
            subject=getattr(principal, "subject", "anonymous"),
            method=request.method,
            path=path,
            status_code=response.status_code,
            latency_ms=round(latency_ms, 2),
            client_ip=request.client.host if request.client else None,
        )
        try:
            _audit_queue.put_nowait(row)
        except asyncio.QueueFull:
            # 队列满：丢一条最旧的（审计不阻塞业务）
            global _dropped_count
            try:
                _audit_queue.get_nowait()
                _audit_queue.put_nowait(row)
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                pass
            _dropped_count += 1
            if _dropped_count % 100 == 1:
                logger.warning(
                    "审计队列已满，累计丢弃 %d 条（业务不受影响）", _dropped_count
                )

        return response


# --------------------------------------------------------------------------
# ★ 授权到期拦截（2026-10-20）
#
# 到期后「全面停用」：除下列白名单，业务接口一律 403，前端只剩
# 「授权已到期」页 —— 但**登录与续期必须放行**，否则管理员连授权码
# 都没地方输入，系统就真成砖头了。
#
# 白名单理由：
#   /api/auth/    登录、当前身份、登出（不登录就没法续期）
#   /api/license  查授权状态 + 续期（拦截页与续期入口依赖它）
#   /internal/    内部 OpenAPI 文档（排障用，不含业务数据）
# 只拦 /api/ 与 /openapi/：**静态资源必须放行**，
# 否则拦截页本身都加载不出来（SPA 是从同一个端口托管的）。
# --------------------------------------------------------------------------
_LICENSE_ALLOW_PREFIXES = ("/api/auth/", "/api/license", "/internal/")
_LICENSE_ALLOW_EXACT = ("/health", "/openapi/v1/health")


class LicenseGateMiddleware(BaseHTTPMiddleware):
    """授权到期 → 业务接口 403（带到期日与续期指引）。

    ★ 2026-10-26：授权改成「服务器时间 + 10 分钟窗口续期码」后，
      这里同步改用 lic.status()，并把**服务器时间**一并返回 ——
      到期页要把这个时间显示给客户，让客户报给供应商换续期码。
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith(("/api/", "/openapi/")):
            return await call_next(request)
        if path in _LICENSE_ALLOW_EXACT or path.startswith(_LICENSE_ALLOW_PREFIXES):
            return await call_next(request)

        from server.services import license as lic

        if not lic.is_expired():
            return await call_next(request)

        info = lic.status()
        return JSONResponse(
            status_code=403,
            content={
                "detail": (
                    f"授权已到期（到期日 {str(info.get('expires_on'))[:10]}），"
                    "系统已停用。请联系供应商获取续期码。"
                ),
                "code": "license_expired",
                "expires_on": info.get("expires_on"),
                # ★ 客户要报给供应商的时间
                "server_now": info.get("server_now"),
                "server_window": info.get("server_window"),
                "renew_hint": info.get("renew_hint"),
            },
        )
