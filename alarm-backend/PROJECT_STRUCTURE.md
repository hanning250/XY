# 项目结构

```
alarm-backend/
│
├── main.py                    ★ 主程序入口（python main.py 或 uv run python main.py）
├── start.py / start.bat       ★ 一键启动（自动查环境/装依赖/拷运行库）
├── config.json                ★ 配置文件（改端口、关键词、标签映射）
├── pyproject.toml + uv.lock      uv 依赖声明（加依赖用 uv add）
├── requirements.txt              给不用 uv 的人（pip install -r）
├── setup_libs.py                 从 new_sdk 拷 ISUP DLL 到 lib_isup/
├── README.md                     使用文档（怎么跑、怎么对接甲方）
└── PROJECT_STRUCTURE.md          本文件（东西都在哪）
│
├── core/                      设备接入层 —— ISUP 协议相关
│   ├── hcisup.py                 ISUP SDK 的 ctypes 绑定（DLL 加载、结构体、API）
│   └── alarm_service.py          报警服务：注册监听 + 报警监听 + 回调入队 + worker
│
├── web/                       REST API 层 —— 对外给甲方 IT 用的
│   ├── api.py                    所有 HTTP 路由（/api/alarms 等）
│   ├── schemas.py                接口响应模型（Pydantic）+ 行→模型转换
│   ├── notifier.py               WebSocket 实时推送
│   └── static/index.html         监控页面
│
├── common/                    公共层 —— 与协议/HTTP 都无关的业务逻辑
│   ├── event_parser.py           解析报警 JSON（AIOP 算法结果、ISAPI 字段）
│   ├── storage.py                SQLite 存储（建表、迁移、增删查）
│   └── alarm_view.py             告警记录序列化 + 落库后推送（core 和 web 都要用）
│
├── tools/                     工具 —— 现场诊断和本地测试用
│   ├── doctor.py                 ★ 现场自检（设备连不上时先跑这个）
│   ├── simulate_alarm.py         假报警模拟器（不用盒子就能测全链路）
│   └── push_test.py              HTTP 推送测试（备用入口用）
│
├── tests/                     单元测试
│   └── test_alarm_flow.py        不用设备，手工拼 SDK 内存布局验证全流程
│
├── lib_isup/                  ISUP SDK 运行库（由 setup_libs.py 生成，不入库）
├── data/                      运行时数据：alarms.db + pictures/（不入库）
└── IsupLog_Python/            SDK 日志（不入库）
```

## 该去哪个文件改东西

| 我想改… | 改这个文件 |
|---------|-----------|
| 监听端口、协议、接入安全模式 | `config.json` → `isup` 段 |
| 什么算"防护服告警"的关键词 | `config.json` → `event_filter_keywords` |
| 算法类别号（`obj.type`）的中文名 | `config.json` → `aiop_type_labels` |
| 加一个 REST 接口 | `web/api.py` |
| 接口返回的字段 | `web/schemas.py` |
| 报警类型（0x.. 那些）的处理逻辑 | `core/alarm_service.py` → `_handle_alarm` |
| 图片怎么从回调里抠出来 | `core/alarm_service.py` → `_copy_isapi` |
| SDK 结构体定义、DLL 加载 | `core/hcisup.py` |
| 数据库表结构 / 加字段 | `common/storage.py` → `_init_db` / `_migrate` |
| 报警 JSON 的解析规则 | `common/event_parser.py` |
| 接口返回里图片URL怎么拼 | `common/alarm_view.py` → `_picture_urls` |
| 监控页面样式 | `web/static/index.html` |
| 启动前的环境检查 | `start.py` |

## 报警数据是怎么流动的

```
设备(盒子)
   │ ①ISUP 注册到 :7660
   ▼
core/hcisup.py ── NET_ECMS_StartListen ──▶ core/alarm_service.py
   │                                          _on_device_register()
   │                                          → 记录设备到 self._devices
   │
   │ ②ISUP 上报报警到 :7661
   ▼
   NET_EALARM_StartListen ──▶ _on_alarm_msg()
                              只做 memcpy + 入队（SDK 要求 <10ms）
                                    │
                                    ▼
                              queue.Queue（上限 2000）
                                    │
                                    ▼
                              worker 线程 _consume_loop()
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              存图片到           解析 JSON       写 SQLite
              data/pictures/   common/          common/
                               event_parser.py  storage.py
                                    │
                                    ▼
                              web/notifier.py → WebSocket 推给页面
                                    │
                                    ▼
                              web/api.py  ← 甲方 IT 来 GET
```

**为什么要队列**：ISUP SDK 头文件明确规定「严禁在报警回调中调用 SDK 外部接口，
耗时不宜超过 10ms」。所以回调里只拷贝字节入队，重活全在 worker 线程。
`tests/test_alarm_flow.py` 里有一条专门断言这个（回调必须 <10ms）。

## 三条常用命令

```powershell
# 启动服务
uv run python main.py

# 现场诊断（设备连不上时）
uv run python tools/doctor.py --wait 300

# 本地测试（不用盒子）
uv run python tools/simulate_alarm.py --start     # 终端1
uv run python tools/simulate_alarm.py --count 3   # 终端2

# 跑测试
uv run python -m unittest discover -s tests -t .
```

> `tools/doctor.py` 和 `main.py` **不能同时跑** —— 都抢 7660/7661。

## 依赖方向（改代码时别搞出循环导入）

```
main.py
  ├─→ core/alarm_service.py ─→ core/hcisup.py
  │        │                └→ common/alarm_view.py   （落库后推 WebSocket）
  │        └─→ common/event_parser.py
  ├─→ common/storage.py
  └─→ web/api.py ─→ web/schemas.py ─→ common/alarm_view.py
                └→ web/notifier.py
                └→ common/event_parser.py
```

规则（单向，别反向）：

```
common  ←  core  ←  main
   ↑
  web
```

- `common` **不依赖** `core` 和 `web`
- `core` **不依赖** `web`（早期 `core` 从 `web/helpers.py` 拿序列化函数，
  是反向依赖，已把那段挪到 `common/alarm_view.py` 修掉）
- 新增共享逻辑一律放 `common`
