# -*- coding: utf-8 -*-
"""全局配置。告警图片归档、SQLite 等走环境变量 / server/.env。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# server/config.py -> server/ -> 项目根
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 告警图片归档根目录。按日期分层。
STORAGE_DIR = PROJECT_ROOT / "storage"
# 同事的解码服务产出的视频，我方托管目录（VideoProvider=file 时使用）
MEDIA_VIDEO_DIR = PROJECT_ROOT / "media" / "video"
# ffmpeg HLS 输出目录（VideoProvider=hls 时使用）
MEDIA_HLS_DIR = PROJECT_ROOT / "media" / "hls"


class Settings(BaseSettings):
    """服务自身配置。可用环境变量或 server/.env 覆盖。"""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / "server" / ".env"),
        env_prefix="ISUP_",
        extra="ignore",
    )

    # ---- 服务 ----
    app_name: str = "ISUP 告警平台"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8088

    # ---- 数据库 ----
    # 默认放在项目根的 data/ 下
    database_url: str = f"sqlite+aiosqlite:///{(PROJECT_ROOT / 'data' / 'alarm.db').as_posix()}"

    # ★ 连接池（2026-09-30 修复并发打爆问题）
    #
    # 背景：SQLAlchemy 默认 pool_size=5 / max_overflow=10（共 15）。
    #   而**一个请求要占 2 个连接**（审计中间件 1 个 + 路由依赖 1 个），
    #   甲方多车间并发拉取时直接打爆：
    #       QueuePool limit of size 5 overflow 10 reached
    #   实测 20 并发 → 100% 失败。
    #
    # SQLite 是本地文件，连接很廉价，所以池子可以放大。
    # 若要支持更多并发，调大这三个值即可。
    db_pool_size: int = 20
    db_max_overflow: int = 40
    db_pool_timeout: int = 60

    # ---- 鉴权 ----
    # jwt    : 登录页 + JWT（默认）
    # apikey : 内部 API 也要求 X-API-Key
    # （anonymous 已移除；开放 API 一律要求 X-API-Key）
    auth_mode: str = "jwt"

    # JWT
    jwt_secret: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1576800  # 默认 3 年（3×365×24×60）

    # ★ 启动时确保存在的管理员（auth_mode=jwt 时生效）
    #   账号不存在 → 创建；已存在且配置了密码 → 按环境变量同步密码（便于本机部署）。
    admin_username: str = "admin"
    admin_password: str = ""

    # ---- ★ 告警聚合（见 docs §3）----
    # 收到告警后，等待图片到达的窗口（秒）。
    #
    # ⚠️ 2026-09-17 变更：默认改为 **0（关闭聚合窗口）**。
    #    原因：已通过设备黑名单屏蔽了每秒刷屏的海康 IO 告警，
    #          真正的告警（box001 的未穿防护服）**每条都独立成条**即可，
    #          不再需要靠时间窗把多条合并。
    #    图片的关联改为「就近匹配 + 队列回填」，不依赖这个窗口。
    #    设为 >0 可恢复原有的窗口聚合行为。
    correlate_window_seconds: float = 0.0

    # 图片就近匹配的容差（秒）。图片可能比告警早到或晚到，用它匹配。
    #
    # ⚠️ 注意：这个容差**只影响「能否找到该告警」**，不再决定能收几张图。
    #    一条告警只保留一张「报警图」（与同事实现对齐），
    #    详见 correlator.on_storage_image 的说明。
    image_match_tolerance_seconds: float = 120.0

    # 聚合窗口巡检间隔（秒）
    correlate_sweep_interval: float = 1.0

    # ---- ★ 告警去重 ----
    # ⚠️ 2026-09-20 变更：默认改为 **0（关闭去重）**，与同事实现对齐。
    #    同事（src/Backend）的做法是「每条 SDK 回调都入库 + 都广播」，不做任何合并。
    #    实测 box001 的 AIOP_Polling_Snap 是**轮询抓拍**模式：只要画面里还有人
    #    未穿防护服，设备就每 6 秒重复上报一次。开启去重会把后续上报静默吞掉
    #    （前端收不到任何推送），与同事的行为不一致。
    #
    #    设为 > 0 可恢复合并行为（累加 repeatCount，不重复推送）。
    dedup_window_seconds: float = 0.0

    # ---- ★ 告警过滤（按设备/事件类型屏蔽噪音）----
    # 逗号分隔。实测 HaiKang-1 的 IO 告警无业务含义且每秒重复，会淹没真告警，
    # 且它不上传图片（图片由 box001 上传），因此建议屏蔽。
    # 例：ISUP_IGNORE_DEVICES=HaiKang-1
    ignore_devices: str = ""
    # 例：ISUP_IGNORE_EVENT_TYPES=IO
    ignore_event_types: str = ""
    # 白名单：非空时**只接受**这些设备的告警（优先级高于黑名单）
    # 例：ISUP_ALLOW_DEVICES=box001
    allow_devices: str = ""

    # ---- 图片归档 ----
    # 图片是否按 yyyy/mm/dd 分层存放（原实现是 storage/ 平铺，文件多后会卡）
    storage_date_partition: bool = True

    # ---- ★ 媒体保留策略 ----
    # ★★ 2026-10-29：图片与视频**分开配置**（甲方要求）
    #
    #   甲方口径：
    #     · 报警视频：按套餐 3 / 7 / 30 天（影响磁盘，是关键成本项）
    #     · 报警记录 + 图片：统一 30 天（体积小，多留没压力）
    #
    #   为什么必须分开：
    #     视频单段 84 MB，30 天要 10 TB 级磁盘；图片一张 51 KB，
    #     3 路 × 4950 条/天 × 30 天 ≈ 7.5 GB，连零头都算不上。
    #     如果两者共用一个保留期，缩短视频保留期会把图片一起删掉 ——
    #     但甲方要求「报警消息和图片都留 30 天」。
    #
    #   语义：
    #     video_retention_days  视频文件（media/video）保留天数
    #     image_retention_days  图片文件（storage）保留天数
    #     media_retention_days  ★兼容旧配置：两者都没显式设置时的统一回退值
    media_retention_days: int = 30
    video_retention_days: int = 0     # 0 = 跟随 media_retention_days
    image_retention_days: int = 0     # 0 = 跟随 media_retention_days
    # SDK 日志保留天数
    log_retention_days: int = 7

    # ---- ★ 告警记录保留策略 ----
    # ⚠️ 必须关注：box001 的 AIOP_Polling_Snap 是**轮询抓拍**模式，
    #    只要画面里还有违规目标，设备就每 6 秒重复上报一次。
    #    关闭去重后（dedup_window_seconds=0，与同事行为一致），
    #    告警记录会以约 600 条/小时、14400 条/天的速度增长。
    #
    #    这里按天数清理历史告警记录，防止数据库无限膨胀。
    #    0 = 不清理（保留全部）
    alarm_retention_days: int = 30
    # 清理时按 alarm_time 还是 created_at 判断（默认按告警时间）
    alarm_retention_by: str = "alarm_time"
    # 是否在服务启动时自动跑一次清理
    cleanup_on_startup: bool = True

    # ---- ★ 开放 API 增量同步（甲方每 10 分钟拉一次）----
    #
    # 甲方要求「每 10 分钟取一次，每次都要成功」。要成立必须解决两件事：
    #   ① 对方不能自己算时间窗 —— 时钟偏差会直接变成数据缺口；
    #   ② 窗口末尾的告警，视频还在异步转码，拉过去 video_url 是 null。
    #
    # 因此服务端提供：
    #   · 全钟点对齐的窗口（sync_window_minutes）
    #   · 只吐「已经过去 sync_grace_seconds 秒」的数据 —— 保证视频转码完成
    #   · sync_token 水位：下一轮原样传回，精确到 (时间, id)，同秒多条不漏不重
    sync_window_minutes: int = 10
    sync_grace_seconds: int = 60

    # ---- ★ 开放 API 限流 ----
    # 甲方「每次都要成功」的硬要求下，限流不能成为失败的来源。
    # 正常 10 分钟一轮远低于此；但**补拉积压**时一页 1000 条可能要连发几十个请求，
    # 原来 120/分钟 偏紧，撞上就是 429（对方看到的是"取数失败"）。
    # 这里放宽到 600/分钟，同时保留兜底（防内网失控程序刷挂服务）。
    # 0 = 不限流（不建议，除非前面有 nginx 做限流）
    open_api_rate_limit_per_min: int = 600
    # 自动清理巡检间隔（小时）。0 = 关闭定时清理
    cleanup_interval_hours: float = 24.0

    # ---- ★ 审计日志保留期（2026-XX 新增）----
    # api_audit_log 表原来没有任何清理策略，长期运行会无限膨胀。
    # 0 = 不清理（保留全部）
    audit_retention_days: int = 90

    # ---- ★ 软件授权（有效期 1 年）----
    # 客户现场**首次启动**即激活，到期日 = 激活日 + license_days。
    # 记录写在 data/license.json（打包脚本排除 data/，不受交付影响）。
    # 到期后全面停用：除登录/授权/健康检查，业务接口一律 403。
    license_days: int = 365
    # 到期是否拦截业务：关掉可临时解除拦截（排障/演示用）；正式交付保持 true
    license_enforce: bool = True
    # 授权码签名密钥。★ 交付前务必换成自己的密钥，否则谁都能算码
    license_secret: str = "isup-license-change-me"
    # 授权记录文件路径（留空 = <项目根>/data/license.json）
    license_file: str = ""

    # ---- ★ 界面缩放（2026-XX 新增：现场大屏适配）----
    # 现场是 1920×1080 壁挂大屏，实测整页 80% 刚好一屏看完（不用手动缩放浏览器）。
    # 前端启动时从 /api/auth/config 取这个值写进 <html style="zoom">，
    # 所以改这里 **不需要重新构建前端**，重启后端 + 刷新页面即可。
    # 取值范围 (0.5, 2]；填 1 表示不缩放。CSS 里另有 0.8 兜底（拿不到配置时生效）。
    ui_scale: float = 0.8

    # ---- ★ 事件归并窗口（秒）----
    # box001 是 AIOP 轮询抓拍模式，同一个人站在镜头前会每 3~4 秒推一条。
    # 实测 2026-10-22 一天 4202 条里，17 点这一小时就 4188 条，相邻间隔
    # 1 秒 2702 次、0 秒 1471 次 —— 是设备在"刷屏"，不是 4202 次违规。
    #
    # 看板因此按 (设备, 通道, 事件类型) 做时间窗归并：
    # 相邻两条间隔 <= 本值 → 视为同一次违规，合并成一个事件。
    #   120 秒：5826 条 → 121 事件（实测）
    #   60  秒：更严格，能把同一人反复进出也拆开
    # 调大 = 事件数变少（更"友好"）；调小 = 更接近原始次数。
    # ⚠️ 这个值只影响**看板统计口径**，不改数据库里的原始记录。
    event_merge_seconds: int = 120

    # ---- 视频 Provider ----
    # mock    : 返回内置样例视频，用于同事的解码服务未就绪时跑通前端
    # file    : 同事产出 MP4 文件，我方只托管 URL（★最理想）
    # http    : 同事提供 HTTP 接口，我方代理
    video_provider: str = "mock"
    # file / http provider 的基址（对外可访问的前缀）
    video_public_base: str = "http://127.0.0.1:8088/media/video"
    # 同事的解码服务地址（http provider 用）
    video_service_base: str = "http://127.0.0.1:9000"
    # 视频会话 TTL（秒），到期自动回收，防止句柄/文件泄漏
    video_session_ttl_seconds: int = 300

    # ---- ★ 告警视频片段（甲方要求：前后各 30 秒）----
    # 从设备录像抓取 [告警时刻 - pre, 告警时刻 + post] 这一段。
    # ⚠️ 旧实现是「告警前 1 分钟 → 告警时刻」，只有前段没有后段，
    #    不符合甲方"前后 30 秒"的要求。
    #
    # ⚠️ 注意：开启 video_merge_by_minute 时，下面两个参数**不再生效**——
    #    改为固定抓「该自然分钟」（00~60 秒）。
    # ★★ 2026-10-23 现场调整：前 20 秒 + 后 15 秒（共 35 秒）
    #
    #   原来 30+30（60 秒）。按 3 摄像头交付形态核算后压缩：
    #     单次抓取 = 延迟 + 码流 + 转码
    #     60 秒方案：30+60+15 = 105 秒 → 并发 3 只能 1.7 段/分，需求 3 → 不够
    #     35 秒方案：15+35+15 =  65 秒 → 并发 3 达 2.8 段/分，接近需求
    #   缩短后段还有个额外好处：**延迟也随之减半**（见下面的说明）。
    #
    #   ⚠️ 甲方原要求"前后各 30 秒"，这里已与其确认压缩。
    #      若要改回，把这两个值调回 30/30，并把下面的 delay 调回 30。
    # ★★★ 2026-10-26 定稿：前 30 秒 + 后 30 秒（甲方原始要求，容量已够）
    #
    #   ── 实测基准（2026-10-26，NVR 已改 H.264）──
    #     ISAPI 下载：40 秒录像 / 17.0 秒 = 2.35 倍速
    #     转码：H.264 → remux，0.8 秒（几乎不耗时）
    #     3 路并发：已实测支持（带重试 100% 成功）
    #
    #   ── 容量核算（单条 60 秒视频）──
    #     下载 60 ÷ 2.35 = 25.5 秒 + remux 0.8 = 26.3 秒
    #     3 路产能 = 6.8 段/分钟（需求 3）→ 余量 128%
    #     报警后 30(等后段) + 26.3 = 56 秒可查，满足 ≤60 秒
    #
    #   ── 密集时段（15 秒一条，合并后 105 秒视频）──
    #     单段 45.5 秒，3 路产能 4.0 段/分钟（需求 3）→ 余量 33%
    #     可查约 120 秒（超 60 秒，但信息科 10 分钟取一次，无影响）
    #
    #   ── 为什么密集时段超过 60 秒 ──
    #     合并需等到该分钟最后一条报警 + 30 秒，再下载 105 秒录像。
    #     这是「合并」与「快速可查」的固有矛盾；
    #     甲方要求「前后各 30 秒」优先，故接受密集时段慢一些。
    video_pre_seconds: int = 30
    video_post_seconds: int = 30

    # ---- ★★★ 2026-10-24 新增：ISAPI 录像下载（突破 SDK 回放限制）----
    #
    # 为什么加这个（现场实测，详见 services/isapi_client.py 的说明）：
    #
    #   SDK 回放（NET_ECMS_StartPlayBack）有两个硬限制：
    #     · **同一设备只支持 1 路**：实测 3 路并发时后开踢前开
    #       （lane0=1.1s/7%, lane1=0.4s/2%, lane2=16.0s/100%）
    #     · **1 倍速**：要 60 秒画面必须花 60 秒
    #
    #   ISAPI 的 /ISAPI/ContentMgmt/download 完全不同：
    #     · **支持并发**：实测 3 路同时下载同一段，3 路全成功，
    #       墙钟 3.4~3.8 秒（单路也是 3.7 秒 → 并发效率 1.0x）
    #     · **约 4.5 倍速**：15 秒录像（6.7 MB）3.7 秒下完 = 1788 KB/s
    #
    #   这让「3 台摄像头 + 1 台 NVR」从**缺口 3 倍**变成**余量 33%**。
    #
    # 开关与参数：
    video_use_isapi: bool = True
    # NVR 的 ISAPI 地址（必须是平台能直连的 IP，不是设备注册名）
    isapi_host: str = "192.168.1.64"
    isapi_port: int = 80
    isapi_username: str = "admin"
    isapi_password: str = ""
    # 同时下载几路。实测设备支持 3 路（偶发失败靠重试兜住）。
    isapi_max_concurrent: int = 3
    # 每段下载的超时秒数（含重试）
    isapi_download_timeout: float = 60.0
    # 单段最多允许下载多少秒的录像（防止误传超大区间把带宽打满）
    isapi_max_segment_seconds: int = 180
    # 拉 NVR 的 ISAPI 报警长连接（/ISAPI/Event/notification/alertStream）
    # 与 HCNetSDK 布防同时开会重复入库，默认关，作布防失败时的兜底
    isapi_alert_enable: bool = False
    # 告警归属的设备 ID（报文没有 deviceID 时用）。现场盒子常用 box001
    isapi_device_id: str = "box001"
    # HCNetSDK 设备网路 SDK：Login + SetupAlarmChan，收 COMM_ISAPI_ALARM
    hcnetsdk_enable: bool = True
    hcnetsdk_dir: str = str(PROJECT_ROOT / "lib" / "hcnetsdk")
    # 登录模式：0=私有协议 1=ISAPI（默认，收 COMM_ISAPI_ALARM）2=自适应
    hcnetsdk_login_mode: int = 1
    # 登录端口。ISAPI 模式请用 HTTP 口（通常与 isapi_port 一致=80）；
    # 8000 是私有协议口，ISAPI 登录会失败 err=9。
    hcnetsdk_port: int = 80

    # ★★ 抓取前**延迟**多少秒（等设备把后段录完）
    #
    #   问题：报警在 t 时刻产生，立即抓 [t-pre, t+post] 时，
    #         **t+post 那一刻的画面还没录出来**，设备只能返回 [t-pre, now]。
    #         实测视频时长普遍只有 26~30 秒（缺后段）。
    #
    #   解决：报警到达后先等 post 秒，让设备把后段录完整，再抓。
    #
    #   ★ 2026-10-23：默认值改为**跟随 post_seconds**（15 秒）。
    #     原来固定 30 是因为后段有 30 秒；后段缩到 15 后，
    #     只需等 15 秒，白赚 15 秒的吞吐（单次 105→65 秒）。
    #
    #   设为 0 退回「立即抓取」的旧行为（视频会比预期短）。
    #   设为负数表示「自动 = post_seconds」。
    video_capture_delay_seconds: float = -1.0  # -1 = 自动跟随 video_post_seconds

    # ---- ★★ 按自然分钟合并视频抓取（实现见 playback_service）----
    #
    # 开启后：同一个 (设备, 通道, 自然分钟) 内的报警共用一段视频，
    # 减少串行回放次数。设为 False 则每条报警单独抓取。
    video_merge_by_minute: bool = True

    # ★ 告警到达后**自动**抓取视频，无需人工点击。
    #
    #   为什么默认开启：甲方 IT 部门是**按天批量拉取**的，
    #   拉的时候视频必须已经生成好 —— 不能等他们点了才去抓。
    #
    #   ⚠️ 代价：每次抓取要连设备取流 + ffmpeg 转码（约 30 秒~3 分钟），
    #      且设备回放是独占资源（并发被限制为 1）。
    #      告警频繁时任务会排队，积压量可通过
    #      GET /api/admin/pending-stats 观察。
    #
    #   设为 False 则退回「按需点击」模式。
    video_auto_capture: bool = True
    # 自动抓取队列积压上限。超过后**停止自动抓取**（告警与图片仍照常），
    # 避免视频任务无限堆积把设备连接占死。
    video_auto_max_queue: int = 200

    # ---- 媒体 URL ----
    # 对外暴露的 API 基址，用于拼绝对 URL 给甲方 IT 部门
    public_base_url: str = "http://127.0.0.1:8088"

    # ---- ★ CORS（2026-XX 安全审查新增）----
    # 允许跨域访问的前端来源，逗号分隔。
    #   空（默认）→ **不注册** CORS 中间件：浏览器同源策略天然生效，
    #               内网里随便一个网页都无法跨域读取告警/图片。
    #   配了来源 → 只放行列出的 origin（开发期配 Vite 的 5173）。
    # ⚠️ 永远不要再配成 "*"：开放 API 不鉴权 + CORS 全开 =
    #   任何内网用户开一个网页就能把告警数据全部拉走。
    cors_origins: str = ""

    # ---- ★ 设备在线判定 ----
    # 兜底窗口（分钟）：online=1 但 last_seen 超过这个时长，按离线展示。
    #
    # ⚠️ ISUP 设备**没有周期心跳刷新 last_seen** —— 注册（上线）是一次性
    #    事件，之后 last_seen 就停在上线的时刻。所以这个值不能太小，
    #    否则长期在线的设备会被误判离线。
    #
    # ★★ 2026-10-26 调整：3 天 → 1 天。
    #   原因：现在有**主动探测**（见 services/online_probe.py），
    #   在线判定不再只靠这个标记值：
    #     ① device.ip 已知 → 探测端口层 / ISAPI，给明确结论
    #     ② 探测无法判定 → 才用 online 标记
    #     ③ last_seen 只防「进程被强杀导致离线事件彻底丢失」
    #   有了①之后，这个兜底窗口可以收紧到 1 天。
    device_offline_after_minutes: int = 60 * 24  # 1 天

    # ---- ★ 静默断线兜底（2026-XX 起语义收窄）----
    # ⚠️ 该配置**不再单独判离线**（口径见 crud/device.py 的注释）：
    #    本项目报警是「有人违规才产生」，两次报警间隔几小时很正常。
    #    按「30 分钟没数据就离线」会把安静的产线全判成离线
    #    （实测：某通道 33 分钟前刚报过警，仍被显示离线）。
    #    现在在线与否以主动探测 / SDK online 标记为准；本值只在
    #    「有 online 标记但缺 last_seen」时作为辅助判据。
    device_silence_after_minutes: int = 240

    # ---- ★★ 主动在线探测（2026-10-26 新增）----
    # 不依赖 SDK 标记，直接探设备是否活着。需要 device.ip 已知
    # （由 correlator.on_alarm 从报警报文的 ipAddress 自动补登记）。
    #
    # 探测顺序：平台侧 ISUP 长连接 → ISAPI HTTP 端口 → 都不可达判离线
    device_online_probe_enabled: bool = True
    # ISAPI 探测端口
    device_online_probe_port: int = 80
    # 单次探测超时（秒）
    device_online_probe_timeout: float = 1.5
    # 探测结果缓存（秒）：避免每次刷页面都探
    device_online_probe_cache_seconds: float = 20.0

    # ---- ★ 内部接口开关（交付配置，2026-09-30）----
    #
    # True  = 内部 /api/* 可用（前端登录看板、admin 管理接口、WebSocket 推送）
    # False = **完全不注册**内部接口（甲方拿到的东西只剩 /openapi/v1 的 9 个）
    #
    # 为什么默认 False：
    #   甲方明确「不需要前端，只要后端接口」。与其把内部接口藏起来
    #   （藏在文档里仍然可调用，只是多一层 401），不如交付时**根本不注册**，
    #   让"没有这回事"比"有但锁着"更干净。
    #
    # 关掉后我方管理操作不受影响：
    #   车间分配、账号管理等 CLI 脚本**直连数据库**，不走 HTTP。
    #   详见 docs/车间管理操作手册.md。
    #
    # ⚠️ 我们的看板前端（web/dist）依赖 /api/*，关掉后前端会显示
    #    「登录失效」并停在登录页 —— 交付机若要开前端，设回 True。
    enable_internal_api: bool = False
    # 交付时是否托管前端页面（/）。同样默认关闭 —— 甲方不要前端。
    enable_web_ui: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


# ---------------------------------------------------------------------------
# ★ 媒体保留天数解析（图片与视频分开）
#
#   优先级：专用项 > media_retention_days（兼容旧配置）
#   集中在这里，避免 cleanup / 接口 / 文档各写一份导致口径漂移。
# ---------------------------------------------------------------------------
def resolve_video_retention_days(s: "Settings | None" = None) -> int:
    """视频保留天数。video_retention_days=0 时回退 media_retention_days。"""
    s = s or get_settings()
    return int(s.video_retention_days or s.media_retention_days or 0)


def resolve_image_retention_days(s: "Settings | None" = None) -> int:
    """图片保留天数。image_retention_days=0 时回退 media_retention_days。"""
    s = s or get_settings()
    return int(s.image_retention_days or s.media_retention_days or 0)


def ensure_dirs() -> None:
    """确保运行期需要的目录都存在。"""
    for d in (
        STORAGE_DIR,
        MEDIA_VIDEO_DIR,
        MEDIA_HLS_DIR,
        PROJECT_ROOT / "data",
    ):
        d.mkdir(parents=True, exist_ok=True)
