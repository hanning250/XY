<script setup lang="ts">
/**
 * ★ 实况画面（LiveFocus）—— 「报警看板」页的"当下这一刻"。
 *
 * 设计意图：
 *   值班人员最关心的永远是「最新那条报警长什么样」。所以列表不再是唯一入口，
 *   左侧常驻一个实况窗口：
 *     · 点列表任意一行 → 窗口立刻换成那张图（与列表双向联动）
 *     · 打开「跟随最新」→ 新报警到达自动换图 + 红框闪一下
 *     · 键盘 ↑/↓ 换图、空格标记已处理、Esc 回到最新
 *   一屏之内完成「看态势 → 看图 → 处置」闭环，不用来回跳页。
 *
 * 状态语义：
 *   · 未处理/已处理 用色点区分，不在按钮上重复说一遍
 *   · 媒体已过期 / 无图 / 加载失败 三种"没有图"的原因分别给出人话提示
 */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft,
  ArrowRight,
  Picture,
  RefreshRight,
  VideoCamera,
  View,
} from '@element-plus/icons-vue'
import { withToken } from '@/api'
import { alarmTypeText, useAlarmStore } from '@/stores/alarm'
import type { AlarmBrief } from '@/types'

const props = defineProps<{
  /** 当前聚焦的报警（通常 = 列表选中行） */
  alarm: AlarmBrief | null
  /** 是否跟随最新（新报警自动切图） */
  follow: boolean
  /** 当前在列表里的位置（从 1 开始显示，-1 表示不在当前页） */
  index: number
  /** 本页条数 */
  total: number
  /** 新报警到达的闪烁标记（由父组件计时） */
  flash?: boolean
}>()

const emit = defineEmits<{
  (e: 'open-detail', a: AlarmBrief): void
  (e: 'prev'): void
  (e: 'next'): void
  (e: 'toggle-follow'): void
}>()

const store = useAlarmStore()

const imgLoading = ref(false)
const imgFailed = ref(false)
const grabbing = ref(false)

const imageUrl = computed(() => {
  const a = props.alarm
  if (!a || a.media_expired || !a.thumbnail_url) return ''
  return withToken(a.thumbnail_url)
})

watch(imageUrl, () => {
  imgFailed.value = false
})

/** 没有图时的原因（分情况给话术，避免一律"暂无图片"） */
const emptyReason = computed(() => {
  const a = props.alarm
  if (!a) return { title: '值守中', sub: '等待新的报警接入' }
  if (a.media_expired) return { title: '媒体已清理', sub: '该报警的图片/视频已按保留策略删除' }
  if (imgFailed.value) return { title: '图片加载失败', sub: '稍后重试，或打开详情查看' }
  if (!a.thumbnail_url) {
    return {
      title: '图片待关联',
      sub: a.status === 'awaiting_media' ? '设备图片正在上传，稍候自动刷新' : '该报警没有关联图片',
    }
  }
  return { title: '', sub: '' }
})

const typeLabel = computed(() => {
  const a = props.alarm
  if (!a) return ''
  return a.type_text || alarmTypeText(a.alarm_type)
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
  return e.channel_name ? `通道 ${e.channel_name}` : ''
})

/** ★ 违规人数（替代原来的"未处理/已处理"标签）：直接回答"这次卷进了几个人" */
const alarmedCount = computed(() => {
  const n = props.alarm?.extra?.alarmed_count
  return typeof n === 'number' ? n : 0
})

/** 报警时间的两段式表达：大字给时分秒，小字给日期 */
const timeMain = computed(() => {
  const t = props.alarm?.alarm_time
  if (!t) return '--:--:--'
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return t
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
})

const timeSub = computed(() => {
  const t = props.alarm?.alarm_time
  if (!t) return ''
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
})

/** 视频状态 → 一行短文案（就绪的给"可查看"，其余给进度） */
const videoText = computed(() => {
  const v = props.alarm?.video
  if (!v) return ''
  switch (v.status) {
    case 'ready':
      return '视频已就绪'
    case 'starting':
      return '视频抓取中…'
    case 'failed':
      return '视频获取失败'
    case 'unavailable':
      return '视频已清理'
    default:
      return '未抓取视频'
  }
})

const canGrabVideo = computed(() => {
  const v = props.alarm?.video
  if (!props.alarm || props.alarm.media_expired) return false
  return v?.status !== 'starting'
})

async function grabVideo() {
  const a = props.alarm
  if (!a || grabbing.value) return
  grabbing.value = true
  try {
    await store.requestPlayback(a.id)
    ElMessage.success('已提交抓取，完成后自动更新')
  } catch {
    /* 拦截器已提示 */
  } finally {
    grabbing.value = false
  }
}

/* ---------------- 键盘操作（值守效率，作用域仅本页） ---------------- */
/** 正在输入/选择/按按钮时不吃按键（筛选框、日期面板、弹窗、按钮都要正常响应） */
function typingInForm(): boolean {
  const el = document.activeElement as HTMLElement | null
  if (!el) return false
  const tag = el.tagName?.toLowerCase()
  if (tag === 'input' || tag === 'textarea' || tag === 'select') return true
  if (tag === 'button' || tag === 'a') return true
  if (el.isContentEditable) return true
  return !!el.closest('.el-select, .el-date-editor, .el-picker-panel, .el-dialog, .el-message-box')
}

function onKey(e: KeyboardEvent) {
  if (typingInForm()) return
  switch (e.key) {
    case 'ArrowUp':
      emit('prev')
      e.preventDefault()
      break
    case 'ArrowDown':
      emit('next')
      e.preventDefault()
      break
    case 'Escape':
      // 暂停时按 Esc 回到「跟随最新」
      if (!props.follow) emit('toggle-follow')
      break
  }
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <section class="focus" :class="{ flash: props.flash, empty: !props.alarm }">
    <!-- 头部：标题 + 跟随开关 + 上一个/下一个 -->
    <header class="f-head">
      <div class="f-title">
        <el-icon><VideoCamera /></el-icon>
        <span>实况画面</span>
        <span v-if="props.alarm" class="f-pos">{{ props.index > 0 ? props.index : '–' }}/{{ props.total }}</span>
      </div>

      <div class="f-ops">
        <button
          class="mini"
          :class="{ on: props.follow }"
          :title="props.follow ? '正在跟随最新报警，点击停止' : '开启后新报警自动换图'"
          @click="emit('toggle-follow')"
        >
          <span class="dot" />{{ props.follow ? '跟随中' : '已暂停' }}
        </button>
        <button class="mini icon" title="上一条 (↑)" @click="emit('prev')">
          <el-icon><ArrowLeft /></el-icon>
        </button>
        <button class="mini icon" title="下一条 (↓)" @click="emit('next')">
          <el-icon><ArrowRight /></el-icon>
        </button>
      </div>
    </header>

    <!-- 画面区：contain 不变形，深色底，等图期间不跳布局 -->
    <div class="stage">
      <el-image
        v-if="imageUrl && !imgFailed"
        :src="imageUrl"
        fit="contain"
        class="shot"
        :preview-src-list="[imageUrl]"
        :initial-index="0"
        preview-teleported
        hide-on-click-modal
        @load="imgLoading = false"
        @error="imgFailed = true"
      >
        <template #placeholder>
          <div class="ph"><el-icon :size="26"><Picture /></el-icon></div>
        </template>
      </el-image>

      <div v-else class="idle">
        <div class="idle-ring"><span class="idle-dot" /></div>
        <div class="idle-title">{{ emptyReason.title }}</div>
        <div class="idle-sub">{{ emptyReason.sub }}</div>
      </div>

      <!-- 角标：时间 + 车间，扫读时不用看下面的明细 -->
      <div v-if="props.alarm" class="stamp">
        <span class="stamp-time">{{ timeMain }}</span>
        <span v-if="props.alarm.workshop_name || props.alarm.workshop" class="stamp-ws">
          {{ props.alarm.workshop_name || props.alarm.workshop }}
        </span>
      </div>
    </div>

    <!-- 明细 + 操作 -->
    <div v-if="props.alarm" class="meta">
      <div class="m-row">
        <span class="m-type">{{ typeLabel }}</span>
        <!-- ★ 2026-10-26：原「未处理/已处理」标签 + 「标记已处理」按钮已移除。
             这是纯展示看板，甲方只看不点。这个位置改为**违规人数**：
             红底白字，直接回答"这次卷进了几个人"。
             新报警仍会闪动提醒（store 计时，15 秒后自动停）。 -->
        <span
          class="m-alarmed"
          :class="{ zero: alarmedCount === 0, flashing: store.isFlashing(props.alarm.id) }"
        >
          违规 {{ alarmedCount }} 人
        </span>
      </div>
      <div v-if="summaryText" class="m-sum">{{ summaryText }}</div>
      <div class="m-sub">
        <span>{{ timeSub }}</span>
        <span class="sep">·</span>
        <span>{{ props.alarm.device_id || '未知设备' }} CH{{ props.alarm.channel }}</span>
        <span class="sep">·</span>
        <span>{{ props.alarm.image_count }} 张图</span>
        <span class="sep">·</span>
        <span class="v-txt">{{ videoText }}</span>
      </div>

      <div class="acts">
        <el-button
          size="small"
          :icon="RefreshRight"
          :disabled="!canGrabVideo"
          :loading="grabbing"
          @click="grabVideo"
        >
          抓取视频
        </el-button>
        <el-button size="small" :icon="View" @click="emit('open-detail', props.alarm)">
          详情
        </el-button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.focus {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  overflow: hidden;
  box-shadow: var(--shadow-2);
  transition: border-color 0.5s, box-shadow 0.5s;
}
/* 新异常到达：红框闪动（时长可配，默认 15 秒；呼吸式，不遮挡画面内容） */
.focus.flash {
  border-color: var(--danger);
  animation: panelFlash 1s ease-in-out infinite;
}
@keyframes panelFlash {
  0%, 100% {
    box-shadow: 0 0 0 1px rgba(var(--danger-rgb), 0.45), 0 0 0 rgba(var(--danger-rgb), 0);
  }
  50% {
    box-shadow: 0 0 0 2px rgba(var(--danger-rgb), 0.75), 0 0 22px rgba(var(--danger-rgb), 0.3);
  }
}
@media (prefers-reduced-motion: reduce) {
  .focus.flash { animation: none; box-shadow: 0 0 0 2px rgba(var(--danger-rgb), 0.6); }
}

.f-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 9px 12px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.f-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--fs-md);              /* 视觉 12.8px */
  font-weight: 700;
  color: var(--text);
}
.f-title .el-icon { color: var(--brand); font-size: var(--fs-md); }
.f-pos {
  font-size: var(--fs-cap);             /* 视觉 11.2px */
  font-weight: 700;
  color: var(--text-2);
  font-variant-numeric: tabular-nums;
}
.f-ops { display: flex; align-items: center; gap: 7px; }

.mini {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 11px;
  font-size: var(--fs-cap);
  font-weight: 600;
  color: var(--text-2);
  background: var(--surface-3);
  border: 1px solid var(--border-2);
  border-radius: var(--r-sm);
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}
.mini:hover { color: var(--brand-deep); border-color: var(--brand-line); background: var(--brand-soft); }
.mini.icon { padding: 0 7px; }
.mini .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-3);
}
.mini.on { color: var(--ok); border-color: rgba(var(--ok-rgb), 0.45); background: rgba(var(--ok-rgb), 0.1); }
.mini.on .dot { background: var(--ok); animation: pulse 2.4s ease-out infinite; }

.stage {
  position: relative;
  flex: 1;
  min-height: 0;
  /* ★ 2026-10-26：与实时监控页统一 —— 空图/失败时不要一块死灰白板，
     加极淡斜纹让"没有图"也像一个有意的舞台。 */
  background:
    repeating-linear-gradient(
      135deg,
      transparent 0 22px,
      rgba(14, 110, 180, 0.022) 22px 44px
    ),
    var(--stage);
  display: flex;
  align-items: center;
  justify-content: center;
}
.shot { width: 100%; height: 100%; cursor: zoom-in; }
.shot :deep(img) { width: 100%; height: 100%; }
.ph { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--border-strong); }

.idle {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 20px;
  height: 100%;
}
.idle-ring {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  border: 1px solid var(--border-2);
  background: rgba(255, 255, 255, 0.75);
  box-shadow: var(--shadow-1);
  display: flex;
  align-items: center;
  justify-content: center;
}
.idle-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--ok);
  animation: pulse 2.8s ease-out infinite;
}
.idle-title { font-size: var(--fs-md); font-weight: 700; color: var(--text-2); letter-spacing: 0.4px; }
.idle-sub { font-size: var(--fs-cap); color: var(--text-3); text-align: center; line-height: 1.7; max-width: 280px; }

.stamp {
  position: absolute;
  left: 12px;
  top: 12px;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 5px 12px;
  border-radius: var(--r-sm);
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(6px);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-2);
  pointer-events: none;
}
.stamp-time {
  font-size: var(--fs-xl);              /* 视觉 16px */
  font-weight: 800;
  color: var(--text);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.3px;
}
.stamp-ws {
  font-size: var(--fs-cap);
  font-weight: 600;
  color: var(--text-2);
  padding-left: 9px;
  border-left: 1px solid var(--border-2);
}

.meta {
  padding: 12px 14px 13px;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.m-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.m-type {
  font-size: var(--fs-xl);              /* 视觉 16px */
  font-weight: 800;
  color: var(--text);
  letter-spacing: 0.2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.m-alarmed {
  display: inline-flex;
  align-items: center;
  height: 28px;
  padding: 0 13px;
  border-radius: var(--r-pill);
  font-size: var(--fs-md);
  font-weight: 800;
  letter-spacing: 0.3px;
  flex-shrink: 0;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  color: #fff;
  background: linear-gradient(135deg, var(--danger), #e3543a);
  border: 1px solid #b7261a;
  box-shadow: 0 1px 3px rgba(var(--danger-rgb), 0.38);
}
.m-alarmed.zero {
  color: var(--text-3);
  background: var(--surface-3);
  border-color: var(--border-2);
  box-shadow: none;
}
/* ★ 检出异常：标签闪动（时长可配，到点由 store 摘掉 class） */
.m-alarmed.flashing {
  animation: focusBlink 0.72s steps(1, end) infinite;
  box-shadow: 0 0 0 4px var(--danger-line);
}
@keyframes focusBlink {
  0% { opacity: 1; }
  50% { opacity: 0.35; }
  100% { opacity: 1; }
}
@media (prefers-reduced-motion: reduce) {
  .m-alarmed.flashing { animation: none; box-shadow: 0 0 0 3px var(--danger); }
}

.m-sum {
  font-size: var(--fs-base);
  color: var(--text-2);
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.m-sub {
  font-size: var(--fs-cap);
  color: var(--text-2);
  display: flex;
  align-items: center;
  gap: 7px;
  flex-wrap: wrap;
  font-variant-numeric: tabular-nums;
}
.m-sub .sep { color: var(--border-2); }
.v-txt { color: var(--text-2); }

.acts { display: flex; gap: 9px; margin-top: 3px; }
.acts :deep(.el-button) { flex: 0 0 auto; }

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(var(--ok-rgb), 0.5); }
  70% { box-shadow: 0 0 0 9px rgba(var(--ok-rgb), 0); }
  100% { box-shadow: 0 0 0 0 rgba(var(--ok-rgb), 0); }
}
</style>
