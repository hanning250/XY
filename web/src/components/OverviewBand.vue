<script setup lang="ts">
/**
 * ★ 运行概览（报警看板顶部态势带）。
 *   「数据分析」图表/分类汇总已独立到 DataAnalysisView 页面。
 */
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { Bell, Monitor, Picture, Refresh, User, WarningFilled } from '@element-plus/icons-vue'
import { useAlarmStore } from '@/stores/alarm'
import { useDashboardStore } from '@/stores/dashboard'

const props = defineProps<{ connected?: boolean }>()
const emit = defineEmits<{ (e: 'devices'): void }>()
const dashboard = useDashboardStore()
dashboard.ensureScope()
const alarms = useAlarmStore()
const data = computed(() => dashboard.data)

const updatedLabel = computed(() =>
  dashboard.updatedAt
    ? new Date(dashboard.updatedAt).toLocaleTimeString('zh-CN', { hour12: false })
    : '',
)
const notOnline = computed(() =>
  Math.max(0, (data.value?.devices_total ?? 0) - (data.value?.devices_online ?? 0)),
)
const quality = computed(() => data.value?.data_quality)
const notices = computed(() => {
  if (!data.value) return []
  const out: string[] = []
  if (notOnline.value) out.push(`${notOnline.value} 台设备未在线，请到设备管理确认状态`)
  if (quality.value?.total && quality.value.with_image_pct < 80) {
    out.push(`今日 ${quality.value.without_image} 条记录缺少抓拍图`)
  }
  if (data.value.unassigned) out.push(`${data.value.unassigned} 条记录未指派车间`)
  return out
})

let poll: number | undefined
let scheduled: number | undefined
function scheduleRefresh() {
  if (scheduled !== undefined) return
  scheduled = window.setTimeout(() => {
    scheduled = undefined
    void dashboard.refresh(true)
  }, 1500)
}
watch(() => alarms.stats.today, scheduleRefresh)
watch(
  () => props.connected,
  (online, previous) => {
    if (online && previous === false) scheduleRefresh()
  },
)
function onVisible() {
  if (document.visibilityState === 'visible') void dashboard.refresh(true)
}
onMounted(() => {
  void dashboard.refresh()
  poll = window.setInterval(onVisible, 15_000)
  document.addEventListener('visibilitychange', onVisible)
})
onUnmounted(() => {
  window.clearInterval(poll)
  window.clearTimeout(scheduled)
  document.removeEventListener('visibilitychange', onVisible)
})
</script>

<template>
  <section class="board" aria-label="运行概览" :aria-busy="dashboard.refreshing">
    <header class="overview-head">
      <div class="overview-title">
        <span class="title-mark" />
        <h2>运行概览</h2>
        <span class="period">今日</span>
      </div>
      <div class="overview-actions">
        <span class="connection" :class="{ disconnected: !props.connected }">
          <i />{{ props.connected ? '实时推送已连接' : '实时推送重连中' }}
        </span>
        <span class="updated">
          {{ dashboard.refreshing ? '正在更新…' : updatedLabel ? `${updatedLabel} 更新` : '等待数据' }}
        </span>
        <button
          class="icon-button"
          aria-label="刷新概览"
          title="刷新概览"
          :disabled="dashboard.refreshing"
          @click="dashboard.refresh(true)"
        >
          <el-icon :class="{ spinning: dashboard.refreshing }"><Refresh /></el-icon>
        </button>
      </div>
    </header>

    <template v-if="data">
      <div class="metric-grid">
        <article class="metric metric-primary">
          <div class="metric-top"><span>今日报警记录</span><el-icon><Bell /></el-icon></div>
          <div class="metric-value">
            {{ data.records_today.toLocaleString() }}<span>条</span>
          </div>
          <div class="metric-foot">
            归并为 {{ data.events_today.toLocaleString() }} 个事件 · 重复上报可能更新原记录
          </div>
        </article>
        <article class="metric">
          <div class="metric-top"><span>设备估算人次（未核实）</span><el-icon><User /></el-icon></div>
          <div class="metric-value" :class="{ danger: data.people_today > 0 }">
            {{ data.people_today.toLocaleString() }}<span>人次</span>
          </div>
          <div class="metric-foot">海康识别结果，仅供参考，不代表实际人数</div>
        </article>
        <button
          class="metric metric-device"
          aria-label="查看设备管理与在线状态"
          @click="emit('devices')"
        >
          <div class="metric-top"><span>在线设备</span><el-icon><Monitor /></el-icon></div>
          <div class="metric-value" :class="{ warning: notOnline > 0 }">
            {{ data.devices_online }}<span>/ {{ data.devices_total }} 台</span>
          </div>
          <div class="metric-foot">
            <span>
              {{
                data.devices_total
                  ? notOnline
                    ? `${notOnline} 台未在线`
                    : '全部设备在线'
                  : '暂无已登记设备'
              }}
            </span>
            <span class="metric-link">查看设备 →</span>
          </div>
        </button>
        <article class="metric">
          <div class="metric-top"><span>抓拍完整率</span><el-icon><Picture /></el-icon></div>
          <div
            class="metric-value"
            :class="{ warning: quality?.total && quality.with_image_pct < 80 }"
          >
            {{ quality?.total ? quality.with_image_pct : '—' }}
            <span v-if="quality?.total">%</span>
          </div>
          <div class="metric-foot">
            {{
              quality?.total
                ? `有图 ${quality.with_image} 条 / 共 ${quality.total} 条`
                : '今日暂无抓拍记录'
            }}
          </div>
        </article>
      </div>
      <div v-if="dashboard.error || notices.length" class="attention" role="status">
        <el-icon><WarningFilled /></el-icon>
        <strong>{{ dashboard.error ? '更新未完成' : '需要关注' }}</strong>
        <span class="attention-copy">
          {{
            dashboard.error
              ? `暂时显示 ${updatedLabel} 的数据，请重试刷新。`
              : notices.join('；')
          }}
        </span>
      </div>
    </template>

    <div v-else-if="dashboard.error" class="load-error" role="status">
      <el-icon><WarningFilled /></el-icon>
      <span>概览暂时无法加载，报警列表仍可独立使用。</span>
      <button class="retry-btn" @click="dashboard.refresh(true)">重新加载</button>
    </div>
    <div v-else class="metric-grid skeleton" aria-label="正在加载概览">
      <div v-for="index in 4" :key="index" class="metric"><span /><b /><span /></div>
    </div>
  </section>
</template>

<style scoped>
.board {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 18px;
  min-width: 0;
}
.overview-head,
.overview-title,
.overview-actions {
  display: flex;
  align-items: center;
}
.overview-head {
  justify-content: space-between;
  gap: 16px;
  min-height: 32px;
}
.overview-title {
  gap: 10px;
  white-space: nowrap;
}
.title-mark {
  width: 4px;
  height: 18px;
  border-radius: 3px;
  background: var(--brand);
}
h2 {
  margin: 0;
  color: var(--text);
  font-size: var(--fs-lg);
  font-weight: 700;
}
.period {
  font-size: var(--fs-cap);
  color: var(--text-2);
  padding: 2px 8px;
  border-radius: 5px;
  background: var(--surface-3);
}
.overview-actions {
  gap: 14px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.connection,
.updated {
  font-size: var(--fs-cap);
  color: var(--text-2);
}
.connection {
  display: flex;
  align-items: center;
  gap: 7px;
}
.connection i {
  width: 7px;
  height: 7px;
  background: var(--ok);
  border-radius: 50%;
}
.connection.disconnected i {
  background: var(--warn);
}
.connection.disconnected {
  color: var(--warn);
}
button {
  font: inherit;
}
.icon-button,
.retry-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  border: 1px solid var(--border-2);
  background: var(--surface);
  color: var(--text-2);
  border-radius: 7px;
  min-height: 34px;
}
.icon-button {
  width: 34px;
  font-size: var(--fs-md);
}
.retry-btn {
  padding: 5px 12px;
  font-size: var(--fs-cap);
  font-weight: 600;
}
.icon-button:hover,
.retry-btn:hover {
  color: var(--brand);
  border-color: var(--brand-line);
  background: var(--surface-2);
}
.icon-button:disabled {
  opacity: 0.5;
  cursor: default;
}
button:focus-visible {
  outline: 3px solid var(--brand-line);
  outline-offset: 3px;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}
.metric {
  display: flex;
  flex-direction: column;
  text-align: left;
  min-width: 0;
  padding: 18px 20px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: var(--surface);
  box-shadow: 0 2px 4px rgba(26, 50, 79, 0.025);
  color: var(--text);
}
.metric-primary {
  background: #edf5fc;
  border-color: #c9deef;
}
.metric-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: var(--text-2);
  font-size: var(--fs-md);
  font-weight: 600;
}
.metric-top .el-icon {
  font-size: 21px;
  color: #8398ae;
}
.metric-primary .metric-top,
.metric-primary .metric-top .el-icon {
  color: var(--brand-deep);
}
.metric-value {
  font-size: 42px;
  line-height: 1.15;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
  margin: 12px 0 10px;
  letter-spacing: -1px;
}
.metric-primary .metric-value {
  color: var(--brand-deep);
}
.metric-value span {
  margin-left: 7px;
  font-size: var(--fs-base);
  color: var(--text-2);
  font-weight: 500;
  letter-spacing: 0;
}
.metric-value.danger {
  color: var(--danger);
}
.metric-value.warning {
  color: var(--warn);
}
.metric-foot {
  display: flex;
  gap: 5px;
  align-items: center;
  flex-wrap: wrap;
  font-size: var(--fs-cap);
  color: var(--text-2);
  line-height: 1.5;
}
.metric-device {
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.metric-device:hover {
  border-color: var(--brand-line);
  box-shadow: var(--shadow-2);
}
.metric-link {
  margin-left: auto;
  color: var(--brand);
  font-weight: 600;
}
.attention {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 9px 13px;
  background: #fff8ed;
  border: 1px solid #f0dfc4;
  border-radius: 8px;
  color: #855012;
  font-size: var(--fs-cap);
  line-height: 1.6;
}
.attention .el-icon {
  flex-shrink: 0;
  margin-top: 4px;
}
.attention strong {
  white-space: nowrap;
  font-weight: 650;
}
.attention-copy {
  max-height: 3.2em;
  overflow-y: auto;
}
.load-error {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  font-size: var(--fs-base);
  color: var(--text-2);
}
.skeleton .metric {
  gap: 16px;
  min-height: 158px;
}
.skeleton span,
.skeleton b {
  display: block;
  border-radius: 4px;
  background: var(--surface-3);
  animation: breathe 1.6s ease-in-out infinite;
  width: 55%;
  height: 16px;
}
.skeleton b {
  width: 38%;
  height: 38px;
}
.skeleton span:last-child {
  width: 80%;
}
.spinning {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@keyframes breathe {
  50% {
    opacity: 0.45;
  }
}
@media (max-width: 1300px) {
  .metric {
    padding: 15px;
  }
  .overview-actions {
    gap: 8px;
  }
  .updated {
    display: none;
  }
  .metric-value {
    font-size: 36px;
  }
}
@media (max-width: 1000px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 650px) {
  .overview-head {
    align-items: flex-start;
    flex-direction: column;
  }
  .metric-grid {
    gap: 8px;
  }
  .metric {
    padding: 12px;
  }
  .metric-value {
    font-size: 30px;
  }
  .metric-top .el-icon {
    display: none;
  }
  .connection {
    font-size: var(--fs-micro);
  }
}
@media (prefers-reduced-motion: reduce) {
  .spinning,
  .skeleton span,
  .skeleton b {
    animation: none;
  }
}
</style>
