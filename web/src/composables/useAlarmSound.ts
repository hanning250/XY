/**
 * ★ 异常声音报警 —— 工业现场值守的"耳朵"。
 *
 * 设计要点（踩过的坑都在这）：
 *   · 不依赖音频文件：现场部署常把 dist 拷来拷去，丢一个 mp3 就哑了；
 *     这里用 WebAudio 现场合成，零资源、零依赖。
 *   · 浏览器自动播放策略：AudioContext 必须由**用户手势**唤醒。
 *     所以模块加载时就挂一次性 pointerdown/keydown 监听做解锁，
 *     登录那一下点击就把它唤醒了。
 *   · 音色：三角波双音（B5→F#5），穿透车间噪声但不刺耳；
 *     增益带指数包络，避免爆音"咔哒"声。
 *   · 响铃时长可配（默认 15 秒），与状态框频闪同步（见 useAlarmTiming）：
 *     双音一循环 1.2 秒，中间留 0.35 秒间隙，共约 9 个循环。
 *     整段音频一次性排进 WebAudio 时间轴（不靠 JS 定时器逐个触发，
 *     后台标签页定时器被节流也不会忽快忽慢）。
 *   · 可随时静音：统一走 master 增益节点淡出，人工「标记已处理」
 *     或关掉开关都立即停声 —— 报警音必须能被随时掐断。
 *   · 开关状态全局单例（顶栏一个按钮，各页面共用），localStorage 记住。
 */
import { ref } from 'vue'
import { soundMs } from '@/composables/useAlarmTiming'

const KEY = 'isup_alarm_sound'
/** 默认开：现场值守最怕漏掉异常 */
export const soundEnabled = ref(localStorage.getItem(KEY) !== '0')

/**
 * ★ 响铃时长：改为可配置（默认 15 秒）。
 *
 * 原来这里写死 `RING_MS = 15000`，现在由 useAlarmTiming 统一管理 ——
 * 现场在顶栏「报警提醒设置」里拖动滑块即可，**立即生效，无需重启**。
 * 保留 RING_MS 这个名字作为「当前值」的导出，方便别处（全屏浮层）引用。
 */
export const RING_MS = soundMs

/** ★ 是否正在响铃（顶栏喇叭据此脉动）——
 *  现场看不到"声音还剩多久"，就让按钮跟着一起闪，
 *  顺带也是个自检：闪多久 = 响多久。 */
export const soundRinging = ref(false)

/** 一个双音循环的周期（含间隙）：988Hz 短音 + 740Hz 长音 + 停顿。
 *  1500ms × 10 个循环 ≈ 14 秒发声，加上首尾余量正好铺满默认 15 秒窗口 */
const CYCLE_MS = 1500

let ctx: AudioContext | null = null
/** 总线增益：所有音都经它输出，静音只需把它拉到 0 */
let master: GainNode | null = null
let ringTimer: number | null = null
let restoreTimer: number | null = null

function ensureCtx(): AudioContext | null {
  if (typeof window === 'undefined') return null
  const AC: typeof AudioContext | undefined =
    window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
  if (!AC) return null
  if (!ctx) {
    try {
      ctx = new AC()
    } catch {
      return null
    }
  }
  return ctx
}

function masterNode(c: AudioContext): GainNode {
  if (!master) {
    master = c.createGain()
    master.gain.value = 1
    master.connect(c.destination)
  }
  return master
}

/** 用户首次交互时解锁音频（浏览器策略要求） */
function unlock() {
  const c = ensureCtx()
  if (c && c.state === 'suspended') void c.resume()
}

if (typeof window !== 'undefined') {
  window.addEventListener('pointerdown', unlock, { once: true, passive: true })
  window.addEventListener('keydown', unlock, { once: true, passive: true })
}

/** 单个音符：三角波 + 指数包络，输出到总线 */
function tone(c: AudioContext, at: number, freq: number, dur: number, vol: number) {
  const osc = c.createOscillator()
  const gain = c.createGain()
  osc.type = 'triangle'
  osc.frequency.setValueAtTime(freq, at)
  gain.gain.setValueAtTime(0.0001, at)
  gain.gain.exponentialRampToValueAtTime(vol, at + 0.02)
  gain.gain.exponentialRampToValueAtTime(0.0001, at + dur)
  osc.connect(gain)
  gain.connect(masterNode(c))
  osc.start(at)
  osc.stop(at + dur + 0.03)
}

/** 总线淡出，立即静音（已排程的音符还在响，但听不到了） */
function fadeOut(fade = 0.1) {
  const c = ctx
  if (!c || !master) return
  const now = c.currentTime
  master.gain.cancelScheduledValues(now)
  master.gain.setValueAtTime(master.gain.value, now)
  master.gain.linearRampToValueAtTime(0.0001, now + fade)
  // 淡出完成后把增益复位，下一次报警才能正常出声
  if (restoreTimer !== null) window.clearTimeout(restoreTimer)
  restoreTimer = window.setTimeout(() => {
    if (master && ctx) {
      master.gain.cancelScheduledValues(ctx.currentTime)
      master.gain.setValueAtTime(1, ctx.currentTime)
    }
  }, fade * 1000 + 60)
}

/** ★ 停声：人工处理 / 关开关 / 组件卸载都走这里 */
export function stopAlarmSound() {
  if (ringTimer !== null) {
    window.clearTimeout(ringTimer)
    ringTimer = null
  }
  soundRinging.value = false
  fadeOut()
}

/** 异常报警音：双音循环，时长取当前配置（默认 15 秒） */
function ringAlarm(durationMs: number = RING_MS.value) {
  const c = ensureCtx()
  if (!c) return
  if (c.state === 'suspended') void c.resume()
  const m = masterNode(c)

  // 时长为 0 = 现场把"响多久"拖到了 0：只闪不响，直接返回
  if (durationMs <= 0) return

  // 新一轮报警：清掉上一轮的排程与静音，从头响满整个窗口
  if (ringTimer !== null) window.clearTimeout(ringTimer)
  const now = c.currentTime
  m.gain.cancelScheduledValues(now)
  m.gain.setValueAtTime(1, now)

  const t0 = now + 0.02
  const cycles = Math.max(1, Math.floor(durationMs / CYCLE_MS))
  for (let i = 0; i < cycles; i++) {
    const base = t0 + (i * CYCLE_MS) / 1000
    tone(c, base, 988, 0.16, 0.16) // 高音：抓注意力
    tone(c, base + 0.19, 740, 0.3, 0.16) // 低音：落下去，不刺耳
  }

  // 到点自动收声（与 statusBlink / 全屏浮层同一个窗口）
  soundRinging.value = true
  ringTimer = window.setTimeout(() => {
    ringTimer = null
    soundRinging.value = false
    fadeOut(0.25)
  }, durationMs)
}

/** 开关打开时的确认音（顺带当"试听"） */
function playPing() {
  const c = ensureCtx()
  if (!c) return
  if (c.state === 'suspended') void c.resume()
  const m = masterNode(c)
  m.gain.cancelScheduledValues(c.currentTime)
  m.gain.setValueAtTime(1, c.currentTime)
  tone(c, c.currentTime + 0.02, 1174, 0.12, 0.12)
}

export function useAlarmSound() {
  function play() {
    if (!soundEnabled.value) return
    ringAlarm()
  }

  function setEnabled(v: boolean) {
    soundEnabled.value = v
    localStorage.setItem(KEY, v ? '1' : '0')
    if (v) playPing()
    else stopAlarmSound() // ★ 关掉开关立即静音，不等窗口结束
  }

  function toggle() {
    setEnabled(!soundEnabled.value)
  }

  return { enabled: soundEnabled, ringing: soundRinging, play, stop: stopAlarmSound, toggle, setEnabled, test: playPing }
}
