# -*- coding: utf-8 -*-
"""数据库模型层。

对应 docs/技术选型与架构方案.md §7。

核心设计：
  · Alarm 是聚合根，一条告警 = 消息内容 + N 张图片 + 一段视频
  · video_status 默认 'not_requested' —— 对应「不点就不加载」的挂起设计，
    告警到达时零资源占用，用户点击才去拉起同事的解码服务
  · content_raw 完整留档原始报文（解析逻辑一定会变，丢了就找不回）
"""

from __future__ import annotations

import enum
from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """★ 统一时间基准：**本地时间（东八区）naive**。

    历史遗留问题（已修）：原来这里返回 UTC naive，而 alarm_time 存的是
    设备上报的本地时间，导致同一条记录两个字段**差 8 小时**。
    混用会造成：按时间过滤/统计错误、图片与告警配对时间差算错、
    对外 API 返回裸时间戳让对方误解。

    现在全库统一为「本地 naive」——现场就一个时区，存本地最直观。
    口径定义见 server/services/timeutil.py。

    函数名保留 utcnow 是为了不改动大量既有调用点（它现在是本地时间）。

    ★ 2026-10-21 分层修正：这里原本 `from server.services.timeutil import now_local`，
      造成 **model 层反向依赖 service 层** —— models 是底层数据定义，
      它被 services 导入，反过来又导入 services，形式上就是循环依赖
      （当前没炸只因为那是延迟导入）。
      本地时间口径是纯 stdlib 概念，不该由 service 层「授权」，
      因此改为在此处用同一套常量计算，语义与 timeutil.now_local() 完全一致。
    """
    # 与 server.services.timeutil.LOCAL_TZ 保持一致（东八区）
    return datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


# --------------------------------------------------------------------------
# 枚举（用字符串常量，便于直接存进 SQLite 且可读）
# --------------------------------------------------------------------------
class AlarmStatus(str, enum.Enum):
    """聚合状态机（docs §3.2）。"""

    AWAITING_MEDIA = "awaiting_media"  # 告警内容已到，图片/视频待关联
    COMPLETE = "complete"  # 三件套齐了，或窗口超时后按已有内容封板
    EXPIRED = "expired"  # 窗口超时且没有任何图片
    MEDIA_EXPIRED = "media_expired"  # ★ 媒体文件已按保留策略清理，记录保留


class VideoStatus(str, enum.Enum):
    """视频状态。★ 默认 not_requested，即「挂起」。"""

    NOT_REQUESTED = "not_requested"  # 用户还没点，零资源占用
    STARTING = "starting"  # 已点击，正在向 Provider 申请
    READY = "ready"  # 可播放
    FAILED = "failed"  # 申请失败
    UNAVAILABLE = "unavailable"  # 设备侧没有对应录像


class PrincipalKind(str, enum.Enum):
    API_KEY = "api_key"
    USER = "user"


# --------------------------------------------------------------------------
# ★ 多车间（多租户）隔离 —— 核心三张表
# --------------------------------------------------------------------------
class Workshop(Base):
    """车间（租户）。

    ★ 设计要点：
      · code 是隔离依据（稳定，代码里用它），name 只是给人看的
      · 甲方把「1号车间」改名成「装配车间」，只需改 name，
        所有归属关系自动跟着变，不用动一行业务数据
    """

    __tablename__ = "workshop"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(String(256), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Channel(Base):
    """★ 通道登记表 —— 把「上报通道」指派给「车间」。

    为什么这样设计（针对现场真实约束）：

    ① **不绑定 device_id**
       现场是单盒子多通道：deviceID / MAC / IP 全都相同，无法区分。
       而实测确认 **childDevID 每路视频通道天然唯一**（换设备也稳定），
       所以以它为主依据。

    ② **三级兜底**
       childDevID → taskID → channelID。
       有些报文（如 VMD）不带 childDevID，用 channelID 兜底。

    ③ **运行时发现 + 人工指派**
       收到没登记过的通道 → 自动建 status='unassigned' 记录，
       admin 在界面上按「缩略图」认出是哪个车间，点一下分配。
       **换设备、加摄像头都不需要改代码。**

    ④ workshop_code 是隔离的唯一依据
       告警落库时按通道查这里，把 workshop_code 写进 alarm.workshop。
    """

    __tablename__ = "channel"

    # ★ 自增主键：因为 VMD 报文没有 childDevID，不能拿它当主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 主依据：子设备 ID（报文的 childDevID），每路视频通道唯一
    child_dev_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 次依据：算法任务 ID（报文的 taskID）
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 兜底：设备侧通道号（channelID）
    channel_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 设备侧通道名（现场常改乱，仅展示）
    channel_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # 最近见到的设备标识（会变，仅供排查）
    last_device_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_mac: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ★ 归属车间。NULL = 尚未指派
    workshop_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # unassigned(待指派) / assigned(已指派) / disabled(停用)
    status: Mapped[str] = mapped_column(String(16), default="unassigned")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    alarm_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("idx_channel_child", "child_dev_id"),
        Index("idx_channel_task", "task_id"),
        Index("idx_channel_workshop", "workshop_code"),
        Index("idx_channel_status", "status"),
    )


class UserWorkshop(Base):
    """用户 ↔ 车间 多对多关联。

    ★ 为什么用关联表而不是 user.workshop 单字段：
      · 车间主任/厂长需要同时看多个车间
      · admin 看全部（另外用 User.is_superuser）
    单字段现在省事，将来改起来要动表结构 + 所有查询。
    """

    __tablename__ = "user_workshop"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    workshop_code: Mapped[str] = mapped_column(
        String(32), ForeignKey("workshop.code", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# --------------------------------------------------------------------------
# 表
# --------------------------------------------------------------------------
class Device(Base):
    """设备表。由 CMS 注册回调维护。"""

    __tablename__ = "device"

    device_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    online: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Alarm(Base):
    """告警主表 —— 聚合根。"""

    __tablename__ = "alarm"

    # 对外暴露的稳定 ID
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # ---- 来源 ----
    device_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    channel: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    alarm_type: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alarm_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    # ★ 归属车间（隔离的唯一依据）。NULL = 尚未指派。
    #   落库时由 ChannelRegistry 按 childDevID/taskID/channelID 解析。
    workshop: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # 归属依据留痕：便于排查「这条为什么归到 A 车间」
    workshop_rule: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # ★ 筛选/统计冗余列（来自 AIOP；落库时写入，避免每次解析 content_json）
    rule_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    person_count: Mapped[int] = mapped_column(Integer, default=0)
    alarmed_count: Mapped[int] = mapped_column(Integer, default=0)

    # ---- ① 报警消息内容 ----
    content_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ---- ③ 视频（★ 挂起：默认不申请）----
    video_status: Mapped[str] = mapped_column(
        String(24), default=VideoStatus.NOT_REQUESTED.value
    )
    video_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    video_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    video_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # ★ 抓取失败原因（2026-XX）：前端必须能回答「为什么没拿到视频」，
    #   否则界面只会默默变回按钮，用户以为点了没反应。
    video_error: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # ---- 聚合状态 ----
    status: Mapped[str] = mapped_column(String(24), default=AlarmStatus.AWAITING_MEDIA.value)
    # 聚合窗口的截止时间（内部用，不对外暴露）
    correlate_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ★ 媒体过期：文件已被清理策略删除，但记录保留（前端显示占位而不是裂图）
    media_expired: Mapped[bool] = mapped_column(Boolean, default=False)
    media_expired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ★ 人工处置状态：默认 False（未处理）。前端左侧红点 = 未处理条数。
    handled: Mapped[bool] = mapped_column(Boolean, default=False)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    handled_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    images: Mapped[list["AlarmImage"]] = relationship(
        back_populates="alarm",
        cascade="all, delete-orphan",
        order_by="AlarmImage.seq",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_alarm_time", "alarm_time"),
        Index("idx_alarm_device", "device_id", "channel", "alarm_time"),
        Index("idx_alarm_status", "status", "correlate_deadline"),
    )


class AlarmImage(Base):
    """告警图片。一条告警 : N 张图（实测存在 (2)~(25) 这种一组图）。"""

    __tablename__ = "alarm_image"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alarm_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("alarm.id", ondelete="CASCADE"), nullable=False
    )

    # 文件名哈希（如 02C91C96CDD838274D13E28864DE8C9F）
    file_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    # ★ 内容 sha256：用于**按内容去重**
    #   实测设备会用不同文件名上传完全相同的内容（见 add_image 注释）
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 相对项目根的路径，如 storage/2026/09/17/xxx.jpg
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    # ★ 保留 SS 回调给的原始 pFileName（P0 验证 & 排查用）
    source_name: Mapped[str | None] = mapped_column(String(512), nullable=True)

    seq: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 该图片是通过哪条路径关联进来的：ams（报文中自带） / ss（存储回调时序关联）
    linked_by: Mapped[str | None] = mapped_column(String(16), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    alarm: Mapped[Alarm] = relationship(back_populates="images")

    __table_args__ = (Index("idx_img_alarm", "alarm_id", "seq"),)


class PendingImage(Base):
    """★ 待关联图片队列（持久化）。

    为什么需要它（替代原来的内存 list `_pending_images`）：

    ① **重启不丢**
       实测图片比告警早到约 11 秒。服务重启时内存队列里的图片会全部丢失，
       变成永远无人认领的孤儿文件。

    ② **可监控**
       「积压多少张」是串图风险的核心指标。内存队列看不到。

    ③ **顺序配对的前提**
       设备与平台之间是同一根 ISUP 连接，告警与图片到达顺序严格一致。
       本表按 arrived_at 排序，就是配对顺序。

    ④ **可人工兜底**
       配对失败（丢包/乱序）时保留证据，支持事后人工关联。
    """

    __tablename__ = "pending_image"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 原始文件名（SS 回调给的哈希名）
    source_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # 落盘后的相对路径
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    # 内容 sha256（按内容去重）
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ★ 到达时刻：顺序配对的排序依据（同一连接，顺序即语义）
    arrived_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # pending(待配对) / matched(已配对) / ambiguous(歧义待确认) / orphan(孤儿)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    # 配对结果
    matched_alarm_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    matched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_pending_status_time", "status", "arrived_at"),
        Index("idx_pending_content", "content_hash"),
    )


class VideoSession(Base):
    """视频会话。★ 用户点击"查看视频"时才创建，带 TTL 自动回收。"""

    __tablename__ = "video_session"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    alarm_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("alarm.id", ondelete="CASCADE"), nullable=False
    )

    status: Mapped[str] = mapped_column(String(24), default=VideoStatus.STARTING.value)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Provider 返回的句柄（可能是文件路径 / 上游 session id）
    handle: Mapped[str | None] = mapped_column(String(512), nullable=True)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ★ 预留：将来接入登录注册后填 user_id
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("idx_vsession_alarm", "alarm_id"),)


class ApiClient(Base):
    """★ 开放 API 调用方（甲方 IT 部门）。Key 只存哈希。"""

    __tablename__ = "api_client"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    # 逗号分隔的 scope，如 "alarm:read,media:read"
    scopes: Mapped[str] = mapped_column(String(256), default="alarm:read,media:read")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class User(Base):
    """★ 用户账号。登录注册 + 车间权限。"""

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # bcrypt 哈希
    password_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role: Mapped[str] = mapped_column(String(32), default="viewer")
    # ★ 跨车间账号（admin）：可查看全部车间
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # ★ 密码版本号：set_password 时 +1，JWT 里的 pwdv 与之比对实现改密即吊销
    password_version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ApiAuditLog(Base):
    """★ 审计日志。现在就挂中间件，将来接用户体系后能查"谁看了哪条告警"。"""

    __tablename__ = "api_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 用抽象身份，兼容未来的用户体系
    principal_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(128), nullable=True)
    method: Mapped[str] = mapped_column(String(8), default="")
    path: Mapped[str] = mapped_column(String(512), default="")
    status_code: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (Index("idx_audit_time", "created_at"),)
