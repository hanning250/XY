# ISUP 告警平台（精简源码）

从同事交接包抽出的**前后端基础源码**，已去掉一键部署、离线镜像、运维脚本、文档包等杂项。

## 目录

```
isup-alarm/
├─ server/       FastAPI 后端（API / 鉴权 / 告警聚合 / WebSocket）
├─ web/          Vue3 + Vite 前端源码
├─ src/          海康 ISUP SDK Python 封装（CMS / AMS / SS / SMS）
├─ lib/          海康 ISUP 动态库（Windows .dll + Linux .so）
├─ resources/    isupConf.json 等运行配置
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
#   ISUP_ENABLE_ISUP_SDK=false      # 无设备时先关 SDK
#   ISUP_AUTH_MODE=anonymous
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

### 3. 接真实设备（ISUP）

1. 编辑 `resources/conf/isupConf.json`（监听 IP/端口、`ISUPKey` 与设备端一致）
2. `server/.env` 中设 `ISUP_ENABLE_ISUP_SDK=true`
3. 启动：`uvicorn server.main:app --host 0.0.0.0 --port 8088`
4. 单端口托管前端时，先 `cd web && npm run build`，再：
   `uvicorn server.serve_web:app --host 0.0.0.0 --port 8088`

## 说明

- 协议主体为 **ISUP 5.0**（CMS 注册 / AMS 报警 / SS 图片）；NVR 录像回放等能力会用到 ISAPI。
- 本目录不含 Docker / 一键部署 / 现场验收脚本；需要时再从原交接包取用。
- `server/.env` 含密钥类配置，勿提交到公开仓库。
