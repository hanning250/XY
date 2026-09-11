# 海康 NVR 防护服告警后端

接收海康 NVR / AI 摄像头的告警事件，入库并提供 REST API 查询。

## 架构

```
AI摄像头 → NVR → alarm-backend(SDK布防/HTTP推送) → SQLite → REST API
```

## 快速开始

### 1. 复制 SDK 库

```powershell
cd alarm-backend
python setup_libs.py
```

### 2. 修改配置

复制并编辑 `config.json`（参考 `config.example.json`）：

- `nvr.ip` / `username` / `password`：NVR 内网地址和账号
- `alarm_mode`：`deploy`（布防，推荐）或 `listen`（监听）
- `api.port`：后端 API 端口，默认 8080

### 3. 安装并启动

```powershell
pip install -r requirements.txt
python main.py
```

仅测试 API（不连 NVR）：

```powershell
python main.py --api-only
```

## 三种告警接收方式

| 方式 | config 设置 | 说明 |
|------|-------------|------|
| SDK 布防 | `"alarm_mode": "deploy"` | 后端登录 NVR 并布防，推荐 |
| SDK 监听 | `"alarm_mode": "listen"` | 后端开 7200 端口，NVR 配置报警主机 |
| HTTP 推送 | 无需 SDK | NVR 配置 ISAPI HTTP 推送到 `/api/hikvision/event` |

### 监听模式额外配置

`config.json` 中设置：

```json
"alarm_mode": "listen",
"listen": { "host": "0.0.0.0", "port": 7200 },
"alarm_host": { "ip": "192.168.1.100", "port": 7200 }
```

后端会自动把 NVR 的报警主机地址写成 `alarm_host`。

### NVR Web 配置（HTTP 推送）

1. 登录 NVR Web：`http://NVR_IP`
2. 配置 → 事件 → 事件通知 / 报警上传
3. 添加 HTTP 监听主机：
   - URL：`http://后端IP:8080/api/hikvision/event`
   - 内容类型：JSON（若可选）
4. 勾选 AI 事件 / 智能分析 / 未穿防护服 等相关事件

## API 接口

启动后访问：

- **监控页面**：`http://localhost:8080/`
- **Swagger 文档**：`http://localhost:8080/docs`
- **WebSocket 实时推送**：`ws://localhost:8080/ws/alarms`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/status` | SDK 连接状态 |
| GET | `/api/alarms` | 告警列表 |
| GET | `/api/alarms?ppe_only=true` | 仅防护服相关 |
| GET | `/api/alarms/{id}` | 单条详情 |
| GET | `/api/stats` | 统计 |
| GET | `/api/pictures/{filename}` | 告警图片 |
| WS | `/ws/alarms` | 新告警实时推送 |
| POST | `/api/hikvision/event` | ISAPI HTTP 推送入口 |

## 联调步骤

### 无 NVR 时（API-only）

终端 1：

```powershell
python main.py --api-only
```

终端 2：

```powershell
python test_push.py
curl http://127.0.0.1:8080/api/alarms?ppe_only=true
```

### 有 NVR 时

1. 修改 `config.json` 中 NVR IP 和密码
2. `python main.py`
3. 确认 `/api/status` 中 `alarm_service.state` 为 `connected`
4. 现场触发一次未穿防护服告警
5. 查看 `/api/alarms?ppe_only=true`

## 内网部署要求

```
公司内网
├── NVR          192.168.1.10
├── AI 摄像头     由 NVR 管理
└── 后端服务器    192.168.1.100  (固定 IP)
```

防火墙放行：

- 8000：SDK 登录/布防
- 8080：REST API / HTTP 推送
- 7200：监听模式（如使用）

## 单元测试

```powershell
python test_event_parser.py
```

## 常见问题

**Q: 启动报 NVR 登录失败？**  
检查 IP、端口 8000、账号密码；确认后端与 NVR 在同一局域网。

**Q: 能登录但收不到告警？**  
AI 事件通常走 `COMM_ISAPI_ALARM`；确认 NVR 上 AI 规则已启用并勾选上传中心。可改用 `listen` 模式或 HTTP 推送。

**Q: 收到告警但 ppe_only 为空？**  
查看 `/api/alarms` 中 `raw_payload`，把实际事件关键词加入 `event_filter_keywords`。

**Q: lib 缺少 DLL？**  
重新运行 `python setup_libs.py`。
