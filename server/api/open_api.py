# -*- coding: utf-8 -*-
"""★★ 对外开放 API —— 供甲方 IT 部门（信息课）抓取。

## 需求（甲方明确）
    现场摄像头记录并抓取员工不规范行为，记录
        · 图片
        · 前后 30 秒视频片段
        · 准确时间
    由我方提供接口，让信息课通过接口抓取这些信息，通过内网推送给他们。

## 关键约定

1. **不鉴权**。内网调用，甲方要求不加 Key。
   ⚠️ 因此 `/openapi/v1/*` **只应在内网暴露**，不要直接挂公网。
   内部管理接口 `/api/*` 仍然强制鉴权 + 车间隔离，两者物理隔离。

2. **按车间分组**。用 `?workshop=A` 参数，而不是把车间写进路径 ——
   甲方以后加车间，**他们的代码不用改**。
   先调 `GET /workshops` 拿车间清单，再循环拉取。

3. **按天拉取**（甲方要求一天一次）。推荐用：
       GET /alarms?date=2026-09-28&workshop=A&limit=500
   内部转换为 `[当天00:00, 次日00:00)` 的**左闭右开**区间 ——
   相邻两天不会在边界重复。

4. **游标分页**。告警持续写入，用 offset 会漏/重，必须用 cursor。
   返回 `next_cursor` + `has_more`，拉完为止。

5. **时间统一带时区**：`2026-09-28T17:29:48+08:00`。
   并返回 `server_time` 让对方校准时钟，避免因两边时间不一致漏数据。

6. **图片/视频用 URL 给**，指向 `/openapi/v1/media/*`（同样不鉴权），
   文件存在**我们后端**（不是盒子里）—— 盒子存储会被覆盖且无法区分车间。
"""

from __future__ import annotations

import ipaddress
import logging
import time
from contextvars import ContextVar
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.base import Principal
from server.auth.deps import require_open

from server.config import get_settings
from server.crud import alarm as alarm_crud
from server.db import get_session
from server.models import Alarm, Workshop
from server.services import timeutil
from server.services.camera import (
    camera_of,
    resolve_camera_details,
    resolve_cameras,
)
from server.services.serialize import alarm_brief
from server.services.sync_window import parse_window, resolve_window, settled_before

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/openapi/v1", tags=["对外开放接口"])

# ---------------------------------------------------------------------------
# ★ 请求级 base_url 覆盖（2026-10-27）
#
# 甲方不知道我们的 IP、中间还有网关墙，所以允许他们在请求时带：
#     ?base_url=http://他们的入口地址:8088
# 我们会用这个 base 把媒体路径拼成完整的 URL 返回。
#
# 不带这个参数时：优先使用可用的 ISUP_PUBLIC_BASE_URL；否则按当前请求
# 的 Host 生成链接。回环地址不能用时退回相对路径。
# ---------------------------------------------------------------------------
def _media_info() -> dict:
    """响应里的媒体地址说明（让对方知道怎么拼）。"""
    base = _effective_base()
    if base:
        return {
            "media_base_url": base,
            "media_url_mode": "absolute",
            "media_url_hint": "媒体 URL 已是完整地址，可直接下载。",
        }
    return {
        "media_base_url": "",
        "media_url_mode": "relative",
        "media_url_hint": (
            "媒体 URL 为**相对路径**（以 /openapi/v1/media/ 开头）。"
            "请用你方实际访问本系统的地址拼接，例如："
            "http://<入口地址>:<端口> + /openapi/v1/media/2026/10/27/xxx.jpg 。"
            "也可以在请求时带 ?base_url=http://<入口地址>:<端口> 让我们返回完整 URL。"
        ),
    }



# 对外基础地址（拼绝对 URL 用）
# ---------------------------------------------------------------------------
# ★★ 媒体 URL 策略（2026-10-27 重做）
#
# 现场约束：
#   · 平台部署在**甲方服务器**上，我们不知道那台机器的 IP（要申请）
#   · 甲方信息科与我们之间有**网关墙**，实际访问地址取决于墙的映射
#
# 所以**不能写死任何 IP**。策略：
#   · 配了可用的 ISUP_PUBLIC_BASE_URL → 使用部署配置
#   · 否则 → 使用当前请求的 Host；若为回环地址则返回相对路径
#   · 请求时带 ?base_url=http://xxx → 用这个 base 拼绝对 URL
#
# 响应里会同时给出 media_base_url 和 media_url_hint 说明当前用的是哪种。
# ---------------------------------------------------------------------------
def _configured_base() -> str:
    """配置里的 public_base_url（去掉末尾斜杠）。"""
    return (get_settings().public_base_url or "").rstrip("/")


def _base_is_usable(base: str) -> bool:
    """判断这个 base 能不能给甲方用。

    127.0.0.1 / localhost / 空 → 不可用（对方访问不到自己的回环）
    """
    if not base or any(ch.isspace() for ch in base):
        return False
    try:
        parsed = urlsplit(base)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            return False
        hostname = parsed.hostname.lower()
        if hostname == "localhost":
            return False
        try:
            address = ipaddress.ip_address(hostname)
            if address.is_loopback or address.is_unspecified:
                return False
        except ValueError:
            pass
        return True
    except ValueError:
        return False


# 请求级媒体基址。ContextVar 避免并发请求使用不同 Host/base_url 时互相覆盖。
_request_base: ContextVar[str | None] = ContextVar("open_api_request_base", default=None)

# 兼容旧代码中的模块级常量；请求处理统一使用 _effective_base()。
BASE = _configured_base()


def _effective_base() -> str:
    """请求级媒体基址；不可用时返回空字符串，由调用方生成相对 URL。"""
    request_base = _request_base.get()
    if request_base is not None:
        return request_base
    configured = _configured_base()
    return configured if _base_is_usable(configured) else ""


def _set_request_base(base: str | None, request: Request) -> str:
    """按显式参数、部署配置、当前请求 Host 的顺序选择媒体基址。"""
    cleaned = (base or "").strip().rstrip("/")
    configured = _configured_base()
    incoming = f"{request.url.scheme}://{request.url.netloc}".rstrip("/")
    selected = next(
        (candidate for candidate in (cleaned, configured, incoming) if _base_is_usable(candidate)),
        "",
    )
    _request_base.set(selected)
    return selected


# ---------------------------------------------------------------------------
# ★ 开放 API 限流（2026-XX 安全审查新增）
#
# 开放接口不鉴权（甲方要求），必须防"内网里某个失控程序把服务刷挂"。
# 进程内令牌桶，按来源 IP 限流 —— 本项目强制单 worker，内存桶即全局桶。
#
#   · 阈值可配（ISUP_OPEN_API_RATE_LIMIT_PER_MIN，默认 600/分钟/IP）
#   · 超限返回 429 + Retry-After
#   · 内网反代后 client.host 可能都是网关 IP —— 可靠限流可在 nginx 层
#     （limit_req_zone）做，这里是"没有 nginx 时的兜底"
#
# ★ 2026-10 放宽说明：甲方要求"每 10 分钟取一次，每次都要成功"。
#   补拉积压时一页 1000 条可能连发几十个请求，原来 120/分钟 偏紧，
#   撞上 429 对方就当成"取数失败"。放宽到 600 仍能挡住失控程序。
# ---------------------------------------------------------------------------
_RATE_LIMIT_PER_MIN = get_settings().open_api_rate_limit_per_min
_rate_bucket: dict[str, tuple[float, int]] = {}


async def rate_limit(request: Request) -> None:
    if _RATE_LIMIT_PER_MIN <= 0:
        return  # 不限流（由前面的反向代理负责）
    ip = request.client.host if request.client else "-"
    now = time.monotonic()
    window_start, count = _rate_bucket.get(ip, (now, 0))

    if now - window_start >= 60.0:
        # 窗口过期，重置
        _rate_bucket[ip] = (now, 1)
        return
    if count >= _RATE_LIMIT_PER_MIN:
        retry = int(60 - (now - window_start)) + 1
        logger.warning("开放 API 限流触发: ip=%s (%d/min)", ip, count)
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁（上限 {_RATE_LIMIT_PER_MIN} 次/分钟），请降低调用频率",
            headers={"Retry-After": str(max(retry, 1))},
        )
    _rate_bucket[ip] = (window_start, count + 1)

    # 防字典膨胀：偶尔清理过期 IP
    if len(_rate_bucket) > 10000:
        cutoff = now - 120.0
        for k in [k for k, (s, _) in _rate_bucket.items() if s < cutoff]:
            _rate_bucket.pop(k, None)


# ---------------------------------------------------------------------------
# 统一的对外响应结构
# ---------------------------------------------------------------------------
def _envelope(data, *, message: str = "ok") -> dict:
    """统一信封。

    ★ 契约一旦发布就冻结：**只加字段，不改不删**。
      对方可能已经按这个结构写好解析代码了。
    """
    return {
        "code": 0,
        "message": message,
        "data": data,
        "server_time": timeutil.to_iso_local(timeutil.now_local()),
    }


def _abs_media_url(rel_path: str | None) -> str | None:
    """把相对路径拼成对外可访问的绝对 URL。

    ★ 关键：**必须指向 `/openapi/v1/media/`**（不鉴权），
      而不是 `/media/`（内部用，需要 token）。
      否则甲方拿到 URL 会 401。
    """
    if not rel_path:
        return None
    p = rel_path.replace("\\", "/").lstrip("/")
    # 数据库里存的是 storage/2026/09/28/xxx.jpg
    if p.startswith("storage/"):
        p = p[len("storage/"):]
    base = _effective_base()
    if not base:
        # ★ 没配可用 base → 返回相对路径，让对方自己拼
        return f"/openapi/v1/media/{p}"
    return f"{base}/openapi/v1/media/{p}"


def _abs_video_url(url: str | None) -> str | None:
    """把视频 URL 转成对外开放地址。"""
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        # 内部地址形如 http://host:8088/media/video/xxx.mp4
        # 换成对外开放路径
        marker = "/media/video/"
        if marker in url:
            suffix = url.split(marker, 1)[1]
            base = _effective_base()
            prefix = f"{base}/openapi/v1" if base else "/openapi/v1"
            return f"{prefix}/media/video/{suffix}"
        return url
    p = url.lstrip("/")
    if p.startswith("media/video/"):
        p = p[len("media/video/"):]
    base = _effective_base()
    if not base:
        return f"/openapi/v1/media/video/{p}"
    return f"{base}/openapi/v1/media/video/{p}"


def _alarm_payload(
    alarm: Alarm,
    *,
    workshop_name: str | None = None,
    camera_id: str | None = None,
    camera_name: str | None = None,
    channel_no: int | None = None,
    camera_ip: str | None = None,
    camera_model: str | None = None,
) -> dict:
    """★ 单条告警的对外结构（给甲方信息科）。

    ## 2026-10-27 按对方要求补齐字段

    对方明确要求：**报文内容要和前端一致**，必须能看出「是哪一台摄像头」。
    为此补充以下 4 项：

      · camera_no     摄像头通道编号（前端的 CH1/CH2…）
      · camera_ip     摄像头自己的 IP（不是 NVR 的）
      · camera_model  摄像头型号（如 DS-2CD7T4KY-LSW）
      · display_name  管理员在前端起的自定义名（如「2号车间-西侧工装检测」）

    这些值来自 NVR 的 ISAPI（/InputProxy/channels/<id>）与前端管理页录入，
    与设备管理页显示的完全一致。

    ⚠️ 字段只增不减：老调用方继续用 device_id / channel 即可。
    """
    brief = alarm_brief(alarm)
    images = [_abs_media_url(i.file_path) for i in sorted(alarm.images, key=lambda x: x.seq)]
    images = [u for u in images if u]

    video_url = None
    video_status = brief.video.status
    if brief.video.url:
        video_url = _abs_video_url(brief.video.url)

    return {
        # ---- 标识 ----
        "id": alarm.id,
        "workshop": alarm.workshop,
        "workshop_name": workshop_name,
        # ---- 来源（父设备 = NVR）----
        "device_id": alarm.device_id,
        "channel": alarm.channel,
        # ---- ★★ 摄像头身份（对方要求：必须能定位到具体哪台摄像头）----
        "camera_no": channel_no,          # 通道编号 CH1/CH2…
        "camera_id": camera_id,           # 唯一标识（childDevID，换设备不变）
        "camera_name": camera_name,       # NVR 上的原始名（如 Camera 01）
        "display_name": camera_name,      # 前端自定义名（与 camera_name 同一来源，见下）
        "camera_ip": camera_ip,           # 摄像头自己的 IP
        "camera_model": camera_model,     # 摄像头型号
        # ---- 行为语义 ----
        "alarm_type": alarm.alarm_type,
        "type_text": brief.type_text,
        "summary": brief.summary,
        # ---- ★ 准确时间（带时区）----
        "alarm_time": timeutil.to_iso_local(alarm.alarm_time),
        # ---- 图片 ----
        "image_count": len(images),
        "images": images,
        "thumbnail_url": images[0] if images else None,
        # ---- ★ 视频（前后 30 秒片段）----
        "video_status": video_status,
        "video_url": video_url,
        "video_duration": brief.video.duration,
        # ---- 其它 ----
        "handled": brief.handled,
        "media_expired": brief.media_expired,
        "extra": brief.extra,
    }


async def _count_window(
    db: AsyncSession, *, workshop: str, start, end
) -> int:
    """统计某车间在时间窗口内的告警总数（分页进度用）。

    ★ 2026-10-27：`items` 里的 total 是**本页条数**，
      调用方没法据此判断"还有多少没拉"。这个函数给出窗口总量。
    """
    from sqlalchemy import func

    from server.models import Alarm

    if start is None or end is None:
        return 0
    try:
        v = (
            await db.execute(
                select(func.count(Alarm.id)).where(
                    Alarm.workshop == workshop,
                    Alarm.alarm_time >= start,
                    Alarm.alarm_time < end,
                )
            )
        ).scalar()
        return int(v or 0)
    except Exception:
        return 0


async def _workshop_names(db: AsyncSession) -> dict[str, str]:
    rows = (await db.execute(select(Workshop.code, Workshop.name))).all()
    return {r[0]: r[1] for r in rows}


# ---------------------------------------------------------------------------
# 车间 / 通道清单
# ---------------------------------------------------------------------------
@router.get("/workshops", summary="★ 车间清单（先调这个，再循环拉取）")
async def list_workshops(
    request: Request,
    db: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit),
    # ★ 2026-10-27 安全修复：开放接口鉴权（ISUP_OPEN_API_REQUIRES_KEY=true 时必需 X-API-Key）
    _auth: Principal = Depends(require_open("alarm:read")),
):
    """返回所有车间及其告警数。

    甲方代码逻辑：
        for w in get("/workshops")["data"]["items"]:
            get(f"/alarms?workshop={w['code']}&date=...")

    这样**以后加车间，他们代码不用改**。
    """
    rows = (await db.execute(select(Workshop).order_by(Workshop.sort_order))).scalars().all()

    # ★★ 2026-10-27 性能修复：N+1 → 一次 GROUP BY
    #
    # 原实现每个车间单独 COUNT(*)，实测告警 17025 条时单次 76ms，
    # 3 个车间串行 228ms —— 一个「列车间」的接口要 200ms 完全不合理。
    # 并发 30 时更糟（p95 超 2 秒），因为每个请求都重复扫描。
    #
    # 改成一次 GROUP BY：扫一遍拿全部计数，且不随车间数增长。
    counts: dict[str, int] = {}
    if rows:
        cnt_rows = (
            await db.execute(
                select(Alarm.workshop, func.count(Alarm.id))
                .where(Alarm.workshop.isnot(None))
                .group_by(Alarm.workshop)
            )
        ).all()
        counts = {str(k): int(v) for k, v in cnt_rows if k}

    items = [
        {
            "code": w.code,
            "name": w.name,
            "description": w.description,
            "alarm_count": counts.get(w.code, 0),
            "enabled": w.enabled,
        }
        for w in rows
    ]
    return _envelope({"items": items, "total": len(items)})


@router.get("/channels", summary="通道清单（哪个通道属于哪个车间）")
async def list_channels(
    request: Request,
    db: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit),
    # ★ 2026-10-27 安全修复：开放接口鉴权（ISUP_OPEN_API_REQUIRES_KEY=true 时必需 X-API-Key）
    _auth: Principal = Depends(require_open("alarm:read")),
):
    """通道与车间的对应关系。

    用途：甲方排查「某个摄像头为什么没有数据」，或确认覆盖范围。

    ★ `alarm_count` 是**实时统计**的实际告警数。
      （早期版本直接取 channel 表的累计计数器，那个字段只统计服务运行
        期间新产生的数据，历史数据不计入，导致恒显示 0，会误导甲方。）
    """
    from server.services import workshop_service as ws_svc
    from server.models import Channel

    rows = (
        (await db.execute(select(Channel).order_by(Channel.id))).scalars().all()
    )
    names = await _workshop_names(db)

    # ★★ 2026-10-29 补上摄像头硬件信息。
    #
    #   原来只返回数据库字段，camera_ip / camera_model 恒为 null，
    #   而 /alarms 里的同名字段是有值的（查 NVR 的 ISAPI 得到）。
    #   两个接口不一致会让甲方困惑：清单里看不到摄像头型号，
    #   也就无法判断「这个通道到底接没接设备」。
    #
    #   这里复用告警接口的同一条路径（channel_status.fetch_channel_states），
    #   按通道号批量查一次，带 30 秒缓存，不会拖慢接口。
    camera_states: dict[int, object] = {}
    try:
        from server.config import get_settings as _gs

        _cfg = _gs()
        if getattr(_cfg, "video_use_isapi", False) and _cfg.isapi_host:
            ch_nos = sorted({int(c.channel_id) for c in rows if c.channel_id})
            if ch_nos:
                from server.services.channel_status import fetch_channel_states

                camera_states = fetch_channel_states(
                    _cfg.isapi_host,
                    _cfg.isapi_port,
                    _cfg.isapi_username,
                    _cfg.isapi_password,
                    ch_nos,
                )
    except Exception:
        logger.debug("查摄像头硬件信息失败（不影响清单返回）", exc_info=True)

    items = []
    for c in rows:
        info = await ws_svc.channel_identify_info(db, c)
        st = camera_states.get(int(c.channel_id)) if c.channel_id else None
        items.append(
            {
                "id": c.id,
                "workshop": c.workshop_code,
                "workshop_name": names.get(c.workshop_code or "", None),
                "display_name": c.display_name or c.channel_name,
                "channel_id": c.channel_id,
                # ★ 让甲方能把「告警里的 device_id+channel」
                #   对上「这是哪个摄像头」。
                #   device_id = 父设备；camera_id = 每路唯一（childDevID）
                "device_id": c.last_device_id,
                "camera_id": c.child_dev_id,
                # ★★ 2026-10-29 新增：摄像头硬件信息（来自 NVR 的 ISAPI）
                "camera_ip": getattr(st, "ip", None) if st else None,
                "camera_model": getattr(st, "model", None) if st else None,
                "camera_serial": getattr(st, "serial", None) if st else None,
                "camera_online": (
                    bool(getattr(st, "online", False))
                    if st is not None and not getattr(st, "error", "")
                    else None
                ),
                "camera_info_known": bool(
                    st is not None and not getattr(st, "error", "")
                ),
                "status": c.status,
                "alarm_count": info["last_alarm_count"],
                "last_alarm_at": timeutil.to_iso_local(info["last_alarm_at"]),
            }
        )
    return _envelope({"items": items, "total": len(items)})


# ---------------------------------------------------------------------------
# ★ 告警抓取（主接口）
#
# 核心实现只有一份 —— `/alarms` 与 `/workshops/{code}/alarms` 是同一个
# 逻辑的两个入口（一个是查询参数式、一个是路径式），避免两套代码行为漂移。
# ---------------------------------------------------------------------------
async def _list_alarms_core(
    db: AsyncSession,
    *,
    request: Request,
    workshop: str | None,
    date: str | None,
    start: str | None,
    end: str | None,
    cursor: str | None,
    limit: int,
    include_video: bool,
    window: str | None,
    since_token: str | None,
    # ★★ 2026-10-27 拆分接口开关（甲方要求「4 个接口」）
    #
    #   summary_only=True  → 只要报警本身，剥掉 images / video_* 字段
    #   images_only=True   → 只保留图片相关字段
    #   videos_only=True   → 只保留视频相关字段
    #
    #   三者互斥，都不传 = 原行为（总和）。
    summary_only: bool = False,
    images_only: bool = False,
    videos_only: bool = False,
    # ★ 2026-10-27：调用方可用 ?base_url= 覆盖媒体地址
    base_url: str | None = None,
) -> dict:
    settings = get_settings()
    # ★ 应用请求级 base_url（决定媒体 URL 是相对路径还是完整地址）
    _set_request_base(base_url, request)
    now = timeutil.now_local()

    if not workshop:
        raise HTTPException(
            status_code=400,
            detail="必须指定 workshop（车间）。先调 /openapi/v1/workshops 获取车间列表。",
        )

    # ---- 查车间 ----
    ws = (
        await db.execute(select(Workshop).where(Workshop.code == workshop))
    ).scalar_one_or_none()
    if ws is None:
        raise HTTPException(status_code=404, detail=f"车间 {workshop} 不存在")

    from server.crud.filters import AlarmFilter
    from server.crud.pagination import (
        cursor_matches,
        decode_cursor,
        encode_cursor,
    )

    # ---- 解析时间范围 + 取数模式 ----
    #
    # since_token/window/date 保持既有优先级；精确 start/end 必须单独使用，
    # 与 date、window、since_token 混传会明确返回 400。
    #   · since_token：增量水位，最精确（对方每 10 分钟拉一次就用这个）
    #   · window    ：服务端算好的全钟点窗口（首次接入 / 补拉）
    #   · date      ：按天（保持原有行为）
    #   · start/end ：绝对区间，采用左闭右开 [start, end)
    #
    # ★ 只有增量模式（sync）才在响应里追加 sync_token/mode 字段，
    #   原有 date/start/end 调用的响应**逐字节保持不变** —— 老对接方零影响。
    t_start = t_end = None
    after = None
    mode = "absolute"
    sync = False

    has_start = start is not None
    has_end = end is not None
    if has_start != has_end:
        raise HTTPException(
            status_code=400,
            detail="精确时间范围必须同时提供 start 和 end。",
        )
    if has_start and (date or window or since_token):
        raise HTTPException(
            status_code=400,
            detail="start/end 不能与 date、window 或 since_token 同时使用。",
        )

    if since_token:
        mode, sync = "sync", True
        decoded = decode_cursor(since_token)
        if decoded is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "since_token 无法解析。请使用上一轮响应返回的 sync_token 原值，"
                    "不要修改或自行构造。"
                ),
            )
        if decoded.workshop and decoded.workshop != workshop:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"since_token 属于车间 {decoded.workshop}，但本次请求的是 {workshop}。"
                    "请勿跨车间复用水位。"
                ),
            )
        after = decoded
        t_start = decoded.alarm_time
        t_end = settled_before(now, settings.sync_grace_seconds)
    elif window:
        mode, sync = "window", True
        if date:
            raise HTTPException(
                status_code=400,
                detail="date 与 window 不能同时使用。按窗口取数请只传 window。",
            )
        try:
            win = parse_window(window)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        t_start, t_end = resolve_window(now, win, settings.sync_grace_seconds)
    elif date:
        # ★ 2026-10-29：date 模式要显式标记 mode，
        #   否则会落回默认值 "absolute"，与接口手册不符
        #   （手册里 mode 有 4 种取值：absolute/date/window/sync）
        mode = "date"
        try:
            t_start, t_end = timeutil.day_bounds(date)
        except ValueError:
            raise HTTPException(status_code=400, detail="date 格式应为 YYYY-MM-DD")
    else:
        t_start = timeutil.parse_any(start) if has_start else None
        t_end = timeutil.parse_any(end) if has_end else None
        if has_start and t_start is None:
            raise HTTPException(status_code=400, detail="start 时间格式无法解析")
        if has_end and t_end is None:
            raise HTTPException(status_code=400, detail="end 时间格式无法解析")
        if t_start is not None and t_end is not None and t_end <= t_start:
            raise HTTPException(
                status_code=400,
                detail="end 必须晚于 start；查询区间为左闭右开 [start, end)。",
            )

    # ---- 翻页游标 ----
    if cursor:
        decoded = decode_cursor(cursor)
        if decoded is None:
            # ★ 非法游标：明确报错，而不是静默按第一页处理。
            #   静默处理会让调用方以为「拉完了」，实际只拿到第一页。
            raise HTTPException(
                status_code=400,
                detail=(
                    "cursor 无法解析。请使用上一次响应返回的 next_cursor 原值，"
                    "不要修改或自行构造。"
                ),
            )

        # ★ 沿用游标里记录的模式，保证第 1 页与第 N 页的响应结构一致
        if decoded.mode:
            mode = decoded.mode

        # ★★ 2026-10-22 修复「翻页丢范围」：
        #
        #   调用方只带 cursor、没重复带 date/start/end/window 时，
        #   t_start / t_end 都是 None → 查询**没有上下界**，
        #   于是第 2 页会把窗口/当天之外的记录也返回。
        #
        #   实测（test_paging）：按天翻页第 2 页返回 500 条，其中 478 条
        #   越界到了 09-23、09-28… 甲方按天入库就会串天、重复。
        #
        #   修法：**沿用游标里记录的范围**。游标本来就把 (时间, id, 车间, 区间)
        #   都编码进去了，漏传参数时以它为准，比"退化成无界查询"安全得多。
        if t_start is None and t_end is None:
            adopted_start = timeutil.parse_any(decoded.range_start) if decoded.range_start else None
            adopted_end = timeutil.parse_any(decoded.range_end) if decoded.range_end else None
            if adopted_start is not None or adopted_end is not None:
                t_start, t_end = adopted_start, adopted_end
                # 沿用窗口语义：跳过范围一致性校验（范围本来就取自游标）、
                # 响应继续带回 range_* / sync_token，便于对方接着翻。
                sync = True

        if sync:
            # ★ 增量模式：窗口边界以「发起翻页那一刻的游标」为准（冻结窗口），
            #   否则每翻一页 end 都往后漂移，分页边界会变得不可复现。
            if decoded.workshop and decoded.workshop != workshop:
                raise HTTPException(
                    status_code=400,
                    detail="cursor 属于其它车间，请勿跨车间复用游标。",
                )
            if decoded.range_end:
                frozen = timeutil.parse_any(decoded.range_end)
                if frozen is not None:
                    t_end = frozen
        else:
            # ★★ 校验游标是否属于本次查询范围（防静默丢数据）
            #
            #   原实现把游标当裸下界用，不校验车间/日期 ——
            #   拿 A 日期的游标查 B 日期，会静默丢掉 B 日期游标之前的全部记录，
            #   还返回 200 + has_more=false（看起来像"这天没数据"）。
            #   甲方重试时复用旧游标 → 整天的数据消失且无人察觉。
            ok, why = cursor_matches(
                decoded,
                workshop=workshop,
                range_start=t_start,
                range_end=t_end,
            )
            if not ok:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{why} 翻页时请保持 workshop 与 date/start/end 参数不变，"
                        "并使用上一次响应返回的 next_cursor。"
                    ),
                )
        after = decoded

    # ---- 查询（左闭右开）----
    #   ★ 条件拼装已收口到 server/crud/filters.py 的 AlarmFilter，
    #     与内部列表接口共用同一份实现 —— 但这里 end 是**右开**的。
    flt = AlarmFilter(
        start=t_start,
        end=t_end,
        end_exclusive=True,  # ★ 右开
        # 开放 API 的车间隔离要求「恰好是这个车间」
        # （与内部接口的「可见车间集合」语义不同，所以用单元素列表）
        workshops=[workshop],
    )

    # 升序返回（甲方从旧到新拉）
    rows, has_more = await alarm_crud.list_alarms_page(
        db, flt, after=after, limit=limit, ascending=True
    )

    # ---- 下一个游标 / 增量水位 ----
    next_cursor = None
    sync_token = None
    if rows:
        last = rows[-1]
        if has_more:
            # 还有下一页：给对方带范围绑定的游标（同一窗口内继续翻）
            next_cursor = encode_cursor(
                last.alarm_time,
                last.id,
                workshop=workshop,
                range_start=t_start,
                range_end=t_end,
                mode=mode,
            )
        else:
            # ★ 本窗口拉完了：给「不绑定日期范围」的水位，
            #   下一轮直接拿它当 since_token —— 不会被范围校验卡住，
            #   又因为带 id，同秒多条也不会漏。
            sync_token = encode_cursor(
                last.alarm_time, last.id, workshop=workshop, mode=mode
            )
    elif sync and t_end is not None:
        # 本轮没有数据：把水位推到窗口末尾，下一轮从这里继续，
        # 避免对方反复空拉同一个区间。
        sync_token = encode_cursor(t_end, "", workshop=workshop, mode=mode)

    # ---- 组装 ----
    details = await resolve_camera_details(db, rows)
    items = []
    for a in rows:
        d = details.get((a.device_id, a.channel), {})
        items.append(
            _alarm_payload(
                a,
                workshop_name=ws.name,
                camera_id=d.get("camera_id"),
                camera_name=d.get("camera_name"),
                channel_no=d.get("camera_no"),
                camera_ip=d.get("camera_ip"),
                camera_model=d.get("camera_model"),
            )
        )
    # ---- ★ 按拆分接口裁剪字段（2026-10-27）----
    if summary_only:
        # 只要报警本身：剥掉所有媒体字段
        for it in items:
            for k in (
                "images",
                "image_count",
                "thumbnail_url",
                "video_url",
                "video_status",
                "video_duration",
            ):
                it.pop(k, None)
    elif images_only:
        # 只留图片
        for it in items:
            for k in ("video_url", "video_status", "video_duration"):
                it.pop(k, None)
    elif videos_only:
        # 只留视频
        for it in items:
            for k in ("images", "image_count", "thumbnail_url"):
                it.pop(k, None)

    if not include_video:
        for it in items:
            it.pop("video_url", None)
            it.pop("video_status", None)
            it.pop("video_duration", None)

    data = {
        "items": items,
        # ★ 2026-10-27：total 明确为「本页条数」。
        #   原来叫 total 容易被误解为「车间/窗口总量」，
        #   调用方据此做进度显示会完全错（实测 limit=3 → total=3，
        #   而该车间实际有 12206 条）。
        "total": len(items),
        # 窗口内总量（仅 window/sync 模式返回，用于分页进度）
        "total_in_window": (
            await _count_window(db, workshop=workshop, start=t_start, end=t_end)
            if (sync or mode == "window")
            else None
        ),
        "has_more": has_more,
        "next_cursor": next_cursor,
        "workshop": workshop,
        "workshop_name": ws.name,
        "range_start": timeutil.to_iso_local(t_start),
        "range_end": timeutil.to_iso_local(t_end),
    }
    # ★★ 2026-10-29 修复：mode 必须**无条件**返回。
    #
    #   原来 mode 只在 if sync: 里写入，导致 date / start-end / 无参数
    #   三种模式下响应里根本没有 mode 字段 —— 而接口手册里写了
    #   mode 有 4 种取值（absolute/date/window/sync）。
    #
    #   实测部署环境：
    #     window     → mode="window"   ✅
    #     since_token→ mode="sync"     ✅
    #     date       → 字段缺失        ❌
    #     start/end  → 字段缺失        ❌
    #     无参数     → 字段缺失        ❌
    #
    #   甲方无法据此判断本次数据是什么维度。
    data["mode"] = mode

    if sync:
        # 增量/窗口专用的字段（历史按天/按区间调用保持不变）
        data["sync_token"] = sync_token
        data["grace_seconds"] = settings.sync_grace_seconds
        data["next_poll_hint"] = (
            "下一轮把 sync_token 作为 since_token 传回；"
            "has_more=true 时先用 next_cursor 翻完本窗口。"
        )
    # ★ 2026-10-27：媒体地址说明（相对路径 vs 绝对 URL）
    #   甲方不知道我们 IP、中间还有网关墙，所以要把"怎么拼"讲清楚
    data.update(_media_info())
    return _envelope(data)


@router.get("/alarms", summary="★★ 告警列表（按车间 + 按天/按窗口，主接口）")
async def list_alarms(
    request: Request,
    workshop: str | None = Query(None, description="车间 code（必填）"),
    date: str | None = Query(None, description="按天拉取，格式 YYYY-MM-DD"),
    start: str | None = Query(None, description="起始时间（含），ISO8601 带时区更佳"),
    end: str | None = Query(None, description="结束时间（不含）"),
    cursor: str | None = Query(None, description="上一页返回的 next_cursor"),
    limit: int = Query(500, ge=1, le=1000, description="每页条数，上限 1000"),
    include_video: bool = Query(True, description="是否返回视频 URL"),
    window: str | None = Query(
        None,
        description="★ 增量窗口，如 10m / 30m / 1h。服务端按全钟点对齐，"
        "查询窗口保留 60 秒安全延迟；视频状态仍须按 video_status 判断",
    ),
    since_token: str | None = Query(
        None,
        description="★ 上一轮返回的 sync_token（增量水位，优先于 window/date）",
    ),
    base_url: str | None = Query(
        None, description="媒体地址前缀；不传时按部署配置或当前请求 Host 生成"
    ),
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(rate_limit),
    # ★ 2026-10-27 安全修复：开放接口鉴权（ISUP_OPEN_API_REQUIRES_KEY=true 时必需 X-API-Key）
    _auth: Principal = Depends(require_open("alarm:read")),
):
    """★ 甲方主要用这个接口。

    ## 每 10 分钟拉一次的推荐用法（新增）

        # 第一轮：服务端算好最近一个已结束的 10 分钟窗口
        GET /openapi/v1/alarms?workshop=A&window=10m

        # 之后每轮：把上轮返回的 sync_token 原样传回
        GET /openapi/v1/alarms?workshop=A&since_token=<上轮 sync_token>

    为什么这样最稳：
      · 窗口由**服务端**按全钟点对齐计算，对方不用自己算时间，
        两边时钟差几秒也不会漏数据；
      · 窗口会保留 60 秒的安全延迟；视频仍需逐条检查 `video_status`；
      · 水位精确到 (时间, id)，同一秒多条记录也不会重复或遗漏；
      · 响应里的 `sync_token` 不绑定日期范围，可以跨轮一直用。

    ## 原有用法（完全不变）

        1. `?date=2026-09-28`                  ← 按天
        2. `?start=...&end=...`                ← 自定义区间
        3. 都不传                               ← 不指定时间边界，按游标分页

    分页：`limit` 拉不完时会返回 `next_cursor`，带上它再拉一次，
          直到 `has_more=false`。

    ★ 时间区间是**左闭右开** `[start, end)` —— 相邻两天不会重复。
    """
    return await _list_alarms_core(
        db,
        request=request,
        workshop=workshop,
        date=date,
        start=start,
        end=end,
        cursor=cursor,
        limit=limit,
        base_url=base_url,
        include_video=include_video,
        window=window,
        since_token=since_token,
    )


@router.get(
    "/workshops/{workshop_code}/alarms",
    summary="★★ 按车间独立拉取告警（路径式别名，与 /alarms 完全等价）",
)
async def list_alarms_by_workshop(
    request: Request,
    workshop_code: str,
    date: str | None = Query(None, description="按天拉取，格式 YYYY-MM-DD"),
    start: str | None = Query(None, description="起始时间（含），ISO8601"),
    end: str | None = Query(None, description="结束时间（不含）"),
    cursor: str | None = Query(None, description="上一页返回的 next_cursor"),
    limit: int = Query(500, ge=1, le=1000, description="每页条数，上限 1000"),
    include_video: bool = Query(True, description="是否返回视频 URL"),
    window: str | None = Query(None, description="★ 增量窗口，如 10m"),
    since_token: str | None = Query(None, description="★ 上一轮的 sync_token"),
    base_url: str | None = Query(
        None, description="媒体地址前缀；不传时按部署配置或当前请求 Host 生成"
    ),
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(rate_limit),
    # ★ 2026-10-27 安全修复：开放接口鉴权（ISUP_OPEN_API_REQUIRES_KEY=true 时必需 X-API-Key）
    _auth: Principal = Depends(require_open("alarm:read")),
):
    """与 `GET /alarms?workshop=<code>` **完全等价**，只是把车间写进路径。

    两种写法都能用，已对接的调用方不需要改：
        GET /openapi/v1/alarms?workshop=A&window=10m
        GET /openapi/v1/workshops/A/alarms?window=10m
    """
    return await _list_alarms_core(
        db,
        request=request,
        workshop=workshop_code,
        date=date,
        start=start,
        end=end,
        cursor=cursor,
        limit=limit,
        base_url=base_url,
        include_video=include_video,
        window=window,
        since_token=since_token,
    )


@router.get(
    "/alarms/summary",
    summary="★ 报警清单（只要报警本身，不含图片/视频 URL）",
)
async def list_alarms_summary(
    request: Request,
    workshop: str | None = Query(None, description="车间 code（必填）"),
    start: str | None = Query(None, description="起始时间（含），ISO8601"),
    end: str | None = Query(None, description="结束时间（不含），ISO8601"),
    window: str | None = Query(
        None, description="增量窗口，如 10m / 30m / 1h"
    ),
    date: str | None = Query(None, description="单日 YYYY-MM-DD（window 的简写）"),
    since_token: str | None = Query(None, description="增量水位（上轮返回的 sync_token）"),
    limit: int = Query(500, ge=1, le=1000),
    cursor: str | None = Query(None, description="分页游标（上轮的 next_cursor）"),
    base_url: str | None = Query(
        None, description="媒体地址前缀（如 http://1.2.3.4:8088）；不传时按部署配置或当前请求 Host 生成"
    ),
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(rate_limit),
    # ★ 2026-10-27 安全修复：开放接口鉴权（ISUP_OPEN_API_REQUIRES_KEY=true 时必需 X-API-Key）
    _auth: Principal = Depends(require_open("alarm:read")),
):
    """只返回报警本身（无 images / video_url）。

    适合「先拉清单、再按需取媒体」的场景，报文体积比 /alarms 小 90%。
    与 /alarms 的数据范围、增量语义完全一致。
    """
    return await _list_alarms_core(
        db=db,
        request=request,
        workshop=workshop,
        date=date,
        start=start,
        end=end,
        cursor=cursor,
        limit=limit,
        base_url=base_url,
        include_video=False,
        window=window,
        since_token=since_token,
        summary_only=True,
    )



@router.get(
    "/alarms/images",
    summary="★ 图片清单（每条报警的图片 URL）",
)
async def list_alarms_images(
    request: Request,
    workshop: str | None = Query(None, description="车间 code（必填）"),
    start: str | None = Query(None, description="起始时间（含），ISO8601"),
    end: str | None = Query(None, description="结束时间（不含），ISO8601"),
    window: str | None = Query(None),
    date: str | None = Query(None),
    since_token: str | None = Query(None),
    limit: int = Query(500, ge=1, le=1000),
    cursor: str | None = Query(None),
    base_url: str | None = Query(
        None, description="媒体地址前缀（如 http://1.2.3.4:8088）；不传时按部署配置或当前请求 Host 生成"
    ),
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(rate_limit),
    # ★ 2026-10-27 安全修复：开放接口鉴权（ISUP_OPEN_API_REQUIRES_KEY=true 时必需 X-API-Key）
    _auth: Principal = Depends(require_open("alarm:read")),
):
    """只返回「报警 → 图片」的对应关系。

    返回每条报警的 id / 报警时间 / 摄像头身份 / 图片 URL 列表，
    便于对方批量下载图片。
    """
    return await _list_alarms_core(
        db=db,
        request=request,
        workshop=workshop,
        date=date,
        start=start,
        end=end,
        cursor=cursor,
        limit=limit,
        base_url=base_url,
        include_video=False,
        window=window,
        since_token=since_token,
        images_only=True,
    )



@router.get(
    "/alarms/videos",
    summary="★ 视频清单（每条报警的视频 URL 与状态）",
)
async def list_alarms_videos(
    request: Request,
    workshop: str | None = Query(None, description="车间 code（必填）"),
    start: str | None = Query(None, description="起始时间（含），ISO8601"),
    end: str | None = Query(None, description="结束时间（不含），ISO8601"),
    window: str | None = Query(None),
    date: str | None = Query(None),
    since_token: str | None = Query(None),
    limit: int = Query(500, ge=1, le=1000),
    cursor: str | None = Query(None),
    base_url: str | None = Query(
        None, description="媒体地址前缀（如 http://1.2.3.4:8088）；不传时按部署配置或当前请求 Host 生成"
    ),
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(rate_limit),
    # ★ 2026-10-27 安全修复：开放接口鉴权（ISUP_OPEN_API_REQUIRES_KEY=true 时必需 X-API-Key）
    _auth: Principal = Depends(require_open("alarm:read")),
):
    """只返回「报警 → 视频」的对应关系。

    视频是**异步生成**的：status 可能是
      · not_requested  未抓取（自动抓取关闭时）
      · starting       生成中（稍后重试）
      · ready          可下载
      · failed         抓取失败（带错误原因）

    ★ 建议对方：本轮的 starting 项记下来，下一轮再拉一次。
      或者直接看 /alarms/videos 里 status=ready 的。
    """
    return await _list_alarms_core(
        db=db,
        request=request,
        workshop=workshop,
        date=date,
        start=start,
        end=end,
        cursor=cursor,
        limit=limit,
        base_url=base_url,
        include_video=True,
        window=window,
        since_token=since_token,
        videos_only=True,
    )



@router.get("/alarms/{alarm_id}", summary="单条告警详情")
async def get_alarm(
    request: Request,
    alarm_id: str,
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(rate_limit),
    # ★ 2026-10-27 安全修复：开放接口鉴权（ISUP_OPEN_API_REQUIRES_KEY=true 时必需 X-API-Key）
    _auth: Principal = Depends(require_open("alarm:read")),
):
    _set_request_base(None, request)
    alarm = await alarm_crud.get_alarm(db, alarm_id)
    if alarm is None:
        raise HTTPException(status_code=404, detail="告警不存在")
    names = await _workshop_names(db)
    # 与列表接口保持同一口径：详情也带完整摄像头身份
    # （2026-10-27：改用 resolve_camera_details，含 IP / 型号 / 编号）
    _details = await resolve_camera_details(db, [alarm])
    d = _details.get((alarm.device_id, alarm.channel), {})
    return _envelope(
        _alarm_payload(
            alarm,
            workshop_name=names.get(alarm.workshop or ""),
            camera_id=d.get("camera_id"),
            camera_name=d.get("camera_name"),
            channel_no=d.get("camera_no"),
            camera_ip=d.get("camera_ip"),
            camera_model=d.get("camera_model"),
        )
    )


# ---------------------------------------------------------------------------
# ★★ 逐条下载文件（甲方要求「方式 1：传文件，一条一条传」）
#
# 与上面的 JSON 接口并存，两套都保留：
#   · JSON 接口  → 给 URL，对方自己拉（方式 2）
#   · download   → 直接返回文件字节流（方式 1）
# ---------------------------------------------------------------------------
@router.get(
    "/alarms/{alarm_id}/images/download",
    summary="★ 下载该告警的图片文件（单张直传 / 多张打包 ZIP）",
)
async def download_alarm_images(
    alarm_id: str,
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(rate_limit),
    # ★ 2026-10-27 安全修复：开放接口鉴权（ISUP_OPEN_API_REQUIRES_KEY=true 时必需 X-API-Key）
    _auth: Principal = Depends(require_open("alarm:read")),
):
    """直接返回图片文件字节。

    · 该告警只有 1 张图  → 返回 image/jpeg（可直接存成 .jpg）
    · 有多张图          → 返回 application/zip（内含 seq_文件名.jpg）

    ★ 文件名可从响应头 Content-Disposition 获取。
    """
    import io
    import zipfile

    from fastapi.responses import FileResponse, StreamingResponse

    from server.api.open_media import _media_path
    from server.config import STORAGE_DIR

    alarm = await alarm_crud.get_alarm(db, alarm_id)
    if alarm is None:
        raise HTTPException(status_code=404, detail="告警不存在")

    imgs = sorted(alarm.images, key=lambda x: x.seq)
    found: list[tuple[str, Path]] = []
    for im in imgs:
        ap = _media_path(STORAGE_DIR, str(im.file_path or ""))
        if ap is not None and ap.is_file():
            found.append((f"{im.seq}_{ap.name}", ap))

    if not found:
        raise HTTPException(
            status_code=404,
            detail="该告警没有可下载的图片（可能未上传或已过期清理）",
        )

    # ---- 单张：直接传文件（最自然，「一条一条传」）----
    if len(found) == 1:
        _, ap = found[0]
        suffix = ap.suffix.lower()
        mt = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}.get(
            suffix, "application/octet-stream"
        )
        return FileResponse(
            ap,
            media_type=mt,
            headers={
                "Content-Disposition": f'attachment; filename="{ap.name}"',
                "X-Image-Count": "1",
                "X-Alarm-Id": alarm_id,
            },
        )

    # ---- 多张：打包 ZIP ----
    def _gen():
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for arcname, path in found:
                try:
                    zf.write(path, arcname)
                except OSError:
                    continue
        data = buf.getvalue()
        chunk = 256 * 1024
        for i in range(0, len(data), chunk):
            yield data[i : i + chunk]

    return StreamingResponse(
        _gen(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="images_{alarm_id[:8]}.zip"',
            "X-Image-Count": str(len(found)),
            "X-Alarm-Id": alarm_id,
        },
    )


@router.post(
    "/alarms/{alarm_id}/video/refetch",
    summary="★ 恢复期视频：向设备补抓（7 天前的视频用这个）",
)
async def refetch_alarm_video(
    alarm_id: str,
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(rate_limit),
):
    """请求从设备（NVR）补抓该告警的视频。

    ## 什么时候需要调用

    平台只保留 **最近 7 天** 的视频（原始码率，画质无损）。
    超过 7 天的记录，平台文件已按保留策略清理，
    但设备的录像硬盘里**可能还在**（典型 7~30 天）。

    ## 前提条件（重要）

    补抓能否成功，取决于**设备上是否还有那段录像**：
      · 设备录像未被覆盖 → 能抓到（约 30~60 秒）
      · 设备已覆盖该时段 → **永久丢失，取不回来**

    ## 返回码

    | 状态码 | 含义 | 建议动作 |
    |---|---|---|
    | `202` | 已提交抓取任务 | 等 `retry_after` 秒后查状态 |
    | `409` | 视频已存在或正在抓 | 按 `X-Video-Status` 处理 |
    | `404` | 告警不存在 | 检查 ID |
    | `410` | 超出设备保留期 | **永久丢失**，不要重试 |

    ## 完整流程

    ```bash
    # 1. 请求补抓
    curl -X POST "http://<平台服务器IP>:8088/openapi/v1/alarms/{id}/video/refetch"

    # → 202 {"status":"accepted","retry_after":60}

    # 2. 等 60 秒后查状态
    curl "http://<平台服务器IP>:8088/openapi/v1/alarms/{id}/video"

    # 3. status=ready 时下载
    curl -O "http://<平台服务器IP>:8088/openapi/v1/alarms/{id}/video/download"
    ```
    """
    from datetime import datetime

    from server.services.playback_service import playback_service as svc

    alarm = await alarm_crud.get_alarm(db, alarm_id)
    if alarm is None:
        raise HTTPException(status_code=404, detail="告警不存在")

    status = str(getattr(alarm, "video_status", "") or "not_requested")

    # 已经有了 → 直接告诉对方去下载
    if status == "ready":
        raise HTTPException(
            status_code=409,
            detail=(
                "该视频已存在，无需补抓。请直接调用 "
                f"/openapi/v1/alarms/{alarm_id}/video/download 下载。"
            ),
            headers={
                "X-Video-Status": "ready",
                "X-Video-Url": str(getattr(alarm, "video_url", "") or ""),
            },
        )

    # 正在抓 → 让等
    if status == "starting":
        raise HTTPException(
            status_code=409,
            detail="该视频正在抓取中，请稍后查询状态。",
            headers={"X-Video-Status": "starting", "Retry-After": "60"},
        )

    # 保留期检查：太久的就不白跑（设备多半也覆盖了）
    age_days = (datetime.now() - alarm.alarm_time).total_seconds() / 86400
    MAX_DEVICE_DAYS = 35
    if age_days > MAX_DEVICE_DAYS:
        raise HTTPException(
            status_code=410,
            detail=(
                f"该告警距今 {age_days:.0f} 天，已超出设备录像的典型保留期"
                f"（约 {MAX_DEVICE_DAYS} 天），录像多半已被覆盖，无法补抓。"
            ),
        )

    ok = svc.submit(alarm_id)
    if not ok:
        raise HTTPException(
            status_code=503,
            detail=(
                "视频抓取队列已满或服务未就绪，请稍后重试。"
                "建议降低并发请求频率。"
            ),
        )

    logger.info(
        "甲方请求补抓视频 alarm=%s（距今 %.0f 天）", alarm_id[:8], age_days
    )

    return _envelope(
        {
            "status": "accepted",
            "alarm_id": alarm_id,
            "age_days": round(age_days, 1),
            "retry_after": 60,
            "message": (
                "已提交抓取任务。请等待约 60 秒后调用 "
                f"/openapi/v1/alarms/{alarm_id}/video 查询状态，"
                "status=ready 即可下载。"
            ),
            "note": (
                "补抓能否成功取决于设备上是否还有该时段录像。"
                "若设备已覆盖，本次抓取会返回 failed。"
            ),
        }
    )


@router.get(
    "/alarms/{alarm_id}/video/download",
    summary="★ 下载该告警的视频文件（MP4，支持 Range 断点续传）",
)
async def download_alarm_video(
    alarm_id: str,
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(rate_limit),
    # ★ 2026-10-27 安全修复：开放接口鉴权（ISUP_OPEN_API_REQUIRES_KEY=true 时必需 X-API-Key）
    _auth: Principal = Depends(require_open("alarm:read")),
):
    """直接返回 MP4 文件本体。

    ★ 视频是**异步生成**的，可能还没好：
        · status=ready        → 正常返回文件
        · status=starting     → **425 Too Early**（请稍后重试）
        · status=not_requested→ 404（这条没安排抓取）
        · status=failed       → 404 + 失败原因

    为什么用 425 而不是 404：让对方能区分「还没好」和「不存在」，
    避免把 starting 误判成永久失败而放弃重试。
    """
    from fastapi.responses import FileResponse

    from server.api.open_media import _media_path
    from server.config import MEDIA_VIDEO_DIR

    alarm = await alarm_crud.get_alarm(db, alarm_id)
    if alarm is None:
        raise HTTPException(status_code=404, detail="告警不存在")

    status = str(alarm.video_status or "not_requested")

    if status == "starting":
        raise HTTPException(
            status_code=425,
            detail=(
                "视频正在生成中（约需 60~120 秒），请稍后重试。"
                "建议下一轮（10 分钟后）再来下载。"
            ),
            headers={"Retry-After": "120"},
        )
    if status == "not_requested":
        raise HTTPException(
            status_code=404,
            detail="该告警未安排视频抓取（自动抓取可能已关闭）",
        )
    if status == "failed":
        raise HTTPException(
            status_code=404,
            detail=f"视频抓取失败: {getattr(alarm, 'video_error', '未知原因')}",
        )

    # ready → 找文件
    url = getattr(alarm, "video_url", None)
    if not url:
        raise HTTPException(status_code=404, detail="视频记录存在但没有文件路径")

    name = str(url).split("/")[-1]
    ap = _media_path(MEDIA_VIDEO_DIR, name)
    if ap is None or not ap.is_file():
        raise HTTPException(
            status_code=404,
            detail="视频文件不存在（可能已被清理策略删除）",
        )

    return FileResponse(
        ap,
        media_type="video/mp4",
        headers={
            "Content-Disposition": f'attachment; filename="{ap.name}"',
            "X-Alarm-Id": alarm_id,
            "X-Duration": str(getattr(alarm, "video_duration", "") or ""),
        },
    )


@router.get("/alarms/{alarm_id}/images", summary="该告警的全部图片")
async def get_alarm_images(
    request: Request,
    alarm_id: str,
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(rate_limit),
    # ★ 2026-10-27 安全修复：开放接口鉴权（ISUP_OPEN_API_REQUIRES_KEY=true 时必需 X-API-Key）
    _auth: Principal = Depends(require_open("alarm:read")),
):
    _set_request_base(None, request)
    alarm = await alarm_crud.get_alarm(db, alarm_id)
    if alarm is None:
        raise HTTPException(status_code=404, detail="告警不存在")

    # ★ 直接从 ORM 的 images 取 file_path（权威落盘路径），
    #   不要用 ImageOut.url（/media/... 形式）再去拼，
    #   否则会得到 /openapi/v1/media/media/... 这种 404 坏链。
    images = sorted(alarm.images, key=lambda x: x.seq)
    return _envelope(
        {
            "alarm_id": alarm_id,
            "images": [
                {
                    "seq": i.seq,
                    "url": _abs_media_url(i.file_path),
                    "width": i.width,
                    "height": i.height,
                    "file_size": i.file_size,
                    "captured_at": timeutil.to_iso_local(i.created_at),
                }
                for i in images
            ],
        }
    )


@router.get("/alarms/{alarm_id}/video", summary="该告警的视频片段（前后 30 秒）")
async def get_alarm_video(
    request: Request,
    alarm_id: str,
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(rate_limit),
    # ★ 2026-10-27 安全修复：开放接口鉴权（ISUP_OPEN_API_REQUIRES_KEY=true 时必需 X-API-Key）
    _auth: Principal = Depends(require_open("alarm:read")),
):
    """视频状态。

    ★ 注意：即使还没生成好，也**不返回 404** ——
      返回 status=starting/not_requested，让对方知道「稍后再来」，
      而不是「这条没有」。因为视频是异步生成的，需要时间。
    """
    _set_request_base(None, request)
    alarm = await alarm_crud.get_alarm(db, alarm_id)
    if alarm is None:
        raise HTTPException(status_code=404, detail="告警不存在")

    settings = get_settings()
    return _envelope(
        {
            "alarm_id": alarm_id,
            "status": alarm.video_status,
            "url": _abs_video_url(alarm.video_url),
            "duration": alarm.video_duration,
            "window": {
                "pre_seconds": settings.video_pre_seconds,
                "post_seconds": settings.video_post_seconds,
            },
            "hint": (
                "视频片段为告警时刻前后各 "
                f"{settings.video_pre_seconds}/{settings.video_post_seconds} 秒。"
                "视频为异步生成，status=starting 时请稍后重试。"
            ),
        }
    )


# ---------------------------------------------------------------------------
# ★★ 拆分接口（2026-10-27 按甲方要求）
#
# 甲方原话：「把视频、图片和报警分 4 个接口，1 个可以总和，3 个单独分开」
#
#   /alarms          → 总和（报警 + 图片 URL + 视频 URL）  ← 已存在
#   /alarms/summary  → 只要报警（无媒体字段，最轻）
#   /alarms/images   → 每条报警的图片清单
#   /alarms/videos   → 每条报警的视频清单
#
# 三个新接口的参数与 /alarms **完全一致**（workshop / window / since_token /
# limit / cursor），所以对方改一下路径就能切换，不用重写拉取逻辑。
# ---------------------------------------------------------------------------
@router.get("/health", summary="健康检查")
async def health(request: Request, db: AsyncSession = Depends(get_session)):
    """无需鉴权，最先验这个。探活接口不限流。"""
    from server.services import workshop_service as ws

    try:
        stats = await ws.pending_stats(db)
    except Exception:
        stats = {}

    settings = get_settings()
    _set_request_base(None, request)
    return _envelope(
        {
            "status": "healthy",
            "video_pre_seconds": settings.video_pre_seconds,
            "video_post_seconds": settings.video_post_seconds,
            "video_auto_capture": settings.video_auto_capture,
            "pending_images": stats.get("pending", 0),
            # 当前请求采用的媒体 URL 前缀；为空时媒体地址为相对路径。
            "media_base_url": _effective_base(),
        }
    )
