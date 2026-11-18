<script setup lang="ts">
/**
 * ★ 全屏报警浮层（AlarmFullscreen）—— 现场值守"糊屏"提醒。
 *
 * 需求（甲方现场）：报警来了要**全屏**，字要大 ——
 *   值班室的人可能不在电脑前，余光扫一眼就要知道"哪条产线、什么违规、
 *   几点几分、哪台设备"。小 toast 在 1920 大屏上等于没提醒。
 *
 * 触发口径（与响铃、状态框闪烁完全一致，见 AlarmBoard.isAbnormal）：
 *   **只对"检出违规"的报警弹全屏** —— extra.alarmed_count > 0，或缺值时
 *   AIOP 告警。移动侦测（VMD）这类噪声只走小 toast，不糊屏。
 *
 * 退出方式（三条都要，现场缺一条都会被骂）：
 *   · 到点自动收起 —— 时长跟随「闪烁」设置（默认 15 秒，见 useAlarmTiming），
 *     保证「响 / 闪 / 糊屏」同起同落
 *   · 点「知道了」/ 点遮罩 / 按 Esc / 按空格 —— 立即关闭
 *   · 连发多条报警时，新的一条**顶掉**旧的（排队会比糊屏更糟）
 *
 * 设计取舍：
 *   · 深色遮罩 + 大字号，但**图片本身不被裁**（contain，不 cover）——
 *     看到的是完整抓拍画面，不是裁掉两边的脸
 *   · 版面用 grid 两栏：左图右信息。1920 下图片够大，信息区字号
 *     一路放大到 40~72px，站三米外也读得清
 *   · 红色只用在"未处理"这一件事上，不做整屏红 —— 整屏红看久了会灼眼，
 *     反而丢失"哪里违规"的信息
 *   · 倒计时环：让人知道还要糊多久，减少"它怎么还不走"的焦躁
 */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { Bell, Close, Picture } from '@element-plus/icons-vue'
import { withToken } from '@/api'
import { fullscreenMs } from '@/composables/useAlarmTiming'
import { alarmTypeText, useAlarmStore } from '@/stores/alarm'
import type { AlarmBrief } from '@/types'

const props = defineProps<{ alarm: AlarmBrief | null }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'detail', a: AlarmBrief): void
}>()

const store = useAlarmStore()

/**
 * 自动收起时长：跟随「闪烁」设置（默认 15 秒）。
 * ★ 必须用 computed 而不是 const 快照 —— 现场在弹窗里拖完滑块，
 *   下一条报警就要按新时长走，不能等刷新页面。
 */
const AUTO_CLOSE_MS = fullscreenMs
const remainMs = ref(AUTO_CLOSE_MS.value)
let autoTimer: number | null = null
let tickTimer: number | null = null

const typeLabel = computed(() => {
  const a = props.alarm
  if (!a) return ''
  return a.type_text || alarmTypeText(a.alarm_type)
})

/** 有图才显示，过期/无图给明确占位（绝不画假图） */
const imageUrl = computed(() => {
  const a = props.alarm
  if (!a || a.media_expired || !a.thumbnail_url) return ''
  return withToken(a.thumbnail_url)
})
const imgFailed = ref(false)
watch(imageUrl, () => (imgFailed.value = false))

/** 时间拆成"大时分秒 + 小日期"，扫读时先看时分秒 */
const timeMain = computed(() => {
  const t = props.alarm?.alarm_time
  if (!t) return '--:--:--'
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return t
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
})

const dateSub = computed(() => {
  const t = props.alarm?.alarm_time
  if (!t) return ''
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return ''
  const p = (n: number) => String(n).padStart(2, '0')
  const week = ['日', '一', '二', '三', '四', '五', '六'][d.getDay()]
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} 周${week}`
})

/** 违规人数单独拎出来放大 —— 这是最该被看见的数字 */
const alarmedCount = computed(() => {
  const n = props.alarm?.extra?.alarmed_count
  return typeof n === 'number' && n > 0 ? n : null
})

const summaryText = computed(() => {
  const a = props.alarm
  if (!a) return ''
  if (a.summary) return a.summary
  const e = a.extra || {}
  if (e.person_count != null) {
    return e.alarmed_count
      ? `检出 ${e.person_count} 人，其中 ${e.alarmed_count} 人疑似违规（设备识别）`
      : `检出 ${e.person_count} 人`
  }
  return '—'
})

const wsLabel = computed(() => {
  const a = props.alarm
  return a?.workshop_name || a?.workshop || '未指派车间'
})

/** 倒计时进度（0~1），画在右侧小环上 */
const dashPct = computed(() =>
  AUTO_CLOSE_MS.value > 0 ? Math.max(0, remainMs.value / AUTO_CLOSE_MS.value) : 0,
)
const RING_LEN = 100.5 // 2πr, r=16

function clearTimers() {
  if (autoTimer !== null) {
    window.clearTimeout(autoTimer)
    autoTimer = null
  }
  if (tickTimer !== null) {
    window.clearInterval(tickTimer)
    tickTimer = null
  }
}

function startTimers() {
  clearTimers()
  const total = AUTO_CLOSE_MS.value
  remainMs.value = total
  const startedAt = Date.now()
  tickTimer = window.setInterval(() => {
    remainMs.value = Math.max(0, total - (Date.now() - startedAt))
  }, 100)
  autoTimer = window.setTimeout(() => close(), total)
}

function close() {
  clearTimers()
  emit('close')
}

/** 新报警顶掉旧的：重置计时，不叠加 */
watch(
  () => props.alarm?.id,
  (id) => {
    if (id) startTimers()
    else clearTimers()
  },
)

function onKey(e: KeyboardEvent) {
  if (!props.alarm) return
  // 全屏形态下只吃这四个键：Esc / 空格 / 回车 关闭，D 进详情
  if (e.key === 'Escape' || e.key === ' ' || e.key === 'Enter') {
    e.preventDefault()
    close()
  } else if (e.key === 'd' || e.key === 'D') {
    const a = props.alarm
    if (a) emit('detail', a)
  }
}

onMounted(() => {
  if (props.alarm) startTimers()
  window.addEventListener('keydown', onKey)
})
onUnmounted(() => {
  clearTimers()
  window.removeEventListener('keydown', onKey)
})

function openDetail() {
  const a = props.alarm
  if (a) emit('detail', a)
}
</script>

<template>
  <transition name="fs">
    <div v-if="alarm" class="fs-mask" role="alertdialog" aria-label="新的违规报警">
      <div class="fs-card">
        <!-- ============ 左：抓拍大图 ============ -->
        <div class="fs-media">
          <img v-if="imageUrl && !imgFailed" :src="imageUrl" alt="报警抓拍" @error="imgFailed = true" />
          <div v-else class="fs-noimg">
            <el-icon :size="56"><Picture /></el-icon>
            <span>
              {{ alarm.media_expired ? '该报警的图片已过保留期被清理' : imgFailed ? '图片加载失败' : '该报警暂无抓拍图' }}
            </span>
          </div>

          <!-- 图上角标：哪条产线（现场第一眼要认这个） -->
          <div class="fs-ws">{{ wsLabel }}</div>
        </div>

        <!-- ============ 右：信息 ============ -->
        <div class="fs-info">
          <div class="fs-head">
            <span class="fs-badge">
              <el-icon><Bell /></el-icon>
              新的违规报警
            </span>
            <span class="fs-close" title="关闭（Esc / 空格）" @click="close">
              <el-icon :size="22"><Close /></el-icon>
            </span>
          </div>

          <div class="fs-type">{{ typeLabel }}</div>
          <div class="fs-sum">{{ summaryText }}</div>

          <div class="fs-time">
            <span class="fs-hms">{{ timeMain }}</span>
            <span class="fs-date">{{ dateSub }}</span>
          </div>

          <!-- ★ 违规人数：全屏里第二该被看见的东西。做成大色块而不是小标签，
               一是吃掉右栏中段的纵向空间（原来是一片空白），
               二是让"几个人疑似违规（设备识别）"在余光里也能被扫到。 -->
          <div v-if="alarmedCount !== null" class="fs-hero">
            <div class="hero-main">
              <span class="hero-num">{{ alarmedCount }}</span>
              <span class="hero-unit">人疑似违规（设备识别）</span>
            </div>
            <div v-if="alarm.extra?.person_count != null" class="hero-sub">
              画面检出 <b>{{ alarm.extra.person_count }}</b> 人
            </div>
          </div>

          <div class="fs-tags">
            <span class="fs-tag ws">{{ wsLabel }}</span>
            <span class="fs-tag">{{ alarm.device_id || '未知设备' }}</span>
            <span class="fs-tag">通道 {{ alarm.channel }}</span>
            <span v-if="alarm.extra?.repeat_count && alarm.extra.repeat_count > 1" class="fs-tag warn">
              重复上报 ×{{ alarm.extra.repeat_count }}
            </span>
          </div>

          <div class="fs-foot">
            <button class="fs-btn primary" @click="close">
              知道了
              <span class="fs-kbd">空格</span>
            </button>
            <button class="fs-btn" @click="openDetail">查看详情</button>

            <!-- 倒计时环：让人知道还要糊多久 -->
            <span class="fs-timer" :title="`${Math.ceil(remainMs / 1000)} 秒后自动关闭`">
              <svg viewBox="0 0 40 40" width="42" height="42">
                <circle class="t-bg" cx="20" cy="20" r="16" />
                <circle
                  class="t-fg"
                  cx="20"
                  cy="20"
                  r="16"
                  :stroke-dasharray="`${dashPct * RING_LEN} ${RING_LEN}`"
                />
              </svg>
              <b>{{ Math.ceil(remainMs / 1000) }}</b>
            </span>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
/* ============ 遮罩：深色压住底下的界面，但透一点点 ============ */
.fs-mask {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(8, 16, 28, 0.82);
  backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2.2% 2%;
}

/* ============ 卡片：两栏，左图右信息 ============ */
.fs-card {
  width: 100%;
  height: 100%;
  max-width: 1880px;
  background: #0d1520;
  border: 2px solid var(--danger);
  border-radius: 14px;
  box-shadow: 0 0 0 1px rgba(var(--danger-rgb), 0.35), 0 24px 80px rgba(0, 0, 0, 0.55);
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(420px, 1fr);
  overflow: hidden;
}

/* ============ 左：图 ============ */
.fs-media {
  position: relative;
  background: #070c13;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
  overflow: hidden;
}
.fs-media img {
  /* ★ contain 不裁图：抓拍里的人/工装必须完整可见 */
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  display: block;
}
.fs-noimg {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
  color: #6b7c8f;
  font-size: 22px;
}
.fs-ws {
  position: absolute;
  left: 22px;
  top: 20px;
  font-size: 26px;
  font-weight: 800;
  color: #fff;
  letter-spacing: 1px;
  background: rgba(var(--danger-rgb), 0.9);
  border-radius: 8px;
  padding: 6px 18px;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.4);
}

/* ============ 右：信息 ============ */
.fs-info {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 30px 34px 26px;
  min-width: 0;
  overflow: hidden;
  background: linear-gradient(180deg, #111c2b 0%, #0d1520 100%);
}

.fs-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}
.fs-badge {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 24px;
  font-weight: 800;
  letter-spacing: 2px;
  color: #fff;
  background: var(--danger);
  border-radius: 8px;
  padding: 8px 20px;
  animation: fsBadge 1s ease-in-out infinite;
}
@keyframes fsBadge {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.62; }
}
.fs-close {
  color: #9fb0c4;
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  display: flex;
  transition: color 0.15s, background 0.15s;
}
.fs-close:hover { color: #fff; background: rgba(255, 255, 255, 0.1); }

/* ★ 类型：全屏里最大的字。标题越长越自动缩（clamp），不会溢出去 */
.fs-type {
  font-size: clamp(40px, 4.2vw, 68px);
  font-weight: 800;
  line-height: 1.12;
  color: #fff;
  letter-spacing: 1px;
  word-break: break-word;
}
.fs-sum {
  font-size: clamp(22px, 1.7vw, 30px);
  color: #b9c8d8;
  line-height: 1.45;
}

/* ★ 时间：值班记录要对表，秒级必须看得见 */
.fs-time {
  display: flex;
  align-items: baseline;
  gap: 16px;
  flex-wrap: wrap;
  margin-top: 2px;
}
.fs-hms {
  font-size: clamp(46px, 4.6vw, 74px);
  font-weight: 800;
  color: #fff;
  font-variant-numeric: tabular-nums;
  letter-spacing: 2px;
  line-height: 1;
}
.fs-date {
  font-size: clamp(18px, 1.4vw, 24px);
  color: #8fa2b6;
  font-variant-numeric: tabular-nums;
}

.fs-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.fs-tag {
  font-size: var(--fs-xl);
  color: #c6d4e2;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 7px;
  padding: 6px 14px;
  white-space: nowrap;
}
.fs-tag.ws { color: #9ee0bd; border-color: rgba(26, 127, 75, 0.5); }
.fs-tag.danger {
  color: #ff9b92;
  border-color: rgba(var(--danger-rgb), 0.55);
  background: rgba(var(--danger-rgb), 0.16);
}
.fs-tag.warn { color: #ffc98a; border-color: rgba(var(--warn-rgb), 0.5); }
.fs-tag b { font-size: 22px; font-weight: 800; }

/* ★ 违规人数大色块：吃掉右栏中段剩余空间，数字在余光里可读 */
.fs-hero {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 10px;
  padding: 20px 28px;
  border-radius: 12px;
  background: rgba(var(--danger-rgb), 0.14);
  border: 1px solid rgba(var(--danger-rgb), 0.45);
  border-left: 6px solid var(--danger);
  /* ★ 吃掉剩余纵向空间（原来靠 margin-top:auto 顶，会把中段留成一大块空白） */
  flex: 1 1 auto;
  min-height: 150px;
}
.hero-main {
  display: flex;
  align-items: baseline;
  gap: 14px;
}
.hero-num {
  font-size: clamp(84px, 8.6vw, 152px);
  font-weight: 800;
  line-height: 0.92;
  color: #ff6b5e;
  font-variant-numeric: tabular-nums;
  letter-spacing: -3px;
}
.hero-unit {
  font-size: clamp(26px, 2.1vw, 38px);
  font-weight: 700;
  color: #ffb3ac;
}
.hero-sub {
  font-size: clamp(19px, 1.35vw, 24px);
  color: #b9c8d8;
}
.hero-sub b {
  font-size: 1.3em;
  font-weight: 800;
  color: #fff;
  font-variant-numeric: tabular-nums;
  margin: 0 2px;
}

.fs-foot {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-shrink: 0;
  padding-top: 6px;
}
.fs-btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: 700;
  padding: 14px 26px;
  border-radius: 9px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  background: rgba(255, 255, 255, 0.07);
  color: #e6eef7;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s, border-color 0.15s;
}
.fs-btn:hover { background: rgba(255, 255, 255, 0.14); }
.fs-btn.primary {
  background: var(--danger);
  border-color: var(--danger);
  color: #fff;
  flex: 1;
  justify-content: center;
}
.fs-btn.primary:hover { background: #b8241a; }
.fs-kbd {
  font-size: var(--fs-micro);
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 5px;
  background: rgba(0, 0, 0, 0.25);
  color: rgba(255, 255, 255, 0.8);
}

/* 倒计时环 */
.fs-timer {
  position: relative;
  width: 42px;
  height: 42px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.fs-timer svg { transform: rotate(-90deg); }
.fs-timer .t-bg { fill: none; stroke: rgba(255, 255, 255, 0.16); stroke-width: 3; }
.fs-timer .t-fg {
  fill: none;
  stroke: #8fa2b6;
  stroke-width: 3;
  stroke-linecap: round;
  transition: stroke-dasharray 0.1s linear;
}
.fs-timer b {
  position: absolute;
  font-size: var(--fs-base);
  font-weight: 700;
  color: #b9c8d8;
  font-variant-numeric: tabular-nums;
}

/* ============ 入场 ============ */
.fs-enter-active { transition: opacity 0.18s ease; }
.fs-leave-active { transition: opacity 0.2s ease; }
.fs-enter-from,
.fs-leave-to { opacity: 0; }
.fs-enter-active .fs-card { animation: fsPop 0.22s cubic-bezier(0.2, 0.9, 0.3, 1.2); }
@keyframes fsPop {
  from { transform: scale(0.97); }
  to { transform: scale(1); }
}
@media (prefers-reduced-motion: reduce) {
  .fs-badge { animation: none; }
  .fs-enter-active .fs-card { animation: none; }
}

/* ============ 窄屏/竖屏：图在上、信息在下 ============ */
@media (max-width: 1100px), (orientation: portrait) {
  .fs-card {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: minmax(0, 1.15fr) auto;
  }
  .fs-info { padding: 20px 22px 18px; gap: 12px; }
  .fs-type { font-size: clamp(30px, 6vw, 46px); }
  .fs-hms { font-size: clamp(34px, 7vw, 54px); }
  .fs-tag { font-size: var(--fs-base); }
  .fs-btn { font-size: var(--fs-lg); padding: 11px 18px; }
  .fs-hero { padding: 14px 18px; min-height: 90px; }
  .hero-num { font-size: clamp(52px, 14vw, 84px); }
  .hero-sub { display: none; }
}
</style>
