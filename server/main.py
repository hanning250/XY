# -*- coding: utf-8 -*-
"""FastAPI 应用入口。

启动顺序（很重要）：
  1. 建库建表
  2. 绑定事件循环到事件总线（SDK 回调需要）
  3. 启动聚合器 / 视频服务
  4. 最后才拉起 ISUP SDK 监听（此时总线已就绪）
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from server.api import (
    admin,
    alarms,
    auth,
    dev,
    devices,
    license as license_api,
    media,
    open_api,
    open_media,
    stats,
    videos,
    ws,
)
from server.config import STORAGE_DIR, get_settings
from server.db import SessionLocal, dispose_db, init_db
from server.middleware import AuditMiddleware, LicenseGateMiddleware
from server.services.bus import bus
from server.services.correlator import Correlator
from server.services.video_service import VideoService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # 1) 建表
    await init_db()

    # 1.2) ★ JWT 模式：确保管理员可登录（本机用环境变量固定账号密码）
    if settings.auth_mode.lower() == "jwt":
        from server.crud import user as user_crud

        admin_name = (settings.admin_username or "admin").strip() or "admin"
        admin_pwd = (settings.admin_password or "").strip() or None
        async with SessionLocal() as db:
            user, created_pwd = await user_crud.ensure_admin(
                db, username=admin_name, password=admin_pwd
            )
            if created_pwd is not None:
                if admin_pwd:
                    logger.info(
                        "已创建管理员账号 %s（密码来自 ISUP_ADMIN_PASSWORD）",
                        admin_name,
                    )
                else:
                    logger.warning(
                        "已创建管理员账号 %s，初始密码（仅显示一次）: %s",
                        admin_name,
                        created_pwd,
                    )
            elif admin_pwd:
                # 已存在：仅当环境变量密码与库里不一致时才同步
                # （密码未变则不动 token；环境变量改密时才同步）
                from server.auth.tokens import verify_password

                if not verify_password(admin_pwd, user.password_hash):
                    await user_crud.set_password(db, user=user, password=admin_pwd)
                    logger.info(
                        "管理员账号 %s 已按 ISUP_ADMIN_PASSWORD 同步密码",
                        admin_name,
                    )
                else:
                    logger.info("管理员账号已就绪: %s", admin_name)
            else:
                logger.info("管理员账号已存在: %s", admin_name)

    # 1.3) ★ 历史告警回填 rule_name / person_count（筛选与分类统计依赖）
    try:
        from server.crud import alarm as alarm_crud

        async with SessionLocal() as db:
            n_bf = await alarm_crud.backfill_rule_fields(db)
            if n_bf:
                logger.info("已回填 %d 条历史告警的规则名/人次字段", n_bf)
    except Exception:
        logger.exception("历史告警字段回填失败（不影响启动）")

    # 1.5) ★ 软件授权：首次启动即激活（授权期 = 首次启动 + 365 天）
    #   打包脚本排除 data/，所以客户现场解包首启就是新的一轮授权。
    #
    # ★★ 2026-10-26：授权改成「服务器时间 + 10 分钟窗口续期码」，
    #    接口从 license_info() 改为 status()，字段也变了：
    #      expire_at → expires_on
    #      去掉 state / months_left（用 days_left 换算）
    from server.services import license as lic_svc

    _lic = lic_svc.status()
    _exp = str(_lic.get("expires_on") or "?")[:10]
    _days = int(_lic.get("days_left") or 0)

    if _lic.get("expired"):
        logger.error(
            "★ 授权已到期：到期日 %s。业务接口已停用，"
            "请联系供应商获取续期码（当前服务器时间 %s）。",
            _exp,
            _lic.get("server_now"),
        )
    elif _days <= 30:
        logger.warning(
            "★ 授权即将到期：剩余 %d 天，到期日 %s，请及时续期。",
            _days,
            _exp,
        )
    else:
        logger.info(
            "★ 授权有效：激活日 %s，到期日 %s，剩余约 %d 个月",
            str(_lic.get("activated_at") or "?")[:10],
            _exp,
            _days // 30,
        )

    # 2) 绑定事件循环 —— 必须在 SDK 回调启动前
    bus.bind_loop(asyncio.get_running_loop())

    # 2.5) ★ 积压追补自愈：把近 2 小时内的孤儿图片重置回待配对队列。
    #   ⚠️ 必须在 correlator.start()（其启动任务会在 0.5s 后跑追补）
    #   和巡检循环（会把 arrived_at 超过 5 分钟的图再标成孤儿）之前执行。
    #   场景：重启期间设备积压的补传图错过了匹配窗口成了孤儿，
    #   重置后由追补逻辑 FIFO 回填给最早的没图告警。
    from server.services.workshop_service import reset_recent_orphans

    async with SessionLocal() as db:
        n_orphan = await reset_recent_orphans(db, within_minutes=120)
        if n_orphan:
            logger.info(
                "积压追补：%d 张近期孤儿图片已重新入队（启动追补将自动回填）",
                n_orphan,
            )

    # 3) 启动业务服务
    correlator = Correlator(bus)
    await correlator.start()
    app.state.correlator = correlator

    video_service = VideoService()
    await video_service.start()
    app.state.video_service = video_service

    # 3.5) ★ 媒体清理：启动时跑一次 + 按间隔定时清理
    cleanup_task = asyncio.create_task(_cleanup_loop())
    app.state.cleanup_task = cleanup_task

    # 4) 拉起 ISUP SDK（失败不阻断服务，便于前端先跑通）
    from server.adapters.isup_runtime import runtime as isup_runtime

    loop = asyncio.get_running_loop()
    started = await loop.run_in_executor(None, isup_runtime.start)
    app.state.isup_runtime = isup_runtime
    app.state.isup_ok = started
    if not started:
        logger.warning(
            "ISUP SDK 未启动（原因：%s）。服务继续以 API-only 模式运行。",
            isup_runtime.last_error,
        )

    # 4.2) ★ 启动清零设备在线状态
    #   进程重启后设备与旧进程的连接必然已断，残留的 online=1 是
    #   「假在线」（新进程收不到离线事件）。设备重新注册时会自动翻回在线。
    from server.crud.device import mark_all_offline

    async with SessionLocal() as db:
        await mark_all_offline(db)

    # 4.5) ★ 回放服务：必须在 SDK 起来之后，才能拿到 sms 实例
    from server.services.playback_service import playback_service

    playback_service.bind_loop(loop)
    playback_service.set_done_callback(_on_playback_done)
    if started:
        sms = getattr(isup_runtime, "sms", None)
        if sms is not None:
            playback_service.register_sms(sms)
            logger.info("回放服务已注入 SMS，可抓取设备录像")
        else:
            logger.warning("未能从 isup_runtime 取得 sms 实例，回放抓取不可用")
    playback_service.start()
    app.state.playback_service = playback_service

    # 4.6) ★ 把回放服务注入聚合器 → 告警落库后自动抓取 ±30s 视频片段。
    #      IT 部门按天批量拉取，拉的时候视频必须已生成好。
    correlator.set_playback_service(playback_service)
    if settings.video_auto_capture:
        logger.info(
            "★ 视频自动抓取已启用（每条告警抓 %ds 前置 + %ds 后置，队列上限 %d）",
            settings.video_pre_seconds,
            settings.video_post_seconds,
            settings.video_auto_max_queue,
        )

    # ★ 交付风险提示（2026-XX 安全审查）：
    #   video_provider=mock 时，MediaVideoService 会把**样例视频**复制成
    #   {alarm_id}.mp4 —— 甲方通过 /openapi/v1/media/video/{id}.mp4 拿到的是
    #   与告警无关的画面，且一切看起来"正常"。交付机必须确认 provider 已切到
    #   file / http（或 sms 回放），否则报错比静默给假视频安全得多。
    if settings.video_provider.lower() == "mock":
        logger.warning(
            "★ video_provider=mock：媒体接口将返回与告警无关的样例视频！\n"
            "    开发联调用；交付机请设置 ISUP_VIDEO_PROVIDER=file 或 http。"
        )

    # ★ 交付提示：开放接口会优先使用有效 public_base_url，否则按请求 Host
    #   生成媒体链接；经过反向代理、网关或 NAT 时需配置甲方可访问的入口地址。
    _base = (settings.public_base_url or "").lower()
    if any(h in _base for h in ("127.0.0.1", "localhost", "0.0.0.0", "[::1]")):
        logger.warning(
            "★ public_base_url 指向本机（%s）：开放接口将按请求 Host 生成媒体 URL。"
            "若经反向代理或网关访问，请设置 ISUP_PUBLIC_BASE_URL 为甲方可访问的入口。",
            settings.public_base_url,
        )

    logger.info("服务已就绪 -> %s", settings.public_base_url)
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except (asyncio.CancelledError, Exception):
            pass
        playback_service.stop()
        await video_service.stop()
        await correlator.stop()
        if started:
            await loop.run_in_executor(None, isup_runtime.stop)
        await dispose_db()
        logger.info("服务已停止")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="行为规范识别系统 · 对外接口",
        version="1.0.0",
        description=(
            "## 本页接口供甲方信息课（IT 部门）对接使用\n\n"
            "现场摄像头识别员工不规范行为后，系统保存抓拍图片、"
            "前后 30 秒视频片段与准确时间，通过本组接口对外提供。\n\n"
            "### 特点\n\n"
            "- **无需鉴权**：内网直接调用即可\n"
            "- **只读**：不会修改任何数据\n"
            "- **按车间分组**：用 `?workshop=A` 参数指定车间\n"
            "- **按天拉取**：`?date=2026-09-28&workshop=A`\n\n"
            "### 建议的调用顺序\n\n"
            "1. `GET /openapi/v1/health` — 测试连通性\n"
            "2. `GET /openapi/v1/workshops` — 获取车间列表\n"
            "3. `GET /openapi/v1/alarms?workshop=A&date=...` — 拉取数据\n\n"
            "### 对接文档\n\n"
            "完整说明（含示例代码、常见问题）见《接口手册》。\n\n"
            "> ⚠️ 本接口仅限**内网**使用，请勿暴露至公网。\n\n"
            f"> 导入 Postman / Apifox 时，base url 填 `{settings.public_base_url}`。"
        ),
        lifespan=lifespan,
        # ★ 有了 servers，导入 Postman/Yaak/Apifox 才能自动带出 base url。
        servers=[{"url": settings.public_base_url, "description": "当前部署地址"}],
        docs_url="/docs",
        redoc_url=None,  # 只保留 Swagger，避免两个文档页冗余
        openapi_url="/openapi.json",
    )

    # ★ 开放接口**不需要鉴权**（甲方要求），所以不再往契约里塞
    #   X-API-Key 之类的 securitySchemes —— 否则 Swagger 上会出现
    #   「Authorize」按钮，让甲方以为要填密钥。
    #
    #   自定义 openapi：只做「过滤掉内部接口」这一件事。
    #   正常情况下 include_in_schema=False 已经把它们排除在外了，
    #   这里再兜一层，防止将来有人漏加该参数导致内部接口泄漏到 /docs。
    _original_openapi = app.openapi

    def _custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = _original_openapi()

        # 只保留对外接口（/openapi/v1/**）
        #
        # ★ 2026-09-30：不再放行顶层的 /health。
        #   它是我方的内部探活接口（返回 sdk 状态、ws 订阅数等内部信息），
        #   与对外的 /openapi/v1/health 不是同一个东西。
        #   手册向甲方承诺「/docs 只含对外接口」，
        #   放它进来会让这句话不成立。
        allowed_prefix = "/openapi/v1"
        schema["paths"] = {
            p: ops
            for p, ops in schema.get("paths", {}).items()
            if p.startswith(allowed_prefix)
        }
        # 清掉无用的安全声明
        schema.get("components", {}).pop("securitySchemes", None)

        app.openapi_schema = schema
        return schema

    app.openapi = _custom_openapi

    # 审计中间件（现在就挂，为将来的用户体系留痕）
    app.add_middleware(AuditMiddleware)

    # ★ 授权到期拦截（2026-10-20）：放在最外层 —— 已停用的系统里
    #   业务请求直接被挡在门口，不产生审计噪声（拦截页会反复轮询）。
    app.add_middleware(LicenseGateMiddleware)

    # ---- CORS（2026-XX 安全审查修复）----
    # 默认**不开** CORS：开放 API 不鉴权，若 allow_origins=["*"]，
    # 内网任何用户随便打开的一个网页都能跨域读取告警/图片/视频。
    # 开发期前后端分离时，在 .env 里显式配 ISUP_CORS_ORIGINS（如 Vite 5173）。
    _cors = settings.cors_origins.strip()
    if _cors:
        origins = [o.strip() for o in _cors.split(",") if o.strip()]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info("CORS 已启用，来源: %s", origins)
    else:
        logger.info("CORS 未启用（同源部署；如需跨域请配置 ISUP_CORS_ORIGINS）")

    # ---- 路由 ----
    #
    # ★ 内部接口开关（2026-09-30）：
    #   enable_internal_api=False（交付默认）→ **根本不注册** /api/*，
    #     甲方能用的只剩 /openapi/v1 的 9 个接口。
    #     「不存在」比「存在但锁着」更干净 —— 攻击面为零。
    #
    #   enable_internal_api=True（开发/自用）→ 照常注册，但**从 /docs 隐藏**，
    #     只在 /internal/docs（需 admin 登录）查看。
    #
    #   我方的车间分配 / 账号管理 CLI 脚本直连数据库，不走 HTTP，
    #   因此关掉内部接口**不影响交付机的运维操作**。
    _internal = settings.enable_internal_api

    if _internal:
        # 文档可见性：
        #   主 /docs 只展示对外开放接口；内部接口不进主文档，
        #   改到 /internal/docs（需 admin 登录）查看。
        app.include_router(auth.router, prefix="/api", include_in_schema=False)
        app.include_router(admin.router, prefix="/api", include_in_schema=False)
        # ★ 统计（按车间的报警频率，按账号车间权限过滤）
        app.include_router(stats.router, prefix="/api", include_in_schema=False)
        app.include_router(ws.router, prefix="/api", include_in_schema=False)
        app.include_router(alarms.router, prefix="/api", include_in_schema=False)
        app.include_router(videos.router, prefix="/api", include_in_schema=False)
        app.include_router(media.router, prefix="/api", include_in_schema=False)
        app.include_router(devices.router, prefix="/api", include_in_schema=False)
        app.include_router(ws.ws_router, prefix="/api", include_in_schema=False)
        # ★ 授权：查状态 + 授权码续期（到期后仍可用，否则没法续期）
        app.include_router(license_api.router, prefix="/api", include_in_schema=False)
        # ★ 调试接口（模拟报警等）：仅 ISUP_DEBUG=true 时注册，交付机不存在
        if settings.debug:
            app.include_router(dev.router, prefix="/api", include_in_schema=False)
            logger.warning("★ 调试接口已启用（/api/dev/*，模拟报警用）—— 交付机请设 ISUP_DEBUG=false")
        logger.info("内部接口已启用（/api/*，文档见 /internal/docs）")
    else:
        logger.info(
            "★ 内部接口已关闭（ISUP_ENABLE_INTERNAL_API=false）："
            "仅暴露 /openapi/v1/* 对外接口。"
            "管理操作请用 scripts/user_admin.py（直连数据库）。"
        )

    # ★ 开放 API（甲方 IT 部门）—— **唯一出现在 /docs 上的分组**
    #   ⚠️ 按甲方要求**不鉴权** —— 只应在内网暴露本服务。
    app.include_router(open_api.router)
    app.include_router(open_media.router)

    # ---- 媒体文件（★ 受车间隔离保护）----
    # 原来是 StaticFiles 直接挂载 —— **完全公开**，知道 URL 就能下载任意图片，
    # 绕过所有接口鉴权。现改为带鉴权的路由：
    #   /media/2026/09/28/xxx.jpg  →  校验该图所属告警的车间是否可见
    # 见 server/api/media_files.py
    #
    # ★ 交付模式（_internal=False）**不注册**内部 /media/* ——
    #   这条路径是给我们自己的前端看图用的，甲方该用 /openapi/v1/media/*。
    #   不注册的话攻击面更小：连"带 token 才能看图"这条路都不存在。
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    _video_dir()
    if _internal:
        from server.api import media_files

        app.include_router(media_files.router)

    # ---- 统一异常处理：开放 API 也要返回 JSON 而不是 HTML ----
    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        logger.exception("未处理异常: %s %s", request.method, request.url.path)

        # ★ 连接池耗尽要给出「可操作」的提示，而不是把 SQLAlchemy 的
        #   长串内部错误直接抛给甲方（既看不懂，也泄露内部实现）。
        from sqlalchemy.exc import TimeoutError as SATimeoutError

        if isinstance(exc, SATimeoutError) and "QueuePool" in str(exc):
            logger.error(
                "★ 数据库连接池耗尽（当前并发过高）。"
                "甲方并发拉取时请控制并发数（建议 ≤10），或调大 ISUP 连接池配置。"
            )
            return JSONResponse(
                status_code=503,
                content={
                    "code": 503,
                    "message": "服务器繁忙，请稍后重试（建议降低并发，逐个车间顺序拉取）",
                    "data": None,
                },
                headers={"Retry-After": "5"},
            )

        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "服务内部错误，请联系我方处理", "data": None},
        )

    if _internal:
        # 内部探活：返回 SDK 状态等**内部信息**，只在自用模式下暴露。
        # 交付模式（_internal=False）不注册 —— 甲方没有理由知道 SDK 是否在线，
        # 这属于内部实现细节。
        @app.get("/health", tags=["服务状态"], summary="服务健康检查（无需鉴权）")
        async def health():
            from server.adapters.isup_runtime import runtime as isup_runtime

            return {
                "status": "ok",
                "isup_sdk_started": getattr(app.state, "isup_ok", False),
                "isup_note": isup_runtime.last_error,
                "ws_subscribers": bus.subscriber_count,
            }
    # 交付模式下甲方的探活走 /openapi/v1/health（不泄露内部实现）。

    # ---- ★ 内部接口文档（含全部接口，不给甲方）----
    #
    # 仅 enable_internal_api=True 时才存在。
    # 实现方式：**另外建一个 FastAPI 实例**，把同一批 router 以
    # include_in_schema=True 重新注册一遍，只用它生成文档，
    # 不承载业务请求（业务请求仍由主 app 处理）。
    # 这样比「临时替换 app.openapi 再换回来」可靠得多，也没有全局状态副作用。
    if _internal:
        from fastapi import FastAPI as _FastAPI

        internal_app = _FastAPI(
            title="ISUP 平台 · 内部接口文档",
            version="1.0.0",
            description=(
                "## ⚠️ 内部接口文档（请勿外发）\n\n"
                "本页包含平台全部接口，**仅供我方开发与运维使用**。\n\n"
                "- `/api/*`：内部接口，**需要登录**（JWT），按车间隔离\n"
                "- `/openapi/v1/*`：对外开放接口，无需鉴权\n\n"
                "对外接口的干净版本请访问 `/docs`。"
            ),
            docs_url="/internal/docs",
            openapi_url="/internal/openapi.json",
            redoc_url=None,
        )
        # 把内部 router 重新注册（这次 include_in_schema 默认为 True）
        internal_app.include_router(auth.router, prefix="/api")
        internal_app.include_router(admin.router, prefix="/api")
        internal_app.include_router(stats.router, prefix="/api")
        internal_app.include_router(ws.router, prefix="/api")
        internal_app.include_router(alarms.router, prefix="/api")
        internal_app.include_router(videos.router, prefix="/api")
        internal_app.include_router(media.router, prefix="/api")
        internal_app.include_router(devices.router, prefix="/api")
        internal_app.include_router(license_api.router, prefix="/api")
        internal_app.include_router(open_api.router)
        internal_app.include_router(open_media.router)

        # 把内部文档的两个页面挂到主 app 上（只是 HTML + JSON，无业务逻辑）
        #
        # ★ 这两个页面**必须鉴权**：
        #   否则任何人访问 /internal/openapi.json 就能拿到全部内部接口清单
        #   （含 /api/admin/users/{id}/password），而 /docs 又向甲方承诺
        #   「不含任何内部接口」，属于自相矛盾的暴露面。
        #
        #   鉴权方式：带 admin 的 JWT（同 Authorization 头或 ?token=）。
        async def _require_internal_admin(request: Request) -> None:
            from server.auth.jwt_auth import principal_from_claims
            from server.auth.tokens import TokenError, decode_token

            raw = ""
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                raw = auth[7:].strip()
            if not raw:
                raw = request.query_params.get("token", "").strip()

            if not raw:
                raise HTTPException(status_code=401, detail="需要登录")
            try:
                claims = decode_token(raw, secret=settings.jwt_secret)
            except TokenError:
                raise HTTPException(status_code=401, detail="token 无效或已过期")

            # ★ 补上账号状态校验：停用/已删账号的 token 一律拒绝
            principal = await principal_from_claims(claims)
            if principal is None:
                raise HTTPException(status_code=401, detail="token 无效或账号已停用")

            if not principal.superuser:
                raise HTTPException(status_code=403, detail="需要管理员权限")

        @app.get("/internal/docs", include_in_schema=False)
        async def internal_docs_page(request: Request):
            from fastapi.openapi.docs import get_swagger_ui_html

            await _require_internal_admin(request)
            token = request.query_params.get("token", "")
            suffix = f"?token={token}" if token else ""
            return get_swagger_ui_html(
                openapi_url=f"/internal/openapi.json{suffix}",
                title="ISUP 平台 · 内部接口文档",
            )

        @app.get("/internal/openapi.json", include_in_schema=False)
        async def internal_openapi_json(request: Request):
            await _require_internal_admin(request)
            return JSONResponse(internal_app.openapi())

    return app


async def _on_playback_done(alarm_id: str) -> None:
    """回放任务结束时由 worker 线程调度回来：读最新状态并推给前端。

    ★ 这里在 asyncio 侧执行，可以安全用 async session。
    """
    from server.crud import alarm as alarm_crud
    from server.db import SessionLocal
    from server.services.serialize import alarm_brief

    try:
        async with SessionLocal() as db:
            alarm = await alarm_crud.get_alarm(db, alarm_id)
            if alarm is None:
                # 告警已被删除 —— worker 会把产物清掉，这里什么都不用做
                logger.info("回放完成但告警 %s 已删除，跳过推送", alarm_id)
                return
            payload = alarm_brief(alarm).model_dump(mode="json")
        await bus.publish({"type": "alarm_updated", "data": payload})
    except Exception:
        logger.exception("推送回放结果失败 alarm=%s", alarm_id)


def _video_dir():
    from server.config import MEDIA_VIDEO_DIR

    MEDIA_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    return MEDIA_VIDEO_DIR


async def _cleanup_loop() -> None:
    """★ 媒体清理循环：启动跑一次，之后按 cleanup_interval_hours 周期跑。

    失败不阻断服务 —— 清理只是运维动作，不该影响告警接入。
    """
    from server.db import SessionLocal
    from server.services import cleanup as cleanup_svc

    settings = get_settings()

    if settings.cleanup_on_startup:
        try:
            async with SessionLocal() as db:
                res = await cleanup_svc.cleanup_by_retention(db, dry_run=False)
            logger.info(
                "启动清理完成：删除 %s 个文件（%.2f MB），标记 %s 条告警媒体过期",
                res["deleted"],
                res["bytes_freed"] / 1024 / 1024,
                res["alarms_marked"],
            )
        except Exception:
            logger.exception("启动清理失败（不影响服务运行）")

    interval = settings.cleanup_interval_hours
    if interval <= 0:
        logger.info("定时清理已关闭（cleanup_interval_hours=0）")
        return

    while True:
        try:
            await asyncio.sleep(interval * 3600)
            async with SessionLocal() as db:
                res = await cleanup_svc.cleanup_by_retention(db, dry_run=False)
            logger.info(
                "定时清理完成：删除 %s 个文件，标记 %s 条告警",
                res["deleted"],
                res["alarms_marked"],
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("定时清理失败")


app = create_app()
