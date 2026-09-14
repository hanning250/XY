# 海康 ISUP（EHome）防护服告警后端

通过**海康 ISUP / EHome 协议**接收算力盒子主动上报的告警与图片，入库并提供 REST API 给甲方 IT 取用。

> 本项目早期用的是「设备网络 SDK（HCNetSDK）」，靠服务器登录设备布防。
> 现已整体切换到 ISUP 协议，老的 NET 代码已删除。两者的区别见下。

## 架构（重点：方向反了）

```
老 NET SDK：  服务器 ──登录/布防──▶ 设备          （服务器是客户端，需要设备账号密码）
新 ISUP：     设备 ──注册/上报──▶ 服务器          （服务器是服务端，不需要设备账号密码）
```

```
┌──────────────┐   ①注册(设备ID+密钥)   ┌─────────────────────────────┐
│  算力盒子     │ ─────────────────────▶ │  alarm-backend              │
│  AI摄像头     │   端口 register_port    │  ├ NET_ECMS_StartListen 7660│
│              │                         │  └ NET_EALARM_StartListen   │
│              │   ②报警+图片            │       7661                  │
│              │ ─────────────────────▶ │      ↓ 队列                  │
└──────────────┘   端口 alarm_port       │   worker线程                 │
                                         │   → 存图 → 入库 → WS推送     │
                                         └──────────┬──────────────────┘
                                                    │ REST API
                                                    ▼
                                            甲方 IT 系统
```

服务器不需要知道设备在哪，是**设备来连你**。所以 `config.json` 里没有设备 IP / 账号密码，
只有本机监听地址和端口。

## 怎么运行（最快路径）

本项目是 **uv 项目**（`pyproject.toml` + `uv.lock`），推荐用 uv 管环境。

**方式一：双击 `start.bat`**（自动优先用 uv，没 uv 就退回 `.venv`）

**方式二：uv（推荐）**

```powershell
cd D:\work\xinyiwork\XY\alarm-backend
uv sync                    # 建环境 + 按 uv.lock 装依赖（首次）
uv run python start.py     # 启动
```

**方式三：venv + pip**

```powershell
cd D:\work\xinyiwork\XY\alarm-backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe start.py
```

`start.py` 会依次做 5 项检查，任何一项不过都会明确告诉你差什么、怎么补：

```
1/5  Python 环境        位数、平台、uv 是否可用
2/5  ISUP SDK 运行库    缺了会自动从 new_sdk 拷
3/5  Python 依赖        缺了提示安装命令（加 --install 自动装，优先走 uv add）
4/5  配置检查           端口冲突、JSON 格式
5/5  启动服务
```

| 参数 | 作用 |
|------|------|
| `python start.py --check` | 只做环境检查，不启动 |
| `python start.py --install` | 缺依赖时自动安装（uv 项目走 `uv add`） |
| `python start.py --api-only` | 只起接口，不开 ISUP 监听 |

### 常用 uv 命令

```powershell
uv sync                  # 按 uv.lock 同步环境（换机器/拉代码后第一条）
uv add <包名>            # 加依赖（会同时更新 pyproject.toml 和 uv.lock）
uv remove <包名>         # 删依赖
uv run python main.py    # 在项目环境里跑，不用手动激活 venv
uv lock --upgrade        # 升级依赖锁
```

> **`uv` 命令找不到？** uv 可能装在 `%APPDATA%\Python\Scripts` 但没加进 PATH。
> 把那个目录加进系统环境变量 Path 即可，或直接用绝对路径调用。

## 手动运行（了解原理时看）

### 1. 拷贝 SDK 运行库

ISUP SDK 在 `../new_sdk/HCISUPSDKV2.5.1.35_build20241101_Win64_ZH`，
运行库需要拷进项目（SDK 目录在工作区外，不能直接引用）：

```powershell
cd alarm-backend
python setup_libs.py
```

拷进来的东西在 `lib_isup/`：`HCISUPCMS.dll`（设备注册）、`HCISUPAlarm.dll`（报警接收）、
`libeay32.dll` / `ssleay32.dll`（OpenSSL 1.0.x，ISUP 强依赖）等。

> 必须用 **64 位 Python**，SDK 只有 Win64 库。

### 2. 改配置

编辑 `config.json` 的 `isup` 段：

```json
"isup": {
  "listen_ip": "0.0.0.0",
  "register_port": 7660,
  "alarm_port": 7661,
  "protocol": "tcp",
  "access_security": 0,
  "keep_alive_sec": 30,
  "timeout_count": 3
}
```

- `register_port`：设备注册端口
- `alarm_port`：报警/图片接收端口（必须和注册端口不同）
- `protocol`：`tcp` / `udp` / `mqtt`（ISUP5.0 用 mqtt）
- `access_security`：`0`-兼容（先用这个）`1`-仅4.0以下 `2`-仅4.0以上

### 3. 装依赖并启动

用 uv：

```powershell
uv sync
uv run python main.py
```

或用 pip：

```powershell
python -m pip install -r requirements.txt
python main.py
```

只调 API 不连设备（联调前端时用）：

```powershell
uv run python main.py --api-only
```

> **遇到 `No module named pip`**：这个 venv 建的时候没带 pip，先补上：
> ```powershell
> <venv>\Scripts\python.exe -m ensurepip --upgrade
> ```
> 还不行就重建：
> ```powershell
> python -m venv --upgrade-deps <venv路径>
> ```

### 4. 设备侧配置

在盒子的 Web 界面找 **ISUP / EHome / 平台接入** 配置，填：

| 设备侧字段 | 填什么 |
|-----------|--------|
| 平台地址 / 服务器IP | **部署本后端的服务器 IP**（不是 127.0.0.1） |
| 端口 | `register_port`，默认 **7660** |
| 协议 | TCP（若设备是 ISUP 5.0 则选 MQTT，并改 config 的 `protocol`） |
| 设备ID | 自定义，如 `PPE-BOX-001`，两端约定一致 |
| 密钥 | 自定义，两端一致 |

设备侧保存后**设备会主动连过来**，后台会打印：

```
[isup] ✓ 设备上线: id=PPE-BOX-001 sn=xxx ip=192.168.1.64 ver=4.0
```

## 现场自检工具

第一次联调强烈建议先跑自检，它会逐项告诉你卡在哪：

```powershell
python tools/doctor.py                # 环境自检 + 开监听等设备上线（默认120秒）
python tools/doctor.py --wait 300     # 多等一会儿
python tools/doctor.py --check-only   # 只做本地环境自检，不开端口
```

自检依次检查：Python 位数 → 运行库 → SDK 初始化 → 端口绑定 → 设备上线 → 收报警。
没连上时会直接给出排查清单（IP、端口、防火墙、协议版本、密钥）。

产物在 `isup_doctor_out/`，里面有 `doctor_report.json`。

## 报警与图片是怎么进来的

### 报警类型

设备上报的 `dwAlarmType` 对应 `HCISUPAlarm.h` 里的宏：

| 值 | 宏 | 含义 |
|----|-----|------|
| `13` | `EHOME_ISAPI_ALARM` | **ISAPI报警上传 ← 智能分析/防护服告警走这个** |
| `1` | `EHOME_ALARM` | Ehome 基本报警 |
| `3` | `EHOME_ALARM_FACESNAP_REPORT` | 人脸抓拍报告 |
| `5` | `EHOME_ALARM_CID_REPORT` | 报警主机 CID 告警 |
| `6` | `EHOME_ALARM_NOTICE_PICURL` | 图片 URL 上报 |
| `11` | `EHOME_ALARM_ACS` | 门禁事件 |

非 `13` 的类型不会丢，会按原始内容落库（`event_type` 为 `isup_<类型名>`），方便后续补解析。

### 图片在哪（比 NET SDK 简单）

`EHOME_ISAPI_ALARM` 的 `pAlarmInfo` 指向 `NET_EHOME_ALARM_ISAPI_INFO`：

```c
typedef struct {
    char*   pAlarmData;        // 报警数据（JSON 或 XML）
    DWORD   dwAlarmDataLen;
    BYTE    byDataType;        // 1-xml 2-json
    BYTE    byPicturesNumber;  // 图片数量
    void*   pPicPackData;      // byPicturesNumber 个 NET_EHOME_ALARM_ISAPI_PICDATA
} NET_EHOME_ALARM_ISAPI_INFO;

typedef struct {
    DWORD   dwPicLen;          // 图片长度
    char    szFilename[256];
    BYTE*   pPicData;          // 图片数据指针 ← 真实指针，直接读就行
} NET_EHOME_ALARM_ISAPI_PICDATA;
```

对比一下：老 NET SDK 的 `0x4023` 事件**没有真指针**，得按 `sizeof(结构体)` 在连续内存里
算偏移才能抠出图片；ISUP 这里是正常指针，`string_at(pPicData, dwPicLen)` 就是 JPEG。

> ISUP 4.0 若配置成「报警与图片不分离」，`NET_EHOME_ALARM_MSG.pHttpUrl` 会带回一个图片 URL，
> 此时不下载图片，只把 URL 记进 `event_detail.url`（需要的话可自行加下载逻辑）。

### AI 算法结果（AIOP）

设备下发的 JSON 就是 AI 开放平台的 AIOP 格式，会被解析进 `analysis` 字段：

```json
{
  "width": "704", "height": "576",
  "targets": [
    { "obj": { "id": 1, "type": 0, "confidence": 940, "valid": 1, "visible": 1,
               "rect": { "x": "0.217", "y": "0.588", "w": "0.149", "h": "0.409" } } }
  ]
}
```

> `obj.type` 是**算法自定义的整数类别号**，含义由设备上的模型包决定。
> 用 `config.json` 的 `aiop_type_labels` 映射成中文，否则 `event_type` 会显示成 `aiop_type_N`。

## ⚠ 回调里不能干重活（和 NET 版最大的实现差别）

ISUP SDK 头文件原文警告：

> 「严禁在报警回调函数中调用 HCISUPSDK 外部接口，否则可导致程序崩溃或堵死。」
> 「应避免执行耗时操作……耗时时间不宜超过 10ms。」

所以**不能**像老代码那样在回调里直接写图片文件、写 SQLite、发 WebSocket。
本项目的做法：

```
报警回调  →  只做「memcpy 字节 + 放队列」→ 立即返回（微秒级）
worker线程 →  存图片 → 解析JSON → 入库 → WebSocket 推送
```

`core/alarm_service.py` 的 `_on_alarm_msg()` 走的就是这条路；
单测里有一条专门断言**回调耗时 < 10ms**（`test_callback_is_fast_and_defers_work`）。

队列上限 2000 条，满了丢最旧并计数（`/api/status` 里的 `dropped_alarms`）。

## API 接口

启动后访问：

- **监控页面**：`http://localhost:8080/`
- **Swagger 文档**：`http://localhost:8080/docs`
- **WebSocket 实时推送**：`ws://localhost:8080/ws/alarms`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/status` | ISUP 监听状态 + 在线设备列表 |
| GET | `/api/devices` | 当前注册上来的设备 |
| GET | `/api/alarms` | 告警列表 |
| GET | `/api/alarms?ppe_only=true` | 仅防护服相关 |
| GET | `/api/alarms?channel_no=3&start_time=2026-09-01T00:00:00` | 按通道/时间过滤 |
| GET | `/api/alarms/{id}` | 单条详情 |
| GET | `/api/stats` | 统计 |
| GET | `/api/pictures/{filename}` | 告警图片（JPEG） |
| GET | `/api/aiop-json/{filename}` | 该次告警的原始 JSON |
| WS | `/ws/alarms` | 新告警实时推送 |
| POST | `/api/hikvision/event` | ISAPI HTTP 推送备用入口（设备支持 HTTP 推送时可用） |

### 给甲方 IT 的对接说明

一次告警的返回示例（`GET /api/alarms?ppe_only=true`）：

```json
[
  {
    "id": 12,
    "event_time": "2026-09-11T16:20:16",
    "device_ip": "192.168.1.64",
    "device_serial": "PPE-BOX-001",
    "channel_no": 3,
    "event_type": "未穿反光衣",
    "confidence": 940,
    "target_count": 1,
    "is_ppe_related": true,
    "picture_urls": ["/api/pictures/isup_ch0_20260911_162016_250123.jpg"],
    "analysis": {
      "targets": [
        { "rect": {"x": 0.217, "y": 0.588, "w": 0.149, "h": 0.409}, "confidence": 940 }
      ]
    }
  }
]
```

- `picture_urls` 是相对路径，拼上 `http://服务器IP:8080` 即可下载图片
- `analysis.targets[].rect` 是 0~1 相对坐标，画框时乘以图片宽高
- `confidence` 取值 0~1000
- 告警图片以文件存在 `data/pictures/`，数据库只存路径

## 内网部署要求

```
公司内网
├── 算力盒子 / AI摄像头    由盒子管理
└── 后端服务器            192.168.1.100  (固定 IP，设备要连它)
```

防火墙放行（**入站**）：

- `7660`：设备注册端口
- `7661`：报警/图片接收端口
- `8080`：REST API（给甲方 IT 访问）

## 单元测试

```powershell
uv run python -m unittest discover -s tests -t . -v
# 或
uv run python -m unittest tests.test_alarm_flow -v
```

`tests/test_alarm_flow.py` **不连设备**：它按 SDK 的内存布局手工拼出
`[MSG][ISAPI_INFO][JSON][PICDATA[]][JPEG]` 缓冲区，再走真实回调入口，验证：

- 结构体偏移（`sizeof(NET_EHOME_ALARM_MSG)=72` 等）没算错
- 图片能按字节原样抠出来并存盘（2 张图逐个比对字节）
- AIOP JSON 解析出 targets / rect / confidence
- 设备上线事件能记录设备ID、序列号、协议版本
- 非 ISAPI 类型报警不丢
- **回调耗时 < 10ms**

## 本地测试（不用设备）

不想等设备也能验证软件链路：

```powershell
# 终端1：起一个和正式服务一样的环境，多一个 /simulate 注入接口
uv run python tools/simulate_alarm.py --start

# 终端2：灌假报警
uv run python tools/simulate_alarm.py --count 3 --type vest
uv run python tools/simulate_alarm.py --type helmet
uv run python tools/simulate_alarm.py --type both --no-picture
```

它走的是和真实回调**同一个入口**（`_on_alarm_msg`），所以链路等价，
可以验证「入队 → 存图 → 解析 → 入库 → 接口返回」整条链路。

## 项目结构

见 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) —— 每个文件负责什么、想改东西该动哪个文件。

## 常见问题

**Q: 启动报 `lib_isup 目录缺少 ...`？**  
`python setup_libs.py`。若 SDK 不在默认位置，用 `--sdk-root` 指定。

**Q: 启动报 `必须用 64 位 Python`？**  
ISUP SDK 只有 Win64 库，换成 64 位 Python。

**Q: 设备连不上来（`/api/devices` 一直空）？**  
按 `tools/doctor.py` 给的清单排查，最常见的三个：
1. 设备侧平台地址填了 `127.0.0.1` 或内网别的机器，要填**服务器真实 IP**
2. 服务器防火墙没放行 7660/7661
3. 协议版本不匹配：设备是 ISUP 5.0 时把 `isup.protocol` 改成 `mqtt`

**Q: 日志出现 EHOMEKEY 校验失败？**  
设备侧密钥和平台侧约定不一致；或 `access_security` 设得太严，先改成 `0` 兼容模式试。

**Q: 设备在线但收不到报警？**  
确认盒子上 AI 规则已启用并勾选「上传中心/报警上传」。
若库里有 `isup_*` 类型的记录但 `is_ppe_related` 为 0，说明报警进来了但没识别成防护服，
看 `event_detail.alarm_type_label` 确认走的哪个类型，再把关键词加进 `event_filter_keywords`。

**Q: 收不到图片？**  
看 `event_detail.picture_notes`：
- 空 且 `pictures_number` 为 0 → 设备没带图，检查设备侧抓图/上传设置
- 出现「设备返回图片URL」→ 设备配置成 URL 模式，需要另加下载逻辑

**Q: 想临时不连设备只调接口？**  
`python main.py --api-only`。
