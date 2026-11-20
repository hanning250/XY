# ISUP 告警平台（精简源码）

从同事交接包抽出的**前后端基础源码**，已去掉一键部署、离线镜像、运维脚本、文档包等杂项。

## 目录

```
isup-alarm/
├─ server/       FastAPI 后端（API / 鉴权 / 告警聚合 / WebSocket）
├─ web/          Vue3 + Vite 前端源码
├─ src/          媒体清理等遗留工具（已无 ISUP SDK）
├─ lib/hcnetsdk  设备网路 SDK（布防收 ISAPI 报警）
└─ requirements.txt
```

## 本地开发

### 1. 后端（API-only，可不接设备）

```bash
cd isup-alarm
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp server/.env.example server/.env   # 已有则可跳过
# 本地联调务必确认：
#   ISUP_ENABLE_INTERNAL_API=true   # 前端看板依赖 /api/*
#   ISUP_ENABLE_WEB_UI=true
#   ISUP_AUTH_MODE=jwt
#   ISUP_ADMIN_USERNAME=admin
#   ISUP_ADMIN_PASSWORD=...
#   ISUP_CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173

uvicorn server.main:app --host 0.0.0.0 --port 8088 --reload
```

### 2. 前端

```bash
cd web
npm install
npm run dev          # http://127.0.0.1:5173
```

Vite 已把 `/api`、`/openapi`、`/media`、WebSocket 代理到 `127.0.0.1:8088`。

### 3. 接真实设备（ISAPI + HCNetSDK）

1. `server/.env` 配 `ISUP_ISAPI_HOST` / 密码，以及 `ISUP_HCNETSDK_DIR=…/lib/hcnetsdk`
2. 启动：`uvicorn server.main:app --host 0.0.0.0 --port 8088 --reload-dir server --reload-dir src`
3. 单端口托管前端时，先 `cd web && npm run build`，再：
   `uvicorn server.serve_web:app --host 0.0.0.0 --port 8088`

## 说明

- 告警走 HCNetSDK 布防（ISAPI 登录）；实况/录像走 HTTP ISAPI。已移除 ISUP 5.0 CMS/AMS/SS。
- 环境变量仍以 `ISUP_` 为前缀（历史命名，不是 ISUP 协议）。
- `server/.env` 含密钥类配置，勿提交到公开仓库。
