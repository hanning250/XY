import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { alarmApi } from '@/api'
import { flashMs } from '@/composables/useAlarmTiming'
import type { AlarmBrief, AlarmDetail, AlarmStats } from '@/types'

/** 告警告警类型映射。可后续从后端下发。 */
export const ALARM_TYPE_TEXT: Record<number, string> = {
  13: '人脸抓拍',
  1: '移动侦测',
  2: '视频遮挡',
  3: '视频丢失',
  5: '区域入侵',
  6: '越界侦测',
  7: '进入区域',
  8: '离开区域',
  9: '徘徊侦测',
  10: '人员聚集',
  11: '快速移动',
  12: '停车侦测',
  15: '物品遗留',
  16: '物品拿取',
}

export function alarmTypeText(t: number): string {
  return ALARM_TYPE_TEXT[t] ?? `告警(${t})`
}

export const useAlarmStore = defineStore('alarm', () => {
  const items = ref<AlarmBrief[]>([])
  const total = ref(0)
  const loading = ref(false)
  const page = ref(1)
  // ★ 甲方要求可选 20/50/100；默认 20，并持久化到 localStorage
  const PAGE_SIZE_KEY = 'isup.alarm.pageSize'
  const ALLOWED_SIZES = [20, 50, 100] as const
  function _loadSize(): number {
    try {
      const n = Number(localStorage.getItem(PAGE_SIZE_KEY))
      if ((ALLOWED_SIZES as readonly number[]).includes(n)) return n
    } catch { /* ignore */ }
    return 20
  }
  const size = ref(_loadSize())
  function setPageSize(n: number) {
    if (!(ALLOWED_SIZES as readonly number[]).includes(n)) return
    size.value = n
    try { localStorage.setItem(PAGE_SIZE_KEY, String(n)) } catch { /* ignore */ }
  }

  const filters = ref({
    device_id: '' as string,
    alarm_type: undefined as number | undefined,
    workshop: '' as string,
    rule_name: '' as string,
    start: '' as string,
    end: '' as string,
    /**
     * ★ 抓拍图筛选，默认 true = 只看有图。
     *
     * 图片靠 ISUP 同连接的到达顺序配对，历史上有配不到图的记录
     * （丢包/乱序/早期版本）。这类记录在值守界面上就是一行"没有画面"的
     * 占位，属于噪声，所以默认隐藏；需要排查时切成「全部 / 仅无图」。
     */
    has_image: true as boolean | undefined,
  })

  const detail = ref<AlarmDetail | null>(null)
  const detailLoading = ref(false)

  /** ★ 看板统计（顶部三张卡片 + 左侧红点） */
  const stats = ref<AlarmStats>({ today: 0, pending: 0, handled: 0 })

  /**
   * ★ 新异常报警的"闪动"标记（id → 到期时间戳）。
   *
   * 现场一屏十几条报警，"哪条是刚出的"必须一眼看到：标记后
   * 列表状态框、实况画面状态框一起闪动（见 isFlashing）。
   * 计时放在 store 里 —— 多个页面共用同一份状态，不会各闪各的。
   *
   * ★ 时长改为可配置（默认 15 秒，现场在顶栏设置里调，见 useAlarmTiming）。
   *   FLASH_MS 保留为「当前值的 getter」，不再是写死的常量。
   */
  const FLASH_MS = computed(() => flashMs.value)
  const flashing = ref<Record<string, number>>({})

  function markFlash(id: string, ms: number = flashMs.value) {
    if (ms <= 0) return
    flashing.value = { ...flashing.value, [id]: Date.now() + ms }
    window.setTimeout(() => {
      if (flashing.value[id] === undefined) return
      const next = { ...flashing.value }
      delete next[id]
      flashing.value = next
    }, ms)
  }

  function isFlashing(id: string): boolean {
    return flashing.value[id] !== undefined
  }

  /** ★ 左侧红点 = 未处理数 */
  const pendingCount = computed(() => stats.value.pending)

  async function fetchStats() {
    try {
      stats.value = await alarmApi.stats()
    } catch {
      /* 统计失败不影响主流程 */
    }
  }

  async function fetchList() {
    /** 首次加载才有遮罩；已有数据时的静默刷新不触发 loading（返回列表时不再闪一下） */
    if (items.value.length === 0) loading.value = true
    try {
      const params: Record<string, unknown> = { page: page.value, size: size.value }
      if (filters.value.device_id) params.device_id = filters.value.device_id
      if (filters.value.alarm_type !== undefined) params.alarm_type = filters.value.alarm_type
      if (filters.value.workshop) params.workshop = filters.value.workshop
      if (filters.value.rule_name) params.rule_name = filters.value.rule_name
      if (filters.value.start) params.start = filters.value.start
      if (filters.value.end) params.end = filters.value.end
      // ★ 默认只看有抓拍图的告警（undefined=全部，要看无图记录由用户显式切换）
      if (filters.value.has_image !== undefined) params.has_image = filters.value.has_image

      const data = await alarmApi.list(params)
      items.value = data.items ?? []
      // ★ 后端已返回真实 total；取不到时才退回按页码估算
      total.value =
        typeof data.total === 'number'
          ? data.total
          : data.has_more
            ? page.value * size.value + 1
            : (page.value - 1) * size.value + items.value.length
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id: string) {
    detailLoading.value = true
    try {
      detail.value = await alarmApi.detail(id)
      return detail.value
    } finally {
      detailLoading.value = false
    }
  }

  async function refreshOne(id: string) {
    const fresh = await alarmApi.detail(id)
    const idx = items.value.findIndex((a) => a.id === id)
    if (idx >= 0) {
      items.value[idx] = {
        ...items.value[idx],
        video: fresh.video,
        status: fresh.status,
      }
    }
    if (detail.value?.id === id) detail.value = fresh
    return fresh
  }

  /**
   * ★ WS 推送来的新告警：按 alarm_time 插入到正确位置（而不是无脑 unshift）。
   *
   * 为什么不能 unshift（2026-10-23 现场反馈「新报警把排序打乱」）：
   *
   *     录像机转发存在 20~30 秒延迟 —— 报文里的 alarm_time 是设备侧的
   *     抓拍时刻，而 WS 推送是按平台收到的时刻。于是会出现：
   *
   *         先收到  A（alarm_time 10:56:49）
   *         后收到  B（alarm_time 10:56:27）  ← 实际更早，只是晚到
   *
   *     unshift 会把 B 插到 A 上面 → 列表看起来「倒序错乱」。
   *     列表按 alarm_time 降序，B 应该排在 A 后面。
   *
   * 所以这里做**有序插入**：找到第一个 alarm_time 比自己小的位置插进去。
   * 后端返回的顺序本来就是 alarm_time desc，与这里保持一致。
   */
  function prepend(alarm: AlarmBrief) {
    const idx = items.value.findIndex((a) => a.id === alarm.id)
    if (idx >= 0) {
      // 已存在则原地更新（聚合状态可能从 awaiting_media 变成 complete）
      items.value[idx] = alarm
      return
    }

    // 找到第一个「时间比我早」的位置
    const t = new Date(alarm.alarm_time).getTime()
    let at = items.value.length
    for (let i = 0; i < items.value.length; i += 1) {
      const cur = new Date(items.value[i].alarm_time).getTime()
      // 时间解析失败（NaN）时不参与比较，避免把新告警插到奇怪的位置
      if (!Number.isNaN(cur) && cur < t) {
        at = i
        break
      }
    }
    items.value.splice(at, 0, alarm)

    // 防御：列表不应无限增长（后端也分页，这里只保留前 200 条）
    if (items.value.length > 200) {
      items.value.length = 200
    }
  }

  function resetFilters() {
    filters.value = {
      device_id: '',
      alarm_type: undefined,
      workshop: '',
      rule_name: '',
      start: '',
      end: '',
      has_image: true,
    }
    page.value = 1
  }

  /** ★ 删除单条告警（后端会连磁盘文件一起删） */
  async function removeOne(id: string) {
    await alarmApi.remove(id)
    items.value = items.value.filter((a) => a.id !== id)
    if (detail.value?.id === id) detail.value = null
    total.value = Math.max(0, total.value - 1)
  }

  /** ★ 批量删除 */
  async function removeMany(ids: string[]) {
    const res = await alarmApi.batchRemove(ids)
    const deleted: string[] = res?.data?.deleted_ids ?? ids
    const set = new Set(deleted)
    items.value = items.value.filter((a) => !set.has(a.id))
    if (detail.value && set.has(detail.value.id)) detail.value = null
    total.value = Math.max(0, total.value - deleted.length)
    return deleted
  }

  /** ★ 请求抓取真实回放（后台执行，完成后由 WS 推送更新） */
  async function requestPlayback(id: string) {
    await alarmApi.requestPlayback(id)
    // 立刻把本地状态置为 starting，给用户反馈
    const idx = items.value.findIndex((a) => a.id === id)
    if (idx >= 0) {
      items.value[idx] = {
        ...items.value[idx],
        video: { ...items.value[idx].video, status: 'starting', url: null },
      }
    }
  }

  /** ★ 从 WS 推送的消息里移除告警 */
  function removeByIds(ids: string[]) {
    const set = new Set(ids)
    items.value = items.value.filter((a) => !set.has(a.id))
    if (detail.value && set.has(detail.value.id)) detail.value = null
  }

  return {
    items, total, loading, page, size, setPageSize, ALLOWED_SIZES, filters,
    detail, detailLoading, stats, pendingCount,
    flashing, markFlash, isFlashing, FLASH_MS,
    fetchList, fetchDetail, refreshOne, prepend, resetFilters, fetchStats,
    removeOne, removeMany, requestPlayback, removeByIds,
  }
})
