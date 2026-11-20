import axios from 'axios'
import { ElMessage } from 'element-plus'

/**
 * ★ 鉴权预留（docs §5）：
 *   从第一天就统一注入 Authorization 头（现在为空），
 *   将来接入登录注册时只需 tokenStore 里有值，业务代码零改动。
 */
export const tokenStore = {
  get(): string {
    return localStorage.getItem('isup_token') || ''
  },
  set(token: string) {
    localStorage.setItem('isup_token', token)
  },
  clear() {
    localStorage.removeItem('isup_token')
  },
}

/**
 * ★ 媒体 URL（2026-XX 安全审查：token 不再进 URL）。
 *
 * 原来 <img>/<video> 因为带不了 Authorization 头，把 JWT 拼进
 * ?token= —— 会进浏览器历史 / Referer / 代理日志。
 * 现在登录时后端同时签发 HttpOnly Cookie（isup_media_token），
 * 浏览器对同源媒体请求自动携带，前端直接用原始 URL 即可。
 *
 * withToken 保留为兼容别名：老模板无需改动，行为变为原样返回。
 */
export function withToken(url: string | null | undefined): string {
  return url || ''
}

const http = axios.create({
  baseURL: '/',
  timeout: 20000,
  // ★ 登录接口签发的 HttpOnly Cookie 随同源请求自动携带（媒体鉴权用）
  withCredentials: true,
})

http.interceptors.request.use((config) => {
  const token = tokenStore.get()
  // 现在 token 为空，将来有值就自动带上 —— 不需要改任何调用点
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/**
 * ★ 把后端各种形态的 detail 统一成一句可读文本。
 *
 * 为什么需要：FastAPI 的 422 校验错误里 detail 是**数组**
 * （[{loc, msg, type}, ...]），直接丢给 ElMessage 会显示
 * "[object Object]" —— 用户完全看不懂发生了什么。
 */
function readableDetail(detail: unknown, fallback: string): string {
  if (!detail) return fallback
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const parts = detail
      .map((d) => {
        if (typeof d === 'string') return d
        if (d && typeof d === 'object') {
          const o = d as { msg?: string; loc?: unknown[] }
          const where = Array.isArray(o.loc) ? o.loc.filter((x) => x !== 'body').join('.') : ''
          return where ? `${where}: ${o.msg || ''}` : o.msg || ''
        }
        return String(d)
      })
      .filter(Boolean)
    return parts.length ? parts.join('；') : fallback
  }
  if (typeof detail === 'object') {
    const o = detail as { message?: string; msg?: string }
    return o.message || o.msg || fallback
  }
  return String(detail)
}

http.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const status = error?.response?.status
    const detail = error?.response?.data?.detail

    // ★ 探测类请求失败不弹提示：能力探测的 404/405 是预期结果，不该打扰用户。
    if (error?.config?.headers?.['X-Silent-Probe']) {
      return Promise.reject(error)
    }

    if (status === 401) {
      // ★ token 失效 / 未登录 → 清理并回到登录页
      tokenStore.clear()
      window.dispatchEvent(new CustomEvent('isup:unauthorized'))
      ElMessage.warning('登录已失效，请重新登录')
    } else if (status === 403) {
      // ★ 授权到期（后端 license 中间件的统一拒绝）：这里不弹零散提示，
      //   广播事件让授权 store 立刻切到「已到期」，前端整体换成拦截页。
      if (error?.response?.data?.code === 'license_expired') {
        window.dispatchEvent(new CustomEvent('isup:license-expired'))
      } else {
        // ★ 车间权限不足（例如未分配车间）
        ElMessage.error(readableDetail(detail, '没有权限访问该数据'))
      }
    } else if (status === 409) {
      ElMessage.warning(readableDetail(detail, '当前状态不允许该操作'))
    } else if (status === 429) {
      ElMessage.warning(readableDetail(detail, '操作过于频繁，请稍后重试'))
    } else if (status === 501) {
      ElMessage.info(readableDetail(detail, '该功能未启用'))
    } else if (status === 404) {
      ElMessage.warning(readableDetail(detail, '资源不存在'))
    } else if (detail) {
      ElMessage.error(readableDetail(detail, '请求失败'))
    } else {
      ElMessage.error(error.message || '请求失败')
    }
    return Promise.reject(error)
  },
)

export default http

// ---------------------------------------------------------------- 内部 API
export const alarmApi = {
  list(params: Record<string, unknown> = {}) {
    return http.get('/api/alarms', { params }).then((r) => r.data)
  },
  ruleNames() {
    return http.get('/api/alarms/rule-names').then((r) => r.data as { items: string[] })
  },
  byWorkshopRule(params: Record<string, unknown> = {}) {
    return http
      .get('/api/stats/by-workshop-rule', { params })
      .then((r) => r.data as {
        items: Array<{
          workshop: string | null
          workshop_name?: string
          rule_name: string
          alarm_count: number
          person_sum: number
          alarmed_sum: number
        }>
        note?: string
      })
  },
  detail(id: string) {
    return http.get(`/api/alarms/${id}`).then((r) => r.data)
  },
  /** ★ 只有用户点击「查看视频」才调用这个 */
  createVideoSession(alarmId: string, body: Record<string, unknown> = {}) {
    return http.post(`/api/alarms/${alarmId}/video-session`, body).then((r) => r.data)
  },
  /** ★ 从设备抓取该告警时段的真实录像（PS→MP4 转码，后台执行） */
  requestPlayback(alarmId: string) {
    return http.post(`/api/alarms/${alarmId}/playback`).then((r) => r.data)
  },
  /** ★ 删除告警（连磁盘上的图片/视频一起删） */
  remove(alarmId: string) {
    return http.delete(`/api/alarms/${alarmId}`).then((r) => r.data)
  },
  /** ★ 批量删除（连图片/视频磁盘文件） */
  batchRemove(ids: string[]) {
    return http
      .post('/api/alarms/batch-delete', { ids }, { timeout: 120000 })
      .then((r) => r.data)
  },
  /** ★ 按当前筛选清空告警（连图片/视频磁盘文件） */
  batchRemoveAll(filters: Record<string, unknown> = {}) {
    return http
      .post(
        '/api/alarms/batch-delete',
        { ids: [], all: true, ...filters },
        { timeout: 120000 },
      )
      .then((r) => r.data)
  },
  /** ★ 统计（今日条数）—— 纯展示看板只用到 today */
  stats() {
    return http.get('/api/alarms/stats').then((r) => r.data)
  },
  /** ★ 首页看板聚合（统计卡 + 每日趋势 + 设备在线，按车间隔离） */
  dashboard(days = 7) {
    return http
      .get('/api/alarms/dashboard', { params: { days } })
      .then((r) => r.data)
  },
  /* ★ 2026-10-26：`batchHandled` / `setHandled` 两个处置接口已从前端移除 ——
     本系统是纯展示看板，不承担"谁处理了"的流程职责。
     后端 /api/alarms/{id}/handled、/api/alarms/batch-handled 仍保留，
     外部开放 API 与既有集成不受影响。 */
  pollVideoSession(sessionId: string) {
    return http.get(`/api/alarms/video-sessions/${sessionId}`).then((r) => r.data)
  },
  closeVideoSession(sessionId: string) {
    return http.delete(`/api/alarms/video-sessions/${sessionId}`).then((r) => r.data)
  },
}

export const deviceApi = {
  list() {
    return http.get('/api/devices').then((r) => r.data)
  },
  /** ★ 通道列表（按车间隔离；子账号只看到本车间的摄像头） */
  channels() {
    return http.get('/api/devices/channels').then((r) => r.data)
  },
}

export const authApi = {
  me() {
    return http.get('/api/auth/me').then((r) => r.data)
  },
  config() {
    return http.get('/api/auth/config').then((r) => r.data)
  },
  login(username: string, password: string) {
    return http.post('/api/auth/login', { username, password }).then((r) => r.data)
  },
  /** ★ 修改自己的密码（成功后需重新登录） */
  changePassword(oldPassword: string, newPassword: string) {
    return http
      .put('/api/auth/password', {
        old_password: oldPassword,
        new_password: newPassword,
      })
      .then((r) => r.data)
  },
}

/**
 * ★ 车间 / 通道 / 账号管理（需管理员权限）。
 */
export const adminApi = {
  workshops() {
    return http.get('/api/admin/workshops').then((r) => r.data)
  },
  /** ★ 新建 / 更新车间 */
  upsertWorkshop(body: {
    code: string
    name: string
    description?: string | null
    sort_order?: number
  }) {
    return http.post('/api/admin/workshops', body).then((r) => r.data)
  },
  /** ★ 修改车间名字（只动 name，不动 code） */
  renameWorkshop(code: string, name: string) {
    return http
      .put(`/api/admin/workshops/${encodeURIComponent(code)}/name`, null, {
        params: { name },
      })
      .then((r) => r.data)
  },
  deleteWorkshop(code: string) {
    return http
      .delete(`/api/admin/workshops/${encodeURIComponent(code)}`)
      .then((r) => r.data)
  },
  /** ★ 通道列表 —— 含「待指派」的，admin 据此分配车间 */
  channels(status?: string) {
    return http
      .get('/api/admin/channels', { params: status ? { status } : {} })
      .then((r) => r.data)
  },
  /** ★ 把通道指派给车间（后端会自动回填历史告警） */
  assignChannel(channelId: number, workshopCode: string | null, displayName = '') {
    return http
      .post(`/api/admin/channels/${channelId}/assign`, {
        workshop_code: workshopCode,
        display_name: displayName,
      })
      .then((r) => r.data)
  },
  /** ★ 通道改名（如「1号车间东侧摄像头」） */
  renameChannel(channelId: number, displayName: string) {
    return http
      .patch(`/api/admin/channels/${channelId}`, { display_name: displayName })
      .then((r) => r.data)
  },
  users() {
    return http.get('/api/admin/users').then((r) => r.data)
  },
  createUser(body: {
    username: string
    password: string
    display_name?: string
    superuser?: boolean
    workshops?: string[]
  }) {
    return http.post('/api/admin/users', body).then((r) => r.data)
  },
  /** ★ 编辑账号（资料/密码/启停/车间授权，只传需要改的字段） */
  updateUser(
    userId: number,
    body: {
      display_name?: string
      password?: string
      enabled?: boolean
      superuser?: boolean
      workshops?: string[]
    },
  ) {
    return http.put(`/api/admin/users/${userId}`, body).then((r) => r.data)
  },
  deleteUser(userId: number) {
    return http.delete(`/api/admin/users/${userId}`).then((r) => r.data)
  },
}

// ---------------------------------------------------------------- ★ 软件授权
export const licenseApi = {
  /** 查授权状态（无需登录：拦截页与登录页都要用） */
  info() {
    return http.get('/api/license').then((r) => r.data)
  },
  /** 用授权码续期（仅管理员；后端同样校验 admin） */
  renew(code: string) {
    return http.post('/api/license/renew', { code }).then((r) => r.data)
  },
}
