# -*- coding: utf-8 -*-
"""鉴权层（★ 预留设计，见 docs/技术选型与架构方案.md §5）。

核心思想：把「调用者身份」抽象成 Principal，Provider 可插拔。
  · 现在        → AnonymousProvider，全部放行
  · 开放 API    → ApiKeyProvider（甲方 IT 部门现在就要用）
  · 后续        → JwtProvider（登录注册）

业务代码只依赖 `Depends(require("alarm:read"))`，将来换实现不用改业务代码。
"""
