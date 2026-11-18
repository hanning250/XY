import { onUnmounted, ref } from 'vue'
import type { AlarmBrief } from '@/types'

/**
 * ★ 告警实时推送。
 *
 * 要点：
 *   1. 自动重连（指数退避，上限 30s）
 *   2. 心跳保活
 *   3. 重连后触发一次补拉 —— 断线期间的告警不能丢
 *   4. ★ 预留：将来把 token 放到 query 上（WS 无法自定义头）
 */
export function useAlarmSocket(
  onAlarm: (a: AlarmBrief) => void,
  onReconnect?: () => void,
  handlers?: {
    /** ★ 告警被删除（可能是别的客户端删的） */
    onDeleted?: (ids: string[]) => void
    /** ★ 告警被更新（例如回放抓取完成） */
    onUpdated?: (a: AlarmBrief) => void
  },
) {
  const connected = ref(false)
  let ws: WebSocket | null = null
  let retry = 0
  let heartbeat: number | null = null
  let closedByUser = false
  let reconnectTimer: number | null = null

  function url(): string {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const token = localStorage.getItem('isup_token') || ''
    // ⚠️ WS 无法自定义头，也无法依赖 HttpOnly Cookie 之外的方式；
    //    token 只能走 query（浏览器历史风险可接受：WS URL 不进收藏/日志的场景有限）。
    //    后端对该 token 做与 HTTP 相同的停用/改密吊销校验。
    const q = token ? `?token=${encodeURIComponent(token)}` : ''
    return `${proto}//${location.host}/api/ws/alarms${q}`
  }

  function connect() {
    if (closedByUser) return
    try {
      ws = new WebSocket(url())
    } catch {
      scheduleReconnect()
      return
    }

    ws.onopen = () => {
      const wasDown = retry > 0
      connected.value = true
      retry = 0
      startHeartbeat()
      // 断线重连后补拉，避免漏掉期间的告警
      if (wasDown && onReconnect) onReconnect()
    }

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        if (msg.type === 'alarm' && msg.data) {
          onAlarm(msg.data as AlarmBrief)
        } else if (msg.type === 'alarm_updated' && msg.data) {
          // ★ 回放抓取完成等状态变更
          const payload = msg.data as AlarmBrief
          if (handlers?.onUpdated) handlers.onUpdated(payload)
          else onAlarm(payload)
        } else if (msg.type === 'alarm_deleted' && msg.data) {
          // ★ 别的客户端删除了告警，本地列表也要移除
          const ids = (msg.data.ids as string[]) || []
          if (handlers?.onDeleted) handlers.onDeleted(ids)
        }
      } catch {
        /* 忽略非 JSON 消息 */
      }
    }

    ws.onclose = () => {
      connected.value = false
      stopHeartbeat()
      scheduleReconnect()
    }

    ws.onerror = () => {
      connected.value = false
    }
  }

  function scheduleReconnect() {
    if (closedByUser || reconnectTimer !== null) return
    retry += 1
    const delay = Math.min(1000 * 2 ** Math.min(retry, 5), 30000)
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null
      connect()
    }, delay)
  }

  function startHeartbeat() {
    stopHeartbeat()
    heartbeat = window.setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) ws.send('ping')
    }, 25000)
  }

  function stopHeartbeat() {
    if (heartbeat !== null) {
      clearInterval(heartbeat)
      heartbeat = null
    }
  }

  function close() {
    closedByUser = true
    stopHeartbeat()
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    ws?.close()
    ws = null
    connected.value = false
  }

  onUnmounted(close)

  return { connected, connect, close }
}
