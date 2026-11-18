/** 与后端 server/schemas.py 对应的 TS 类型。 */

export interface VideoInfo {
  /** ★ not_requested 表示「用户还没点，视频挂起中」 */
  status: 'not_requested' | 'starting' | 'ready' | 'failed' | 'unavailable'
  url: string | null
  duration: number | null
  provider: string | null
  /** ★ status=failed 时的原因（如「设备未在线」「该时段无录像」） */
  error?: string | null
}

export interface AlarmImage {
  id: number
  file_hash: string
  seq: number
  width: number | null
  height: number | null
  file_size: number | null
  linked_by: string | null
  url: string
  absolute_url: string
  thumbnail_url: string
  created_at: string | null
}

export interface AlarmBrief {
  id: string
  device_id: string
  channel: number
  alarm_type: number
  alarm_time: string
  status: 'awaiting_media' | 'complete' | 'expired' | 'media_expired'
  /** ★ 归属车间 code / 名字（多车间隔离） */
  workshop?: string | null
  workshop_name?: string | null
  image_count: number
  thumbnail_url: string | null
  video: VideoInfo
  /** ★ 业务类型文本：AIOP 告警为规则名（如「未穿防护服报警」） */
  type_text: string
  /** ★ 一句话摘要 */
  summary: string
  extra: {
    is_aiop?: boolean
    rule_name?: string
    mp_name?: string
    person_count?: number
    alarmed_count?: number
    channel_name?: string
    /** ★ 去重合并次数：同类告警在窗口内重复上报了多少次 */
    repeat_count?: number
  }
  /** ★ 媒体文件已被清理策略删除（显示占位，不再请求图片 URL，避免裂图） */
  media_expired: boolean
  media_expired_at: string | null
  /**
   * ★ 2026-10-26：本系统定位为**纯展示看板**，不再要求值守人员逐条点击
   * 「处理/未处理」。这两个字段后端仍然返回（外部开放 API 与历史数据兼容），
   * 但前端任何界面都不再展示，也不再提供任何处置入口。
   */
  handled: boolean
  handled_at: string | null
}

/** ★ 看板统计（侧边栏红点等仍在用） */
export interface AlarmStats {
  /** 今日报警总数 */
  today: number
  /** 未处理（全部未处理，不限今日）—— 纯展示看板不再使用，仅为接口兼容保留 */
  pending: number
  /** 已处理 —— 纯展示看板不再使用，仅为接口兼容保留 */
  handled: number
}

export interface AlarmDetail extends Omit<AlarmBrief, 'image_count' | 'thumbnail_url'> {
  content: Record<string, unknown> | null
  images: AlarmImage[]
  created_at: string | null
}

export interface VideoSession {
  id: string
  alarm_id: string
  status: VideoInfo['status']
  url: string | null
  error: string | null
  created_at: string | null
  expires_at: string | null
}

export interface Paged<T> {
  items: T[]
  next_cursor: string | null
  has_more: boolean
  /** ★ 总条数（offset 分页接口返回） */
  total?: number | null
}

export interface Device {
  device_id: string
  ip: string | null
  port: number | null
  online: boolean
  last_seen: string | null
}

export interface Principal {
  kind: string
  subject: string
  scopes: string[]
  workshops?: string[]
  superuser?: boolean
}

/** ★ 每日趋势点（看板条形图） */
export interface TrendPoint {
  date: string
  count: number
  /** 已处理数 —— 纯展示看板不再展示，保留字段兼容外部 API */
  handled: number
}

/** ★ 违规热点：某台相机的违规事件排行（看板「热点工位」用） */
export interface HotspotPoint {
  device_id: string
  channel: number
  /** 通道显示名（甲方在通道管理里配的名字，没配则回退 CH{n}） */
  channel_name: string
  workshop: string
  /** 归并后的违规事件数 */
  events: number
  /** 原始推送条数（对比 events 可看出设备刷屏程度） */
  records: number
  /** 占今日全部事件的比例（%） */
  share: number
  last_at: string | null
}

/** ★ 数据完整率：有图率低时，前面所有业务指标都不可信 */
export interface DataQuality {
  total: number
  with_image: number
  without_image: number
  /** 有抓拍图的比例（%），看板据此给出"数据是否可信"的判断 */
  with_image_pct: number
  unassigned: number
}

/** ★ 首页看板聚合数据（GET /api/alarms/dashboard） */
export interface Dashboard {
  today: number
  yesterday: number
  /** 未处理 / 已处理 —— 纯展示看板不再使用，保留字段兼容 */
  pending: number
  handled: number
  devices_online: number
  devices_total: number
  trend: TrendPoint[]
  /** ★ 各车间今日分布（多车间场景） */
  workshops: WorkshopStat[]
  /** ★ 今日 24 小时分布（00~23 共 24 格） */
  hourly: HourlyPoint[]
  /** ★ 今日已处理告警的平均处置时长（分钟）—— 纯展示看板不再使用 */
  avg_handle_minutes: number | null
  handled_today: number
  /** ★ 图片配对队列：待配对 / 孤儿 / 未指派车间 */
  pending_images: number
  orphan_images: number
  unassigned: number

  /* ---------- ★ 事件口径（看板主指标，2026-10-26 新增） ---------- */
  /** 今日归并后的「违规事件数」——同一工位窗口内多次推送算一次 */
  events_today: number
  /** 今日原始推送条数 —— 对比 events_today 可看出设备刷屏程度 */
  records_today: number
  /** 冗余倍数 records/events，>10 说明设备在刷屏，指标需谨慎解读 */
  repeat_ratio: number
  /** 事件归并窗口（秒），用于界面上说明统计口径 */
  event_window_seconds: number
  /** 今日涉及违规人次（事件内取人数峰值再求和） */
  people_today: number
  /** 今日含违规的事件数 */
  abnormal_events_today: number
  /** ★ 违规热点工位（按通道的事件数排行） */
  hotspots: HotspotPoint[]
  /** ★ 数据完整率 */
  data_quality: DataQuality | null
}

export interface HourlyPoint {
  hour: number
  count: number
}

/** ★ 软件授权状态（有效期 1 年，到期全面停用） */
export interface LicenseInfo {
  /** 激活时间（首次启动，以服务器时间为准） */
  activated_at: string | null
  /** 到期日 YYYY-MM-DD */
  expires_on: string | null
  /** 剩余天数（可为负） */
  days_left: number
  expired: boolean
  /** 是否开启"到期拦截" */
  enforced: boolean
  customer: string
  /**
   * ★★ 服务器当前时间——授权基准。
   * 到期后客户要把这个时间报给供应商，换一个 10 分钟有效的续期码。
   */
  server_now: string
  /** 服务器当前所在的 10 分钟窗口（便于对齐） */
  server_window: string
  /** 续期码有效窗口（分钟） */
  window_minutes: number
  /** 到期时给客户的提示文案 */
  renew_hint: string
}

export interface WorkshopStat {
  code: string
  name: string
  today: number
  pending: number
  channels: number
  channels_online: number
}

/** ★ 通道（摄像头）信息 —— 设备管理页 */
export interface ChannelDevice {
  id: number
  display_name: string | null
  channel_name: string | null
  /**
   * ★ 2026-10-26：真实通道号（1/2/3…）。
   * NVR 上多个通道可能同名（实测 CH3/CH4/CH5 都叫 "Camera 01"），
   * 只显示 channel_name 会让运维以为「同一摄像头重复列出」。
   */
  channel_no?: number | null
  workshop_code: string | null
  status: string
  enabled: boolean
  /** ★ null = 无法判定（父设备查不到，多为历史残留），显示「未知」而非「离线」 */
  online: boolean | null
  /** ★ 父设备 ID 与「设备表里查无此设备」标记（排查用） */
  parent_device?: string | null
  parent_missing?: boolean
  alarm_count: number
  last_seen: string | null
  last_alarm_at: string | null
  /** ★ admin 通道列表附带：最近一张告警图（看画面认车间） */
  sample_image_url?: string | null
  sample_image_count?: number
  /**
   * ★★ 2026-10-26 新增：摄像头自己的信息（来自 NVR 的 ISAPI）
   *
   * 为什么需要：通道在线状态不能直接抄父设备（NVR）——
   * NVR 在线时它下面 5 个通道里可能只有 1 个真接了摄像头。
   * 用这些字段才能看出「哪个摄像头真的在用」，也是后续做
   * 「设备自定义/绑定」的基础。
   */
  camera_ip?: string | null
  camera_model?: string | null
  camera_serial?: string | null
  /** true = 查到了摄像头真实状态；false = 查询失败，online 退回父设备状态 */
  camera_online_known?: boolean
}

/** ★ 通道样本图 */
export interface ChannelSample {
  url: string
  alarm_time: string | null
  type_text: string
}

/** ★ 车间 */
export interface Workshop {
  code: string
  name: string
  description: string | null
  sort_order: number
  enabled: boolean
}

/** ★ 账号（管理页） */
export interface UserInfo {
  id: number
  username: string
  display_name: string | null
  role: string
  is_superuser: boolean
  enabled: boolean
  workshops: string[]
}
