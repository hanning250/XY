import { onUnmounted, ref } from 'vue'
import type { AlarmBrief } from '@/types'

/**
 * ★ 告警实时推送。
 *
 * 要点：
 *   1. 自动重连（指数退避，上限 30s）
 *   2. 心跳保活
 *   3. 重连后触发一次补拉 —— 断线期间的告警不能丢
 *   4. token 走 query（WS 无法自定义头）
 *   5. 用 connId 忽略旧连接的迟到回调，避免「新连接已通、旧 onclose 又把状态打成断开」
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
  /** connecting = 首次连接或重连进行中（与 connected 互斥展示） */
  const connecting = ref(false)
  let ws: WebSocket | null = null
  let retry = 0
  let heartbeat: number | null = null
  let closedByUser = false
  let reconnectTimer: number | null = null
  /** 每次发起连接递增；迟到的旧 socket 事件一律忽略 */
  let connId = 0

  function url(): string {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const token = localStorage.getItem('isup_token') || ''
    const q = token ? `?token=${encodeURIComponent(token)}` : ''
    return `${proto}//${location.host}/api/ws/alarms${q}`
  }

  function dropSocket(socket: WebSocket | null) {
    if (!socket) return
    socket.onopen = null
    socket.onmessage = null
    socket.onerror = null
    socket.onclose = null
    try {
      socket.close()
    } catch {
      /* ignore */
    }
  }

  function connect() {
    if (closedByUser) return

    dropSocket(ws)
    ws = null

    const id = ++connId
    connecting.value = true

    try {
      ws = new WebSocket(url())
    } catch {
      if (id !== connId) return
      connected.value = false
      connecting.value = true
      scheduleReconnect()
      return
    }

    ws.onopen = () => {
      if (id !== connId) return
      const wasDown = retry > 0
      connected.value = true
      connecting.value = false
      retry = 0
      startHeartbeat()
      if (wasDown && onReconnect) onReconnect()
    }

    ws.onmessage = (ev) => {
      if (id !== connId) return
      try {
        const msg = JSON.parse(ev.data)
        if (msg.type === 'alarm' && msg.data) {
          onAlarm(msg.data as AlarmBrief)
        } else if (msg.type === 'alarm_updated' && msg.data) {
          const payload = msg.data as AlarmBrief
          if (handlers?.onUpdated) handlers.onUpdated(payload)
          else onAlarm(payload)
        } else if (msg.type === 'alarm_deleted' && msg.data) {
          const ids = (msg.data.ids as string[]) || []
          if (handlers?.onDeleted) handlers.onDeleted(ids)
        }
      } catch {
        /* 忽略非 JSON 消息 */
      }
    }

    // onerror 往往只是 onclose 的前兆，不要单独把状态打成断开，
    // 否则会出现「其实还在连 / 马上重连」时右下角先闪红。
    ws.onerror = () => {
      /* onclose 统一收口 */
    }

    ws.onclose = () => {
      if (id !== connId) return
      connected.value = false
      connecting.value = true
      stopHeartbeat()
      scheduleReconnect()
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
    dropSocket(ws)
    ws = null
    connId += 1
    connected.value = false
    connecting.value = false
  }

  onUnmounted(close)

  return { connected, connecting, connect, close }
}
