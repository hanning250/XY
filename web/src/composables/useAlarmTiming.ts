/**
 * ★ 报警提醒时长配置 —— 声音 / 闪烁 / 全屏 的唯一来源。
 *
 * 背景：这三个时长原来各自写死 15000，散在三个文件里
 *   · useAlarmSound.ts  RING_MS
 *   · stores/alarm.ts   FLASH_MS
 *   · AlarmFullscreen.vue  AUTO_CLOSE_MS
 * 现场要求「提醒多久」可调 —— 报警密集的产线嫌 15 秒太长（一直响一直闪），
 * 夜班人少的车间嫌太短（没走到跟前就停了）。所以做成可配置。
 *
 * 设计要点：
 *   · **前端设置 + localStorage**：现场自己在顶栏齿轮里拖滑块，立即生效，
 *     不用重启后端、不用重新构建前端。改的是"这台机器"的行为，
 *     与后端配置（ISUP_UI_SCALE 那种全局项）分开，互不干扰。
 *   · **默认 15 秒**，与历史行为、与《接口手册》里的口径完全一致 ——
 *     没人动过配置时，行为跟以前一模一样。
 *   · **全屏时长跟随闪烁时长**（产品口径：一次报警就是"响 + 闪 + 糊屏"
 *     同一个窗口，三个动作同时开始、同时结束）。不单独开第三个滑块，
 *     避免现场调出"声音停了全屏还糊着"这种自相矛盾的状态。
 *   · 只在 0~60 秒之间 —— 超过 1 分钟没有意义（真需要就一直处理掉它），
 *     也防止误拖到极值把值守机卡住。
 */
import { computed, ref, watch } from 'vue'

const KEY = 'isup_alarm_timing'

/** 限幅：0~60 秒，整数 */
export function clampSeconds(v: unknown, fallback: number): number {
  const n = Number(v)
  if (!Number.isFinite(n)) return fallback
  return Math.min(60, Math.max(0, Math.round(n)))
}

interface Stored {
  sound?: number
  flash?: number
}

function load(): Stored {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return {}
    const o = JSON.parse(raw) as Stored
    return o && typeof o === 'object' ? o : {}
  } catch {
    return {}
  }
}

const saved = load()

/**
 * 声音时长（秒）。0 = 只闪/糊屏不响 —— 与顶栏喇叭开关是两个维度：
 * 开关是"要不要这个功能"，这里是"响多久"。
 */
export const soundSeconds = ref(clampSeconds(saved.sound ?? 15, 15))

/**
 * 闪烁时长（秒）。同时决定**全屏浮层的自动收起时间**（见下方 fullscreenSeconds）。
 * 下限 1 秒：0 会让"闪一下"变成"看不见"，不如直接关掉功能。
 */
export const flashSeconds = ref(
  Math.max(1, clampSeconds(saved.flash ?? 15, 15)),
)

/** 派生的毫秒值：供各处计时器直接使用 */
export const soundMs = computed(() => soundSeconds.value * 1000)
export const flashMs = computed(() => flashSeconds.value * 1000)
/** ★ 全屏跟随闪烁，保证"响 / 闪 / 糊屏"同起同落 */
export const fullscreenMs = computed(() => flashMs.value)

/** 是否有任何自定义（用于设置面板显示"已修改"） */
export const isCustomized = computed(
  () => soundSeconds.value !== 15 || flashSeconds.value !== 15,
)

function persist() {
  try {
    localStorage.setItem(
      KEY,
      JSON.stringify({ sound: soundSeconds.value, flash: flashSeconds.value }),
    )
  } catch {
    /* 隐私模式写不进去：内存里生效即可，不影响本次值守 */
  }
}

watch([soundSeconds, flashSeconds], persist)

/** 设置面板用：改值（带限幅，防止滑块外部输入越界） */
export function setTiming(next: { sound?: number; flash?: number }) {
  if (next.sound !== undefined) {
    soundSeconds.value = clampSeconds(next.sound, 15)
  }
  if (next.flash !== undefined) {
    flashSeconds.value = Math.max(1, clampSeconds(next.flash, 15))
  }
}

/** 恢复默认 15 / 15 秒 */
export function resetTiming() {
  soundSeconds.value = 15
  flashSeconds.value = 15
}

/**
 * 兼容旧引用：RING_MS / FLASH_MS 原来是被 import 的常量。
 * 保留名字但改成「读当前值」的函数，避免有人直接 import 到旧快照值。
 */
export function ringMsNow(): number {
  return soundMs.value
}
export function flashMsNow(): number {
  return flashMs.value
}
