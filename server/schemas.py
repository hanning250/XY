# -*- coding: utf-8 -*-
"""Pydantic 请求/响应模型（API Schema 层）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


# --------------------------------------------------------------------------
# 统一响应包装（开放 API 对外契约，见 docs §8.2）
# --------------------------------------------------------------------------
class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    request_id: str | None = None
    data: T | None = None


class PageMeta(BaseModel):
    next_cursor: str | None = None
    has_more: bool = False
    total: int | None = None


class PagedData(BaseModel, Generic[T]):
    items: list[T] = Field(default_factory=list)
    next_cursor: str | None = None
    has_more: bool = False
    # ★ 总条数（offset 分页时有值）。前端「共 N 条」用它 ——
    #   原先前端按页码估算，翻页时数字会跳，看起来像 bug。
    total: int | None = None


# --------------------------------------------------------------------------
# 图片
# --------------------------------------------------------------------------
class ImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_hash: str
    seq: int
    width: int | None = None
    height: int | None = None
    file_size: int | None = None
    linked_by: str | None = None
    # 相对路径，前端可直接用
    url: str
    # 绝对 URL，给甲方 IT 部门用
    absolute_url: str
    # 缩略图 URL
    thumbnail_url: str
    created_at: datetime | None = None


# --------------------------------------------------------------------------
# 视频
# --------------------------------------------------------------------------
class VideoOut(BaseModel):
    """★ 默认 status=not_requested，url 为 null —— 对应「不点就不加载」。"""

    status: str
    url: str | None = None
    duration: int | None = None
    provider: str | None = None
    # ★ 抓取失败原因（status=failed 时有值）：前端要显示「为什么没拿到视频」
    error: str | None = None


class VideoSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    alarm_id: str
    status: str
    url: str | None = None
    error: str | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None


class CreateVideoSessionIn(BaseModel):
    """创建视频会话的请求体。默认按告警时间点前后取一段。"""

    pre_seconds: int = Field(default=10, ge=0, le=600, description="告警时间点前取多少秒")
    post_seconds: int = Field(default=30, ge=1, le=3600, description="告警时间点后取多少秒")
    force_refresh: bool = Field(default=False, description="忽略缓存，强制重新生成")


# --------------------------------------------------------------------------
# 告警
# --------------------------------------------------------------------------
class AlarmOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    device_id: str
    channel: int
    alarm_type: int
    alarm_time: datetime
    status: str

    content: dict[str, Any] | None = None
    images: list[ImageOut] = Field(default_factory=list)
    video: VideoOut

    created_at: datetime | None = None
    # ★ 业务类型文本（AIOP 告警会是「未穿防护服报警」这类规则名）
    type_text: str = ""
    summary: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)
    # ★ 媒体文件是否已被清理策略删除（前端据此显示占位而不是裂图）
    media_expired: bool = False
    media_expired_at: datetime | None = None
    # ★ 人工处置状态
    handled: bool = False
    handled_at: datetime | None = None


class AlarmBrief(BaseModel):
    """列表用的精简结构，不带完整 content。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    device_id: str
    channel: int
    alarm_type: int
    alarm_time: datetime
    status: str
    # ★ 归属车间（多车间场景下列表要能一眼看出是哪条产线的报警）
    workshop: str | None = None
    workshop_name: str | None = None
    image_count: int = 0
    thumbnail_url: str | None = None
    video: VideoOut
    # ★ 业务类型文本与摘要
    type_text: str = ""
    summary: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)
    # ★ 媒体文件是否已被清理策略删除
    media_expired: bool = False
    media_expired_at: datetime | None = None
    # ★ 人工处置状态：默认未处理
    handled: bool = False
    handled_at: datetime | None = None


# --------------------------------------------------------------------------
# 设备
# --------------------------------------------------------------------------
class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    device_id: str
    ip: str | None = None
    port: int | None = None
    online: bool
    last_seen: datetime | None = None


class ChannelDeviceInfo(BaseModel):
    """★ 通道（摄像头）信息 —— 设备管理页展示用。

    一台 NVR 设备下有多路通道，每路通道可独立绑定车间；
    车间子账号看到的「设备在线状态」实际就是这些通道。
    """

    id: int
    display_name: str | None = None
    channel_name: str | None = None
    # ★ 2026-10-26：真实通道号（1/2/3…）。
    #   NVR 上多个通道可能同名（实测 ch3/ch4/ch5 都叫 "Camera 01"），
    #   只显示 channel_name 会让运维以为"同一摄像头重复列出"。
    #   前端用 CH{n} 展示，唯一可辨。
    channel_no: int | None = None
    workshop_code: str | None = None
    status: str = "unassigned"
    enabled: bool = True
    # ★ None = 无法判定（父设备在 device 表里查不到，多为历史残留记录），
    #   前端显示「未知」而不是「离线」—— 谎报离线会让运维白排查。
    online: bool | None = False
    # ★ 父设备 ID 与「是否查无此设备」（排查用）
    parent_device: str | None = None
    parent_missing: bool = False
    alarm_count: int = 0
    last_seen: datetime | None = None
    last_alarm_at: datetime | None = None

    # ★★ 2026-10-26 新增：摄像头自己的信息
    #
    # 为什么必须有这些字段：通道在线状态不能只抄父设备（NVR）——
    # NVR 在线时它下面 5 个通道里可能只有 1 个真接了摄像头。
    # 这些值来自 NVR 的 ISAPI /InputProxy/channels/<id>。
    #
    # ⚠️ 踩过的坑：后端 crud 里已经算好了这些值，但**响应模型漏声明**
    #    会被 FastAPI 静默丢弃，前端永远拿不到 —— 表现为「改了没效果」。
    camera_ip: str | None = None
    camera_model: str | None = None
    camera_serial: str | None = None
    # true = 查到了摄像头真实状态；false = 查询失败，online 退回父设备状态
    camera_online_known: bool = False


class ChannelRenameIn(BaseModel):
    """★ 通道改名（设备管理页给摄像头起可读名字）。"""

    display_name: str = Field(min_length=1, max_length=128)


# --------------------------------------------------------------------------
# 鉴权（登录注册 + 车间权限）
# --------------------------------------------------------------------------
class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PrincipalOut(BaseModel):
    """当前调用者身份，便于前端/联调时确认鉴权是否生效。"""

    kind: str
    subject: str
    scopes: list[str]
    # ★ 可访问的车间列表
    workshops: list[str] = Field(default_factory=list)
    # ★ 是否跨车间账号（admin）
    superuser: bool = False


# --------------------------------------------------------------------------
# ★ 车间 / 通道管理
# --------------------------------------------------------------------------
class WorkshopOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    description: str | None = None
    sort_order: int = 0
    enabled: bool = True


class WorkshopIn(BaseModel):
    code: str
    name: str
    description: str | None = None
    sort_order: int = 0


class ChannelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    child_dev_id: str | None = None
    task_id: str | None = None
    channel_id: int | None = None
    channel_name: str | None = None
    # ★ 真实通道号（与 channel_id 同值，单独给出便于前端统一用 channel_no）
    channel_no: int | None = None
    workshop_code: str | None = None
    display_name: str | None = None
    status: str = "unassigned"
    enabled: bool = True
    alarm_count: int = 0

    # ---- ★ 在线状态（2026-XX 修复）----
    # ⚠️ 原来 ChannelOut **没有这两个字段**，前端 row.online 恒为 undefined
    #    → 设备管理页所有通道永远显示「离线」（与报警数据矛盾）。
    #    管理接口（/api/admin/channels）与设备接口（/api/devices/channels）
    #    现在用同一套在线判定口径。
    #    online=None 表示无法判定（父设备在 device 表里查不到）。
    online: bool | None = None
    parent_device: str | None = None
    parent_missing: bool = False
    last_seen: datetime | None = None

    # ---- ★ 辅助「认出这是哪个车间」的信息 ----
    # 只靠 childDevID 这类哈希串，人无法判断通道属于哪个车间。
    # 下面这些字段让运维能通过「看画面」来确认。
    last_alarm_at: datetime | None = Field(
        None, description="该通道最近一次告警时间；None 表示还没收到过数据"
    )
    last_alarm_count: int = Field(
        0, description="该通道在库中的告警总数（判断通道是否活跃）"
    )
    sample_image_url: str | None = Field(
        None, description="最近一张告警图 URL（★ 看画面认车间）。可能为 null"
    )
    sample_image_count: int = Field(0, description="可用的样本图片数量")

    # ---- ★★ 2026-10-26：摄像头自己的信息 ----
    # 来自 NVR 的 ISAPI /ISAPI/ContentMgmt/InputProxy/channels/<id>。
    # 通道在线状态不能只抄父设备（NVR）：NVR 在线时它下面 5 个通道里
    # 可能只有 1 个真接了摄像头。
    # ⚠️ 后端算好了但模型漏声明会被 FastAPI 静默丢弃，前端永远拿不到。
    camera_ip: str | None = None
    camera_model: str | None = None
    camera_serial: str | None = None
    camera_online_known: bool = False


class ChannelSampleOut(BaseModel):
    """通道的样本图片（用于识别该通道属于哪个车间）。"""

    url: str
    alarm_time: str | None = None
    type_text: str = ""


class ChannelAssignIn(BaseModel):
    """把通道指派给车间。workshop_code 留空 = 取消指派。"""

    workshop_code: str | None = None
    display_name: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str | None = None
    role: str = "viewer"
    is_superuser: bool = False
    enabled: bool = True
    workshops: list[str] = Field(default_factory=list)


class UserCreateIn(BaseModel):
    username: str
    # ★ 最少 6 位（2026-XX 安全审查：与管理员改密/自助改密口径统一）
    password: str = Field(min_length=6)
    display_name: str | None = None
    role: str = "viewer"
    superuser: bool = False
    workshops: list[str] = Field(default_factory=list)


class UserUpdateIn(BaseModel):
    """★ 账号编辑（管理员用）。所有字段可选，只更新传入的字段。"""

    display_name: str | None = None
    # 传入即重置密码，同样要求最少 6 位
    password: str | None = Field(default=None, min_length=6)
    enabled: bool | None = None
    superuser: bool | None = None
    workshops: list[str] | None = None


class PasswordChangeIn(BaseModel):
    """★ 修改自己的密码（任何登录用户）。"""

    old_password: str = Field(description="旧密码（校验通过才能改）")
    new_password: str = Field(min_length=6, description="新密码（至少 6 位）")


class PasswordResetIn(BaseModel):
    """★ 管理员重置密码（2026-XX 安全审查：从 URL query 改为请求体，
    避免明文密码进访问日志/代理日志）。"""

    password: str = Field(min_length=6, description="新密码（至少 6 位）")


# --------------------------------------------------------------------------
# ★ 媒体清理（按指定时段删除）
# --------------------------------------------------------------------------
class MediaCleanupIn(BaseModel):
    """按时间区间删除媒体文件的请求体。

    ★ 只删文件，数据库记录保留并标记为 media_expired —— 前端详情页显示占位，
      不会出现裂图，历史告警仍可检索。
    """

    start: datetime = Field(description="起始时间（含），按文件修改时间比对")
    end: datetime = Field(description="结束时间（含）")
    categories: list[str] = Field(
        default_factory=list,
        description=(
            "要清理的目录子集，可选 storage / outputFiles / media-video / IsupSDKLog；"
            "留空表示全部"
        ),
    )
    dry_run: bool = Field(
        default=True,
        description="★ 默认只预演不真删，确认无误后再传 false 执行",
    )


class MediaCleanupOut(BaseModel):
    """媒体清理结果。

    ## ★ 2026-10-27 字段语义澄清

    `dry_run=true` 时，下面的数字是「**会**删多少」，不是「已删」。
    但字段名叫 `deleted` / `bytes_freed` 容易误读成"已完成"。

    所以 dry_run 时同时返回语义明确的别名：
        would_delete / would_keep / would_free_bytes
    并给出 action_taken 标识本次到底动了没有。
    """

    # ---- 原字段（保留兼容）----
    deleted: int = 0
    kept: int = 0
    bytes_freed: int = 0
    dry_run: bool = True
    alarms_marked: int = 0
    errors: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)

    # ---- ★ 语义明确的别名（2026-10-27）----
    would_delete: int = Field(
        0, description="dry_run 时会删除的文件数（真实模式等于 deleted）"
    )
    would_keep: int = Field(
        0, description="dry_run 时会保留的文件数（真实模式等于 kept）"
    )
    would_free_bytes: int = Field(
        0, description="dry_run 时会释放的字节数（真实模式等于 bytes_freed）"
    )
    action_taken: str = Field(
        "preview",
        description='本次实际动作："preview"（未删）或 "deleted"（已删）',
    )


# --------------------------------------------------------------------------
# ★ 批量删除告警
# --------------------------------------------------------------------------
class BatchDeleteIn(BaseModel):
    ids: list[str] = Field(default_factory=list, description="要删除的告警 id 列表")


class BatchDeleteOut(BaseModel):
    deleted_ids: list[str] = Field(default_factory=list)
    files_removed: int = 0


# --------------------------------------------------------------------------
# ★ 看板统计（前端顶部三张卡片）
# --------------------------------------------------------------------------
class AlarmStatsOut(BaseModel):
    today: int = Field(0, description="今日报警总数")
    pending: int = Field(0, description="待处理（未处理的全部，不限今日）")
    handled: int = Field(0, description="已处理")


class HandleIn(BaseModel):
    """标记处理 / 取消处理。"""

    handled: bool = Field(True, description="true=标记已处理，false=取消处理")


class BatchHandledIn(BaseModel):
    """★ 批量标记处理。"""

    ids: list[str] = Field(default_factory=list, description="告警 id 列表")
    handled: bool = Field(True, description="true=标记已处理，false=取消处理")


# --------------------------------------------------------------------------
# ★ 首页看板 / 每日趋势
# --------------------------------------------------------------------------
class TrendPoint(BaseModel):
    date: str = Field(description="YYYY-MM-DD")
    count: int = 0
    handled: int = 0


class DashboardOut(BaseModel):
    """★ 首页看板聚合数据。

    · today / yesterday：卡片与「较昨日」对比
    · trend：按天统计（含已处理数），前端画条形图
    · devices_online / devices_total：在线状态（已按车间隔离）
    · workshops：★ 各车间的今日/待处理分布（多车间场景），已按可见范围过滤

    ★ 2026-10-26：本系统定位是**纯展示看板**，不承担"谁处理了"的流程职责。
      因此新增下面这组客观业务指标（事件数 / 违规人次 / 热点工位 / 数据完整率），
      原 handled 系列字段保留兼容（外部开放 API 仍在用），前端不再展示。
    """

    today: int = 0
    yesterday: int = 0
    pending: int = 0
    handled: int = 0
    devices_online: int = 0
    devices_total: int = 0
    trend: list[TrendPoint] = Field(default_factory=list)
    workshops: list["WorkshopStat"] = Field(default_factory=list)
    # ★ 今日 24 小时分布（哪班次在报警）
    hourly: list["HourlyPoint"] = Field(default_factory=list)
    # ★ 今日已处理告警的平均处置时长（分钟）
    avg_handle_minutes: float | None = None
    handled_today: int = 0
    # ★ 图片配对队列健康度（pending=待配对，orphan=孤儿，matched=已配对）
    pending_images: int = 0
    orphan_images: int = 0
    # ★ 未指派车间的告警数（提醒管理员去分配通道）
    unassigned: int = 0

    # ---------- ★ 事件口径（看板主指标）----------
    # 今日归并后的「违规事件数」（同一工位窗口内多次推送算一次）
    events_today: int = 0
    # 今日原始推送条数（对比 events_today 可以看出设备刷屏程度）
    records_today: int = 0
    # 冗余倍数 records/events，>10 说明设备在刷屏，指标需要谨慎解读
    repeat_ratio: float = 0.0
    # 事件归并窗口（秒），前端在提示里说明口径
    event_window_seconds: int = 120
    # 今日涉及违规人次（按事件去重后，事件内取人数峰值再求和）
    people_today: int = 0
    # 今日含违规的事件数（alarmed > 0）
    abnormal_events_today: int = 0
    # ★ 违规热点工位（按通道的事件数排行）
    hotspots: list["HotspotPoint"] = Field(default_factory=list)
    # ★ 数据完整率
    data_quality: "DataQualityOut | None" = None


class HotspotPoint(BaseModel):
    """★ 违规热点：某台相机的违规事件排行。"""

    device_id: str = ""
    channel: int = 0
    channel_name: str = ""
    workshop: str = ""
    events: int = 0
    records: int = 0
    share: float = 0.0
    last_at: str | None = None


class DataQualityOut(BaseModel):
    """★ 数据可信度：有图率决定了业务指标能不能被采信。"""

    total: int = 0
    with_image: int = 0
    without_image: int = 0
    with_image_pct: float = 0.0
    unassigned: int = 0


class HourlyPoint(BaseModel):
    """今日某小时的报警数。"""

    hour: int
    count: int = 0


class WorkshopStat(BaseModel):
    """单条车间的报警统计（看板用）。"""

    code: str
    name: str
    today: int = 0
    pending: int = 0
    # ★ 车间下挂的通道数与在线数（判断「没数据」是没报警还是设备掉线）
    channels: int = 0
    channels_online: int = 0
