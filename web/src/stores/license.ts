import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { licenseApi } from '@/api'
import type { LicenseInfo } from '@/types'

/**
 * ★ 软件授权状态（有效期 1 年）。
 *
 * 后端负责"拦截"（到期后业务接口一律 403），前端负责"告知与续期"：
 *   · 顶栏角标常显「剩余 X 个月」，不足 3 个月转橙、不足 1 个月转红；
 *   · 到期后整个界面换成「授权已到期」拦截页（全面停用的门面）；
 *   · 管理员可在拦截页 / 角标弹窗里输入授权码续期。
 *
 * 为什么还要挂两个全局事件：
 *   ① isup:license-expired —— 后端返回 403(license_expired) 时立刻切状态，
 *      不用等下一次轮询，正在操作的页面会马上变成拦截页；
 *   ② 定时刷新（10 分钟）—— 剩余天数/月数会随时间变化，
 *      长期开着的值守机不能靠"刷新页面"才更新。
 *
 * 状态未知（首次请求还没回来 / 网络失败）时**不拦**：
 * 安全系统的界面不能因为一次网络抖动就锁死。
 */
export const useLicense = defineStore('license', () => {
  const info = ref<LicenseInfo | null>(null)
  const loading = ref(false)
  const loaded = ref(false)

  /** 真正需要拦截：后端开着拦截 + 已到期 + 状态已知 */
  const blocked = computed(
    () => !!info.value && info.value.expired && info.value.enforced,
  )

  const daysLeft = computed(() => info.value?.days_left ?? 0)
  /** ★ 服务器当前时间（客户要报给供应商换续期码） */
  const serverNow = computed(() => info.value?.server_now ?? '')

  /** 顶栏角标文案：以「月」为主，最后一个月改用「天」（更有压迫感也更精确） */
  const label = computed(() => {
    const i = info.value
    if (!i) return ''
    if (i.expired) return '授权已到期'
    if (i.days_left <= 30) return `授权剩余 ${i.days_left} 天`
    return `授权剩余 ${Math.floor(i.days_left / 30)} 个月`
  })

  /**
   * ★ 角标文案（永远不为空）。
   *   曾经出现过"角标是个空胶囊、看不出剩下多久"的情况 —— 根因是旧包缓存，
   *   但界面自身也不该在数据没到手时显示空白：加载中/失败都要有话说。
   */
  const chipText = computed(() => {
    if (info.value) return label.value
    return loaded.value ? '授权信息不可用' : '授权…'
  })

  /** 到期日（YYYY-MM-DD） */
  const expireText = computed(() => info.value?.expires_on ?? '')

  /** 需要提醒（不足 3 个月）—— 界面出提醒条 */
  const shouldWarn = computed(
    () => !!info.value && !info.value.expired && info.value.days_left <= 90,
  )

  async function fetch() {
    loading.value = true
    try {
      info.value = await licenseApi.info()
      loaded.value = true
    } catch {
      /* 探测失败不改变现有状态，也绝不因网络抖动锁死界面 */
    } finally {
      loading.value = false
    }
  }

  async function renew(code: string) {
    const fresh = await licenseApi.renew(code)
    info.value = fresh
    loaded.value = true
    return fresh
  }

  /** 后端已拒绝业务请求（403 license_expired）→ 强制进入已到期状态 */
  function forceExpired() {
    if (info.value) {
      info.value = { ...info.value, expired: true, enforced: true, days_left: 0 }
    } else {
      info.value = {
        activated_at: null,
        expires_on: null,
        days_left: 0,
        expired: true,
        enforced: true,
        customer: '',
        server_now: '',
        server_window: '',
        window_minutes: 10,
        renew_hint: '授权已到期，请联系供应商获取续期码',
      }
    }
  }

  return {
    info, loading, loaded,
    blocked, daysLeft, serverNow, label, chipText, expireText, shouldWarn,
    fetch, renew, forceExpired,
  }
})
