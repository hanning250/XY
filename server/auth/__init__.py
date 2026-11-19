# -*- coding: utf-8 -*-
"""鉴权层。

核心思想：把「调用者身份」抽象成 Principal，Provider 可插拔。
  · 内部 API  → JwtProvider（登录）或 ApiKeyProvider
  · 开放 API  → ApiKeyProvider（须 X-API-Key）

业务代码只依赖 `Depends(require("alarm:read"))`。
"""
