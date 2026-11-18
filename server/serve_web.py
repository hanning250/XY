# -*- coding: utf-8 -*-
"""可选：把构建好的前端（web/dist）挂到 FastAPI 上，实现单端口部署。

    .venv\\Scripts\\python.exe -m uvicorn server.serve_web:app --port 8080

⚠️ 实现要点（踩过的坑）：
   直接 `app.mount("/", StaticFiles(html=True))` 会**吞掉所有路由** ——
   Starlette 的 mount 是在路由匹配**之前**按前缀拦截的，
   于是 /api/* 和 /openapi/* 都变成 404/500。
   正确做法是：只挂 /assets 静态目录，然后用一个 catch-all 路由
   把「不是 API 前缀」的路径交给 SPA，API 路由保持优先匹配。

开发期仍然推荐前后端分开跑（vite dev 有 HMR），见 docs/运行说明.md。
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request

from server.config import PROJECT_ROOT
from server.main import app

logger = logging.getLogger(__name__)

DIST = PROJECT_ROOT / "web" / "dist"

# 这些前缀必须由后端处理，绝不能落到 SPA
_API_PREFIXES = ("api/", "openapi/", "media/", "docs", "redoc", "health")


def mount_spa(target: FastAPI) -> bool:
    # ★ 交付开关：enable_web_ui=False（默认）时不托管前端。
    #   甲方明确「不需要前端，只要后端接口」，所以交付机不提供 / 页面，
    #   避免暴露管理界面的存在。自用/开发时设 ISUP_ENABLE_WEB_UI=true 打开。
    from server.config import get_settings

    if not get_settings().enable_web_ui:
        logger.info("前端页面已关闭（ISUP_ENABLE_WEB_UI=false），/ 不提供任何页面")
        return False

    if not (DIST / "index.html").exists():
        logger.warning("未找到前端构建产物 %s，请先在 web/ 下执行 npm run build", DIST)
        return False

    # 1) 静态资源按前缀挂载（安全，不会吞路由）
    #    ★ Vite 产物文件名带内容哈希（index-DBScbmgw.js），内容一变文件名就变，
    #      因此可以放心长缓存 —— 现场大屏每次刷新省掉 1.2MB 下载。
    assets = DIST / "assets"
    if assets.exists():
        class _ImmutableAssets(StaticFiles):
            async def get_response(self, path, scope):
                resp = await super().get_response(path, scope)
                if resp.status_code == 200:
                    resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
                return resp

        target.mount("/assets", _ImmutableAssets(directory=str(assets)), name="assets")

    index_file = DIST / "index.html"

    # ★ 首页必须每次回源校验（no-cache = 可缓存但要先问服务器，命中 ETag 走 304）。
    #   之前这里没有任何 Cache-Control，浏览器按"启发式缓存"把 index.html
    #   存下来长期不回源 —— 结果前端重新构建后，用户（尤其现场大屏）一直跑旧包：
    #   声音还是旧版的 1 秒、新加的授权角标根本看不到，且刷新页面也没用。
    #   哈希资源可以长缓存，唯独这张 HTML 不能。
    _INDEX_HEADERS = {"Cache-Control": "no-cache, must-revalidate"}

    # 2) catch-all：只接管非 API 路径，API 路由因注册在前而优先匹配
    @target.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str, request: Request):
        if full_path.startswith(_API_PREFIXES):
            # 交给 FastAPI 的 404 处理，避免把 API 请求伪装成 HTML
            return JSONResponse(status_code=404, content={"code": 404, "message": "接口不存在"})

        # 存在的真实文件（favicon 等）直接返回
        candidate = (DIST / full_path).resolve()
        try:
            candidate.relative_to(DIST.resolve())
        except ValueError:
            return JSONResponse(status_code=404, content={"code": 404, "message": "非法路径"})
        if full_path and candidate.is_file():
            return FileResponse(candidate, headers=_INDEX_HEADERS)

        # 其余一律交给前端路由
        return FileResponse(index_file, headers=_INDEX_HEADERS)

    logger.info("前端已挂载 (SPA fallback): %s", DIST)
    return True


mount_spa(app)
