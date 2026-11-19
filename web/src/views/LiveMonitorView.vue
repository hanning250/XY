<script setup lang="ts">
/**
 * ★ 实时监控（值守页）—— 现场值班室大屏专用。
 *
 * 使用场景（与「实时报警」列表页的区别）：
 *   现场一天没几条报警，值守人员需要的是「来一条 → 立刻看到图」，
 *   而不是在密集列表里翻页找。所以本页做成：
 *     左侧：报警流（最新在最上，新到达高亮闪一下）
 *     右侧：选中报警的大图 + 关键信息 + 一键处置
 *
 * 设计要点：
 *   · 自动跟随：新报警到达自动选中并切图（可关闭，避免打断人工回看）
 *   · 键盘操作：↑/↓ 切换报警、Esc 取消跟随
 *   · 大图不变形：object-fit: contain + 深色底，1920 与 1440 都稳
 *   · 空态是常态：一条都没有时显示「值守中」而不是空白页
 */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Bell,
  Picture,
  RefreshRight,
  VideoCamera,
} from '@element-plus/icons-vue'
import { withToken, devApi, deviceApi } from '@/api'
import { alarmTypeText, useAlarmStore } from '@/stores/alarm'
import type { AlarmBrief } from '@/types'

const props = defineProps<{ connected?: boolean }>()

const emit = defineEmits<{ (e: 'open-detail', a: AlarmBrief): void }>()

const store = useAlarmStore()

/** 当前展示的报警 */
const current = ref<AlarmBrief | null>(null)
/** 自动跟随最新报警（默认开；手动选旧的就是关） */
const follow = ref(true)
/** 大图加载状态 */
const imgLoading = ref(false)
const imgFailed = ref(false)

/** 画面模式：alarm=报警抓拍，live=摄像头实况（ISAPI 定时抓拍） */
const stageMode = ref<'alarm' | 'live'>('alarm')
const liveChannel = ref(1)
const liveUrl = ref('')
const liveError = ref('')
let liveTimer: number | undefined
let liveObjectUrl: string | undefined

async function refreshLive() {
  try {
    const blob = await deviceApi.liveSnapshot(liveChannel.value, 1)
    if (!(blob instanceof Blob) || blob.size < 100 || blob.type.includes('json')) {
      // 失败时后端可能仍以 JSON 错误体返回（axios responseType=blob）
      const text = blob instanceof Blob ? await blob.text() : ''
      try {
        const j = JSON.parse(text) as { detail?: string }
        liveError.value = j.detail || '实况抓拍失败'
      } catch {
        liveError.value = '实况抓拍失败'
      }
      return
    }
    if (liveObjectUrl) URL.revokeObjectURL(liveObjectUrl)
    liveObjectUrl = URL.createObjectURL(blob)
    liveUrl.value = liveObjectUrl
    liveError.value = ''
  } catch (e: unknown) {
    const err = e as { response?: { data?: Blob | { detail?: string } }; message?: string }
    const data = err?.response?.data
    if (data instanceof Blob) {
      try {
        const j = JSON.parse(await data.text()) as { detail?: string }
        liveError.value = j.detail || '实况抓拍失败'
        return
      } catch { /* fallthrough */ }
    }
    liveError.value =
      (typeof data === 'object' && data && 'detail' in data && data.detail) ||
      err?.message ||
      '实况抓拍失败'
  }
}

function startLive() {
  stopLive()
  void refreshLive()
  liveTimer = window.setInterval(() => void refreshLive(), 1500)
}

function stopLive() {
  if (liveTimer !== undefined) {
    window.clearInterval(liveTimer)
    liveTimer = undefined
  }
  if (liveObjectUrl) {
    URL.revokeObjectURL(liveObjectUrl)
    liveObjectUrl = undefined
  }
  liveUrl.value = ''
}

watch(stageMode, (m) => {
  if (m === 'live') startLive()
  else stopLive()
})
watch(liveChannel, () => {
  if (stageMode.value === 'live') startLive()
})

const list = computed(() => store.items)

const currentImage = computed(() => {
  const a = current.value
  if (!a || a.media_expired || !a.thumbnail_url) return ''
  return withToken(a.thumbnail_url)
})

/**
 * 新报警到达：跟随模式下切图。
 * ★ 闪动不在这里计时 —— 统一由 store 标记（时长可配，默认 15 秒），
 *   这样列表页、实况画面、值守大屏三处永远同步。
 */
watch(
  () => list.value[0]?.id,
  (newId) => {
    if (!newId) return
    const fresh = list.value.find((a) => a.id === newId)
    if (!fresh) return
    if (follow.value) {
      current.value = fresh
      imgFailed.value = false
    }
  },
)

watch(currentImage, () => {
  imgFailed.value = false
})

/** 列表为空时清空选中 */
watch(list, (v) => {
  if (!v.length) current.value = null
  else if (!current.value) current.value = v[0]
})

function pick(a: AlarmBrief) {
  current.value = a
  follow.value = false
  imgFailed.value = false
}

function backToLatest() {
  follow.value = true
  if (list.value.length) {
    current.value = list.value[0]
    imgFailed.value = false
  }
}

/* ---------------- 键盘操作（值守效率） ---------------- */
const idx = computed(() =>
  current.value ? list.value.findIndex((a) => a.id === current.value!.id) : -1,
)

function move(delta: number) {
  if (!list.value.length) return
  const next = Math.min(Math.max(idx.value + delta, 0), list.value.length - 1)
  const target = list.value[next]
  if (target) pick(target)
}

async function grabVideo() {
  const a = current.value
  if (!a) return
  try {
    await store.requestPlayback(a.id)
    ElMessage.success('已提交抓取，完成后自动更新')
  } catch {
    /* 拦截器已提示 */
  }
}

/** ★ 模拟一条报警（仅调试模式可见）：现场报警稀疏时用于演示/自测 */
const devAvailable = ref(false)
const simulating = ref(false)

async function simulate() {
  if (simulating.value) return
  simulating.value = true
  try {
    await devApi.simulateAlarm({ device_id: 'sim-box' })
    // 新报警由 WebSocket 推送到达，无需手动插列表
  } catch {
    /* 拦截器已提示（交付机上该路由不存在 → 404） */
  } finally {
    simulating.value = false
  }
}

function onKey(e: KeyboardEvent) {
  const target = e.target as HTMLElement | null
  // 输入框里打字时不劫持按键
  if (target && /input|textarea/i.test(target.tagName)) return
  if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
    e.preventDefault()
    move(1)
  } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
    e.preventDefault()
    move(-1)
  } else if (e.key === 'Escape') {
    void backToLatest()
  }
}

onMounted(() => {
  if (list.value.length) current.value = list.value[0]
  window.addEventListener('keydown', onKey)
  // 探测调试接口是否存在（交付机没有 → 隐藏「模拟报警」按钮）
  void devApi.available().then((ok) => (devAvailable.value = ok))
})

onUnmounted(() => {
  stopLive()
  window.removeEventListener('keydown', onKey)
})

/* ---------------- 展示辅助 ---------------- */
function typeLabel(a: AlarmBrief): string {
  return a.type_text || alarmTypeText(a.alarm_type)
}

/** ★ 违规人数（替代原「未处理/已处理」）：直接回答"这次卷进了几个人" */
function alarmedOf(a: AlarmBrief): number {
  const n = a.extra?.alarmed_count
  return typeof n === 'number' ? n : 0
}

function hms(t: string): string {
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return t
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

function ymd(t: string): string {
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return ''
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function summaryText(a: AlarmBrief): string {
  if (a.summary) return a.summary
  const e = a.extra || {}
  if (e.person_count != null) {
    return e.alarmed_count
      ? `检出 ${e.person_count} 人，其中 ${e.alarmed_count} 人疑似违规（设备识别）`
      : `检出 ${e.person_count} 人`
  }
  return '—'
}

/** 车间名（未指派时给明确文案，不留空） */
function wsLabel(a: AlarmBrief): string {
  return a.workshop_name || a.workshop || '未指派车间'
}

/** 距当前选中报警的相对时间（值守时最关心"刚刚/几分钟前"） */
const agoText = computed(() => {
  const a = current.value
  if (!a) return ''
  const t = new Date(a.alarm_time).getTime()
  if (Number.isNaN(t)) return ''
  const s = Math.max(0, Math.round((Date.now() - t) / 1000))
  if (s < 60) return '刚刚'
  if (s < 3600) return `${Math.floor(s / 60)} 分钟前`
  if (s < 86400) return `${Math.floor(s / 3600)} 小时前`
  return `${Math.floor(s / 86400)} 天前`
})

/** 每秒刷新相对时间（只在有选中时跑） */
const tick = ref(0)
let tickTimer: number | null = null
onMounted(() => {
  tickTimer = window.setInterval(() => (tick.value = Date.now()), 1000)
})
onUnmounted(() => {
  if (tickTimer !== null) window.clearInterval(tickTimer)
})
void tick
</script>

<template>
  <div class="live">
    <!-- ============ 左：报警流 ============ -->
    <aside class="feed">
      <div class="feed-head">
        <div class="fh-top">
          <span class="dot-live" :class="{ off: props.connected === false }" />
          <span class="fh-title">值守中</span>
          <span class="fh-sub">{{ props.connected === false ? '推送断开' : '实时接收' }}</span>
        </div>
        <div class="fh-stat">
          <span>今日 <b>{{ store.stats.today }}</b></span>
          <!-- ★ 2026-10-26：原「待处理」累计数（只涨不跌、无法指导行动）已移除。
               换成「列表条数」—— 值守时真正关心的是"这一轮收了多少条可回看"。 -->
          <span>可回看 <b class="ok">{{ list.length }}</b></span>
        </div>
      </div>

      <div class="feed-tools">
        <button
          class="tool"
          :class="{ on: follow }"
          :title="follow ? '新报警会自动切图' : '已暂停自动跟随，点击恢复'"
          @click="follow ? (follow = false) : backToLatest()"
        >
          <el-icon><RefreshRight /></el-icon>
          {{ follow ? '自动跟随' : '已暂停' }}
        </button>
        <button class="tool" title="手动回到最新" @click="backToLatest">最新一条</button>
        <!-- 仅调试模式出现：现场报警稀疏，演示/自测时手动造一条 -->
        <button
          v-if="devAvailable"
          class="tool sim"
          title="造一条模拟报警（走真实落库与推送链路）"
          @click="simulate"
        >
          模拟报警
        </button>
      </div>

      <div class="feed-list">
        <div v-if="!list.length" class="feed-empty">暂无报警</div>
        <div
          v-for="a in list"
          :key="a.id"
          class="item"
          :class="{
            active: current?.id === a.id,
            flash: store.isFlashing(a.id),
          }"
          @click="pick(a)"
        >
          <div class="i-thumb">
            <img
              v-if="a.thumbnail_url && !a.media_expired"
              :src="withToken(a.thumbnail_url)"
              alt=""
              loading="lazy"
            />
            <div v-else class="i-noimg"><el-icon><Picture /></el-icon></div>
          </div>
          <div class="i-body">
            <div class="i-row1">
              <span class="i-time">{{ hms(a.alarm_time) }}</span>
              <span class="i-ws" :title="wsLabel(a)">
                {{ wsLabel(a) }}
              </span>
            </div>
            <div class="i-type" :title="typeLabel(a)">{{ typeLabel(a) }}</div>
            <div class="i-row3">
              <span class="i-dev">{{ a.device_id || '—' }} · CH{{ a.channel }}</span>
              <!-- ★ 2026-10-26：原「未处理/已处理」改为违规人数（客观事实，不需要人点） -->
              <span class="i-state" :class="{ zero: alarmedOf(a) === 0 }">
                违规 {{ alarmedOf(a) }} 人
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- ★ 2026-10-26：键盘提示的 ↑↓ 原来直接写字符，在某些字体下
           渲染成空白（实测只看到两个空键帽）。改为**纯 CSS 三角**，
           不依赖字体是否有该字形。 -->
      <div class="feed-foot">
        <kbd class="k-arrow up" title="上一条" />
        <kbd class="k-arrow down" title="下一条" />
        <span class="k-txt">切换</span>
        <kbd>Esc</kbd><span class="k-txt">回到最新</span>
      </div>
    </aside>

    <!-- ============ 右：大图 / 实况 ============ -->
    <main class="stage">
      <div class="stage-toolbar">
        <button type="button" class="mode" :class="{ on: stageMode === 'alarm' }" @click="stageMode = 'alarm'">报警抓拍</button>
        <button type="button" class="mode" :class="{ on: stageMode === 'live' }" @click="stageMode = 'live'">实时画面</button>
        <template v-if="stageMode === 'live'">
          <label class="ch">
            通道
            <select v-model.number="liveChannel">
              <option :value="1">1</option>
              <option :value="2">2</option>
              <option :value="3">3</option>
              <option :value="4">4</option>
            </select>
          </label>
          <button type="button" class="mode" @click="refreshLive">刷新</button>
        </template>
      </div>

      <!-- 实况：ISAPI 定时抓拍 -->
      <template v-if="stageMode === 'live'">
        <div class="shot live-shot">
          <img v-if="liveUrl" :src="liveUrl" alt="实时画面" />
          <div v-else class="shot-empty">
            <div class="se-ico"><el-icon :size="38"><VideoCamera /></el-icon></div>
            <div class="se-txt">{{ liveError || '正在连接实况…' }}</div>
            <div class="se-sub">约每 1.5 秒刷新一帧（ISAPI 抓拍）</div>
          </div>
          <div class="shot-tl">
            <span class="badge-live">实时画面</span>
            <span class="badge-time">通道 {{ liveChannel }}</span>
          </div>
        </div>
      </template>

      <template v-else-if="current">
        <!-- 图区 -->
        <div class="shot" :class="{ fresh: store.isFlashing(current.id) }">
          <img
            v-if="currentImage && !imgFailed"
            :src="currentImage"
            alt="报警抓拍"
            :class="{ loading: imgLoading }"
            @load="imgLoading = false"
            @error="imgFailed = true; imgLoading = false"
          />
          <div v-else class="shot-empty">
            <div class="se-ico"><el-icon :size="38"><Picture /></el-icon></div>
            <div class="se-txt">
              {{ current.media_expired ? '该报警的图片已过保留期被清理' : imgFailed ? '图片加载失败' : '该报警暂无抓拍图' }}
            </div>
            <div class="se-sub">
              {{ imgFailed ? '稍后重试，或打开详情查看原图' : '设备可能未上传抓拍图，可尝试重新抓取视频' }}
            </div>
          </div>

          <!-- 图上角标：时间 / 车间 -->
          <div class="shot-tl">
            <span class="badge-live">报警抓拍</span>
            <span class="badge-time">{{ ymd(current.alarm_time) }} {{ hms(current.alarm_time) }}</span>
            <span class="badge-ago">{{ agoText }}</span>
          </div>
          <div class="shot-tr">
            <span
              class="badge-alarmed"
              :class="{ zero: alarmedOf(current) === 0, flashing: store.isFlashing(current.id) }"
            >设备估算 {{ alarmedOf(current) }} 人</span>
          </div>
        </div>

        <!-- 信息 + 操作 -->
        <div class="meta">
          <div class="m-main">
            <div class="m-type">
              <el-icon><Bell /></el-icon>
              <span>{{ typeLabel(current) }}</span>
              <span v-if="current.extra?.repeat_count && current.extra.repeat_count > 1" class="m-repeat">
                ×{{ current.extra.repeat_count }}
              </span>
            </div>
            <div class="m-sum">{{ summaryText(current) }}</div>
            <div class="m-tags">
              <span class="tag ws">
                {{ current.workshop_name || current.workshop || '未指派车间' }}
              </span>
              <span class="tag">{{ current.device_id || '未知设备' }}</span>
              <span class="tag">通道 {{ current.channel }}</span>
              <span v-if="current.image_count" class="tag">{{ current.image_count }} 张图</span>
              <span
                class="tag"
                :class="{
                  'v-ready': current.video.status === 'ready',
                  'v-run': current.video.status === 'starting',
                }"
              >
                视频 {{ videoText(current.video.status) }}
              </span>
            </div>
          </div>

          <div class="m-actions">
            <button class="btn" @click="grabVideo">
              <el-icon><VideoCamera /></el-icon>
              抓取视频
            </button>
            <button class="btn" @click="emit('open-detail', current)">查看详情</button>
          </div>
        </div>
      </template>

      <!-- 待机态：现场大部分时间应该是这个样子 -->
      <div v-else class="idle">
        <div class="idle-ring">
          <span class="idle-dot" />
        </div>
        <div class="idle-title">值守中 · 等待报警上报</div>
        <div class="idle-sub">
          设备触发报警后，抓拍图会自动出现在这里
        </div>
      </div>
    </main>
  </div>
</template>

<script lang="ts">
function videoText(s: string): string {
  const map: Record<string, string> = {
    not_requested: '未抓取',
    starting: '抓取中',
    ready: '已就绪',
    failed: '抓取失败',
    unavailable: '不可用',
  }
  return map[s] || s
}
export default { name: 'LiveMonitorView' }
</script>

<style scoped>
.live {
  display: grid;
  /* ★ 字放大后 344px 会让"时间+车间"挤一行，加宽到 380px；
     右侧大图区本来就富余，让一点不吃亏 */
  grid-template-columns: 380px 1fr;
  gap: 12px;
  height: 100%;
  min-height: 0;
  padding: 14px 18px;
  box-sizing: border-box;
}
.stage-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.stage-toolbar .mode {
  border: 1px solid var(--border-2);
  background: var(--surface);
  color: var(--text-2);
  border-radius: 6px;
  padding: 4px 12px;
  font-size: var(--fs-cap);
  font-weight: 600;
  cursor: pointer;
}
.stage-toolbar .mode.on {
  background: var(--brand);
  border-color: var(--brand);
  color: #fff;
}
.stage-toolbar .ch {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs-cap);
  color: var(--text-2);
  margin-left: 4px;
}
.stage-toolbar .ch select {
  height: 28px;
  border-radius: 6px;
  border: 1px solid var(--border-2);
  background: var(--surface);
  color: var(--text);
  padding: 0 6px;
}

/* ============ 左：报警流 ============ */
.feed {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}
.feed-head {
  padding: 12px 14px 10px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.fh-top { display: flex; align-items: center; gap: 7px; }
.dot-live {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--ok); animation: pulse 2.4s ease-out infinite; flex-shrink: 0;
}
.dot-live.off { background: var(--text-2); animation: none; }
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(var(--ok-rgb), 0.55); }
  70% { box-shadow: 0 0 0 5px rgba(var(--ok-rgb), 0); }
  100% { box-shadow: 0 0 0 0 rgba(var(--ok-rgb), 0); }
}
.fh-title { font-size: var(--fs-md); font-weight: 700; color: var(--text); }
.fh-sub { font-size: var(--fs-cap); color: var(--text-3); margin-left: auto; }
.fh-stat { display: flex; gap: 14px; margin-top: 8px; font-size: var(--fs-micro); color: var(--text-2); }
.fh-stat b { color: var(--text); font-size: var(--fs-base); font-variant-numeric: tabular-nums; }
.fh-stat b.amber { color: var(--warn); }

.feed-tools {
  display: flex; gap: 6px; padding: 8px 10px;
  border-bottom: 1px solid var(--border); flex-shrink: 0;
}
.tool {
  flex: 1;
  display: inline-flex; align-items: center; justify-content: center; gap: 4px;
  background: var(--surface-2); color: var(--text-2);
  border: 1px solid var(--border); border-radius: 5px;
  font-size: var(--fs-micro); padding: 6px 8px; cursor: pointer;
  transition: all 0.15s;
}
.tool:hover { color: var(--text); border-color: var(--border-strong); }
.tool.on { color: var(--ok); border-color: rgba(var(--ok-rgb), 0.4); background: rgba(var(--ok-rgb), 0.1); }
.tool.sim { color: var(--warn); border-color: rgba(var(--warn-rgb), 0.35); flex: 0 0 auto; }
.tool.sim:hover { color: var(--warn); border-color: rgba(var(--warn-rgb), 0.6); }

.feed-list { flex: 1; overflow-y: auto; min-height: 0; }
.feed-empty { padding: 24px 12px; text-align: center; color: var(--text-3); font-size: var(--fs-micro); }

.item {
  display: flex; gap: 10px; padding: 10px 11px;
  border-bottom: 1px solid var(--surface-2);
  cursor: pointer;
  border-left: 2px solid transparent;
  transition: background 0.15s, border-color 0.15s;
}
.item:hover { background: var(--surface-3); }
.item.active { background: var(--surface-3); border-left-color: var(--brand); }
/* 新到达：闪一下（高信号，2.6s 后自动消失） */
.item.flash { animation: itemFlash 2.6s ease-out; }
@keyframes itemFlash {
  0% { background: rgba(var(--danger-rgb), 0.22); border-left-color: var(--danger); }
  70% { background: rgba(var(--danger-rgb), 0.08); border-left-color: var(--danger); }
  100% { background: transparent; border-left-color: transparent; }
}

.i-thumb {
  width: 78px; height: 50px; flex-shrink: 0;
  border-radius: 4px; overflow: hidden;
  background: var(--surface-2); border: 1px solid var(--border-strong);
}
.i-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.i-noimg {
  width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
  color: var(--text-3); font-size: var(--fs-base);
}
.i-body { flex: 1; min-width: 0; }
.i-row1 { display: flex; align-items: baseline; gap: 7px; }
.i-time {
  font-size: var(--fs-md); font-weight: 700; color: var(--text);
  font-variant-numeric: tabular-nums;
}
.i-ws {
  font-size: var(--fs-cap); color: var(--ok);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.i-type {
  font-size: var(--fs-base); color: var(--text); font-weight: 600;
  margin-top: 3px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.i-row3 { display: flex; align-items: center; gap: 6px; margin-top: 3px; }
.i-dev {
  font-size: var(--fs-cap); color: var(--text-3);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
/* ★ 违规人数（替代原「未处理/已处理」） */
.i-state { font-size: var(--fs-cap); margin-left: auto; color: var(--danger); font-weight: 700; flex-shrink: 0; }
.i-state.zero { color: var(--text-3); font-weight: 500; }

.feed-foot {
  flex-shrink: 0; padding: 9px 12px;
  border-top: 1px solid var(--border);
  font-size: var(--fs-cap); color: var(--text-3);
  background: var(--surface-2);
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: nowrap;
  white-space: nowrap;
  overflow: hidden;
}
.feed-foot kbd {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 21px;
  background: var(--surface);
  border: 1px solid var(--border-2);
  border-bottom-width: 2px;
  border-radius: var(--r-sm);
  padding: 0 5px;
  font-size: var(--fs-micro);
  color: var(--text-2);
  font-family: inherit;
  font-weight: 700;
  flex-shrink: 0;
}
.feed-foot .k-txt { margin-right: 8px; }
/* ★ 方向键用 CSS 三角画，不依赖字体字形（↑↓ 在部分字体里会渲染成空白） */
.feed-foot .k-arrow { position: relative; padding: 0; }
.feed-foot .k-arrow::before {
  content: '';
  width: 0;
  height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
}
.feed-foot .k-arrow.up::before { border-bottom: 6px solid var(--text-2); }
.feed-foot .k-arrow.down::before { border-top: 6px solid var(--text-2); }

/* ============ 右：大图舞台 ============ */
.stage {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  min-width: 0;
}
.live-shot img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #0b1220;
}

.shot {
  position: relative;
  flex: 1;
  min-height: 0;
  /* ★ 2026-10-26：闲置/失败态时整块是浅灰大白板，看着太空。
     加一层极淡的斜向纹理，让"没有图"也像个有设计的舞台，而不是漏渲染。 */
  background:
    repeating-linear-gradient(
      135deg,
      transparent 0 22px,
      rgba(14, 110, 180, 0.022) 22px 44px
    ),
    var(--stage);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.shot.fresh { animation: shotFlash 2.6s ease-out; }
@keyframes shotFlash {
  0% { border-color: var(--danger); box-shadow: inset 0 0 0 2px rgba(var(--danger-rgb), 0.5); }
  100% { border-color: var(--border); box-shadow: none; }
}
.shot img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  display: block;
}
.shot-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: var(--text-3);
  padding: 24px;
  text-align: center;
}
/* ★ 空态图标底盘：单独一层，避免 el-icon 自带的 flex 把尺寸压扁 */
.shot-empty .se-ico {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 84px;
  height: 84px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.8);
  box-shadow: var(--shadow-2);
  color: var(--border-strong);
  flex-shrink: 0;
}
.se-txt {
  font-size: var(--fs-md);
  font-weight: 700;
  color: var(--text-2);
  max-width: 340px;
  line-height: 1.6;
}
.se-sub {
  font-size: var(--fs-cap);
  color: var(--text-3);
  max-width: 340px;
  line-height: 1.6;
}

.shot-tl {
  position: absolute; top: 10px; left: 12px;
  display: flex; align-items: center; gap: 8px;
  pointer-events: none;
}
.badge-live {
  font-size: var(--fs-cap); font-weight: 700; color: #fff;
  background: rgba(var(--danger-rgb), 0.85);
  border-radius: 4px; padding: 3px 9px;
}
.badge-time {
  font-size: var(--fs-lg); font-weight: 700; color: var(--text);
  font-variant-numeric: tabular-nums;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid var(--border);
  border-radius: 4px; padding: 3px 10px;
}
.badge-ago {
  font-size: var(--fs-micro); color: var(--text-2);
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid var(--border);
  border-radius: 4px; padding: 3px 8px;
}
.shot-tr { position: absolute; top: 10px; right: 12px; pointer-events: none; }
/* ★ 违规人数角标（替代原「未处理/已处理」）：红底白字，大图上最醒目的一处 */
.badge-alarmed {
  font-size: var(--fs-base); font-weight: 700; color: #fff;
  background: var(--danger);
  border: 1px solid #a81f14;
  border-radius: 14px; padding: 4px 14px;
  font-variant-numeric: tabular-nums;
  box-shadow: 0 2px 8px rgba(var(--danger-rgb), 0.4);
}
.badge-alarmed.zero {
  color: var(--text-2);
  background: rgba(255, 255, 255, 0.92);
  border-color: var(--border-strong);
  box-shadow: var(--shadow-1);
  font-weight: 600;
}
/* ★ 异常报警角标闪动（时长可配，与列表、实况画面同一份计时） */
.badge-alarmed.flashing {
  animation: badgeBlink 0.72s steps(1, end) infinite;
  box-shadow: 0 0 0 4px rgba(var(--danger-rgb), 0.45);
}
@keyframes badgeBlink {
  0% { opacity: 1; }
  50% { opacity: 0.35; }
  100% { opacity: 1; }
}
@media (prefers-reduced-motion: reduce) {
  .badge-alarmed.flashing { animation: none; box-shadow: 0 0 0 3px var(--danger); }
}

/* 信息 + 操作条 */
.meta {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 18px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 16px;
  flex-wrap: wrap;
}
.m-main { flex: 1; min-width: 260px; }
.m-type {
  display: flex; align-items: center; gap: 8px;
  font-size: 19px; font-weight: 700; color: var(--text);
}
.m-type .el-icon { color: var(--danger); }
.m-repeat {
  font-size: var(--fs-cap); font-weight: 700; color: var(--warn);
  background: rgba(var(--warn-rgb), 0.14); border-radius: 8px; padding: 0 7px;
}
.m-sum { font-size: 14.5px; color: var(--text-2); margin-top: 5px; }
.m-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 9px; }
.tag {
  font-size: var(--fs-cap); color: var(--text-2);
  background: var(--surface-2); border: 1px solid var(--border);
  border-radius: 4px; padding: 2px 8px;
}
.tag.ws { color: var(--ok); border-color: rgba(var(--ok-rgb), 0.3); background: rgba(var(--ok-rgb), 0.1); }
.tag.v-ready { color: var(--ok); border-color: rgba(var(--ok-rgb), 0.3); }
.tag.v-run { color: var(--warn); border-color: rgba(var(--warn-rgb), 0.3); }

.m-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--surface-2); color: var(--text);
  border: 1px solid var(--border); border-radius: 6px;
  font-size: var(--fs-base); font-weight: 600;
  padding: 9px 16px; cursor: pointer;
  transition: all 0.15s;
}
.btn:hover { border-color: var(--border-strong); color: var(--text); }
.btn.primary { background: var(--brand); border-color: var(--brand); color: #fff; }
.btn.primary:hover:not(:disabled) { background: var(--brand); }
.btn:disabled { opacity: 0.55; cursor: default; }

/* 待机态 */
.idle {
  flex: 1;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 12px;
  background: var(--stage);
  border: 1px dashed var(--border);
  border-radius: 8px;
}
.idle-ring {
  width: 74px; height: 74px; border-radius: 50%;
  border: 1px solid var(--border);
  display: flex; align-items: center; justify-content: center;
}
.idle-dot {
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--ok); animation: pulse 2.8s ease-out infinite;
}
.idle-title { font-size: var(--fs-xl); font-weight: 600; color: var(--text-2); letter-spacing: 0.5px; }
.idle-sub { font-size: var(--fs-micro); color: var(--text-3); text-align: center; line-height: 1.7; }
.idle-sub b.amber { color: var(--warn); }

/* ============ 响应式 ============ */
@media (max-width: 1180px) {
  .live { grid-template-columns: 340px 1fr; }
  .meta { flex-direction: column; align-items: stretch; }
}
@media (max-width: 860px) {
  .live { grid-template-columns: 1fr; grid-template-rows: 300px 1fr; }
}
</style>
