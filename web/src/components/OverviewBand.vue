<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ArrowDown, Bell, Monitor, Picture, Refresh, User, WarningFilled } from '@element-plus/icons-vue'
import { alarmApi } from '@/api'
import { useAlarmStore } from '@/stores/alarm'
import { useDashboardStore } from '@/stores/dashboard'

const props = defineProps<{ connected?: boolean }>()
const emit = defineEmits<{ (e: 'devices'): void }>()
const dashboard = useDashboardStore()
dashboard.ensureScope()
const alarms = useAlarmStore()
const data = computed(() => dashboard.data)
const expanded = ref(localStorage.getItem('isup_board_expanded') === '1')

/** 区域 × 报警类型分类统计（甲方③） */
type RuleStat = {
  workshop: string | null
  workshop_name?: string
  rule_name: string
  alarm_count: number
  person_sum: number
  alarmed_sum: number
}
const ruleStats = ref<RuleStat[]>([])
const ruleStatsNote = ref('')
async function loadRuleStats() {
  try {
    const res = await alarmApi.byWorkshopRule()
    ruleStats.value = res.items || []
    ruleStatsNote.value = res.note || ''
  } catch {
    ruleStats.value = []
  }
}
const updatedLabel = computed(() => dashboard.updatedAt
  ? new Date(dashboard.updatedAt).toLocaleTimeString('zh-CN', { hour12: false }) : '')
const notOnline = computed(() => Math.max(0, (data.value?.devices_total ?? 0) - (data.value?.devices_online ?? 0)))
const quality = computed(() => data.value?.data_quality)
const trendMax = computed(() => Math.max(1, ...(data.value?.trend ?? []).map(p => p.count)))
const hourlyMax = computed(() => Math.max(1, ...(data.value?.hourly ?? []).map(p => p.count)))
const todayKey = computed(() => {
  const date = new Date(dashboard.updatedAt || Date.now())
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
})
const notices = computed(() => {
  if (!data.value) return []
  const out: string[] = []
  if (notOnline.value) out.push(`${notOnline.value} 台设备未在线，请到设备管理确认状态`)
  if (quality.value?.total && quality.value.with_image_pct < 80) out.push(`今日 ${quality.value.without_image} 条记录缺少抓拍图`)
  if (data.value.unassigned) out.push(`${data.value.unassigned} 条记录未指派车间`)
  return out
})
function toggleExpand() {
  expanded.value = !expanded.value
  localStorage.setItem('isup_board_expanded', expanded.value ? '1' : '0')
}
function barHeight(count: number, max: number) {
  return `${count > 0 ? Math.max(2, count / max * 100) : 0}%`
}
let poll: number | undefined
let scheduled: number | undefined
// Coalesce alarm bursts; navigation and concurrent triggers share the store request.
function scheduleRefresh() {
  if (scheduled !== undefined) return
  scheduled = window.setTimeout(() => {
    scheduled = undefined
    void dashboard.refresh(true)
    void loadRuleStats()
  }, 1500)
}
watch(() => alarms.stats.today, scheduleRefresh)
watch(() => props.connected, (online, previous) => {
  if (online && previous === false) scheduleRefresh()
})
function onVisible() {
  if (document.visibilityState === 'visible') void dashboard.refresh(true)
}
onMounted(() => {
  void dashboard.refresh()
  void loadRuleStats()
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
      <div class="overview-title"><span class="title-mark" /><h2>运行概览</h2><span class="period">今日</span></div>
      <div class="overview-actions">
        <span class="connection" :class="{ disconnected: !props.connected }"><i />{{ props.connected ? '实时推送已连接' : '实时推送连接中' }}</span>
        <span class="updated">{{ dashboard.refreshing ? '正在更新…' : updatedLabel ? `${updatedLabel} 更新` : '等待数据' }}</span>
        <button class="icon-button" aria-label="刷新概览" title="刷新概览" :disabled="dashboard.refreshing" @click="dashboard.refresh(true)"><el-icon :class="{ spinning: dashboard.refreshing }"><Refresh /></el-icon></button>
        <button class="analysis-toggle" :aria-expanded="expanded" aria-controls="overview-analysis" @click="toggleExpand">{{ expanded ? '收起分析' : '数据分析' }}<el-icon :class="{ rotated: expanded }"><ArrowDown /></el-icon></button>
      </div>
    </header>
    <template v-if="data">
      <div class="metric-grid">
        <article class="metric metric-primary">
          <div class="metric-top"><span>今日报警记录</span><el-icon><Bell /></el-icon></div>
          <div class="metric-value">{{ data.records_today.toLocaleString() }}<span>条</span></div>
          <div class="metric-foot">归并为 {{ data.events_today.toLocaleString() }} 个事件 · 重复上报可能更新原记录</div>
        </article>
        <article class="metric">
          <div class="metric-top"><span>设备估算人次（未核实）</span><el-icon><User /></el-icon></div>
          <div class="metric-value" :class="{ danger: data.people_today > 0 }">{{ data.people_today.toLocaleString() }}<span>人次</span></div>
          <div class="metric-foot">海康识别结果，仅供参考，不代表实际人数</div>
        </article>
        <button class="metric metric-device" @click="emit('devices')" aria-label="查看设备管理与在线状态">
          <div class="metric-top"><span>在线设备</span><el-icon><Monitor /></el-icon></div>
          <div class="metric-value" :class="{ warning: notOnline > 0 }">{{ data.devices_online }}<span>/ {{ data.devices_total }} 台</span></div>
          <div class="metric-foot"><span>{{ data.devices_total ? (notOnline ? `${notOnline} 台未在线` : '全部设备在线') : '暂无已登记设备' }}</span><span class="metric-link">查看设备 →</span></div>
        </button>
        <article class="metric">
          <div class="metric-top"><span>抓拍完整率</span><el-icon><Picture /></el-icon></div>
          <div class="metric-value" :class="{ warning: quality?.total && quality.with_image_pct < 80 }">{{ quality?.total ? quality.with_image_pct : '—' }}<span v-if="quality?.total">%</span></div>
          <div class="metric-foot">{{ quality?.total ? `有图 ${quality.with_image} 条 / 共 ${quality.total} 条` : '今日暂无抓拍记录' }}</div>
        </article>
      </div>
      <div v-if="dashboard.error || notices.length" class="attention" role="status">
        <el-icon><WarningFilled /></el-icon><strong>{{ dashboard.error ? '更新未完成' : '需要关注' }}</strong>
        <span class="attention-copy">{{ dashboard.error ? `暂时显示 ${updatedLabel} 的数据，请重试刷新。` : notices.join('；') }}</span>
      </div>
      <div v-if="expanded" id="overview-analysis" class="analysis">
        <div class="analysis-grid">
          <section class="analysis-panel">
            <div class="panel-heading"><h3>近 7 天报警</h3><span>原始记录 · 条</span></div>
            <div class="trend-bars">
              <div v-for="point in data.trend" :key="point.date" class="trend-column" :class="{ today: point.date === todayKey }">
                <span class="bar-number">{{ point.count }}</span>
                <div class="bar-track"><i :style="{ height: barHeight(point.count, trendMax) }" :title="`${point.date}：${point.count} 条`" /></div>
                <span class="bar-label">{{ point.date === todayKey ? '今天' : point.date.slice(5).replace('-', '/') }}</span>
              </div>
            </div>
          </section>
          <section class="analysis-panel">
            <div class="panel-heading"><h3>今日报警时段</h3><span>原始记录 · 条</span></div>
            <div class="hour-bars">
              <div v-for="point in data.hourly" :key="point.hour" class="hour-column">
                <div class="bar-track"><i :style="{ height: barHeight(point.count, hourlyMax) }" :title="`${point.hour}:00–${point.hour}:59：${point.count} 条`" /></div>
                <span class="bar-label">{{ point.hour % 6 === 0 ? `${String(point.hour).padStart(2, '0')}` : '' }}</span>
              </div>
            </div>
            <p class="chart-note">{{ data.records_today ? `今日累计 ${data.records_today} 条上报记录` : '今日暂无报警记录' }}</p>
          </section>
          <section class="analysis-panel">
            <div class="panel-heading"><h3>报警集中工位</h3><span>按事件数排序</span></div>
            <div v-if="data.hotspots?.length" class="hotspots">
              <div v-for="(spot, index) in data.hotspots" :key="`${spot.device_id}-${spot.channel}`" class="hotspot">
                <span class="rank" :class="{ first: index === 0 }">{{ index + 1 }}</span>
                <div class="spot-name"><strong :title="`${spot.device_id} / ${spot.channel_name}`">{{ spot.channel_name || `CH${spot.channel}` }}</strong><span>{{ spot.workshop || '未指派车间' }}</span></div>
                <div class="spot-track"><i :style="{ width: `${Math.min(100, Math.max(0, spot.share))}%` }" /></div>
                <span class="spot-count">{{ spot.events }}<small> 次</small></span>
              </div>
            </div>
            <div v-else class="empty-chart">今日暂无报警工位</div>
          </section>
        </div>
        <div v-if="data.workshops?.length" class="workshop-strip">
          <strong>车间概况</strong><span v-for="workshop in data.workshops" :key="workshop.code" class="workshop-item">{{ workshop.name }}<b>{{ workshop.today }} 条</b><small>在线 {{ workshop.channels_online }}/{{ workshop.channels }}</small></span>
        </div>
        <section class="rule-stats">
          <div class="panel-heading">
            <h3>按区域 × 报警类型汇总</h3>
            <span>{{ ruleStatsNote || '人次为设备估算' }}</span>
          </div>
          <table v-if="ruleStats.length" class="rule-table">
            <thead>
              <tr>
                <th>区域</th>
                <th>报警类型</th>
                <th>报警条数</th>
                <th>设备估算人次</th>
                <th>违规人次</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in ruleStats" :key="`${row.workshop}-${row.rule_name}-${i}`">
                <td>{{ row.workshop_name || row.workshop || '未指派' }}</td>
                <td>{{ row.rule_name || '（未分类）' }}</td>
                <td class="num">{{ row.alarm_count }}</td>
                <td class="num">{{ row.person_sum }}</td>
                <td class="num">{{ row.alarmed_sum }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty-chart">暂无分类统计数据</div>
        </section>
        <footer class="analysis-foot">
          <span>每个事件平均上报 <b>{{ data.repeat_ratio }}</b> 条</span><span>图片等待配对 <b>{{ data.pending_images }}</b> 张</span><span>事件按同一设备、通道、类型及 {{ data.event_window_seconds }} 秒时间窗口归并</span>
        </footer>
      </div>
    </template>
    <div v-else-if="dashboard.error" class="load-error" role="status"><el-icon><WarningFilled /></el-icon><span>概览暂时无法加载，报警列表仍可独立使用。</span><button class="analysis-toggle" @click="dashboard.refresh(true)">重新加载</button></div>
    <div v-else class="metric-grid skeleton" aria-label="正在加载概览"><div v-for="index in 4" :key="index" class="metric"><span /><b /><span /></div></div>
  </section>
</template>

<style scoped>
.board { display: flex; flex-direction: column; gap: 12px; margin-bottom: 18px; min-width: 0; }
.overview-head, .overview-title, .overview-actions { display: flex; align-items: center; }
.overview-head { justify-content: space-between; gap: 16px; min-height: 32px; }
.overview-title { gap: 10px; white-space: nowrap; }
.title-mark { width: 4px; height: 18px; border-radius: 3px; background: var(--brand); }
h2, h3 { margin: 0; color: var(--text); }
h2 { font-size: var(--fs-lg); font-weight: 700; }
.period { font-size: var(--fs-cap); color: var(--text-2); padding: 2px 8px; border-radius: 5px; background: var(--surface-3); }
.overview-actions { gap: 14px; flex-wrap: wrap; justify-content: flex-end; }
.connection, .updated { font-size: var(--fs-cap); color: var(--text-2); }
.connection { display: flex; align-items: center; gap: 7px; }
.connection i { width: 7px; height: 7px; background: var(--ok); border-radius: 50%; }
.connection.disconnected i { background: var(--warn); }
.connection.disconnected { color: var(--warn); }
button { font: inherit; }
.icon-button, .analysis-toggle { display: inline-flex; align-items: center; justify-content: center; gap: 8px; cursor: pointer; border: 1px solid var(--border-2); background: var(--surface); color: var(--text-2); border-radius: 7px; min-height: 34px; }
.icon-button { width: 34px; font-size: var(--fs-md); }
.analysis-toggle { padding: 5px 12px; font-size: var(--fs-cap); font-weight: 600; }
.analysis-toggle:hover, .icon-button:hover { color: var(--brand); border-color: var(--brand-line); background: var(--surface-2); }
.icon-button:disabled { opacity: .5; cursor: default; }
button:focus-visible { outline: 3px solid var(--brand-line); outline-offset: 3px; }
.analysis-toggle .el-icon { transition: transform .2s; }
.rotated { transform: rotate(180deg); }
.metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.metric { display: flex; flex-direction: column; text-align: left; min-width: 0; padding: 18px 20px; border-radius: 12px; border: 1px solid var(--border); background: var(--surface); box-shadow: 0 2px 4px rgba(26, 50, 79, .025); color: var(--text); }
.metric-primary { background: #edf5fc; border-color: #c9deef; }
.metric-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; color: var(--text-2); font-size: var(--fs-md); font-weight: 600; }
.metric-top .el-icon { font-size: 21px; color: #8398ae; }
.metric-primary .metric-top, .metric-primary .metric-top .el-icon { color: var(--brand-deep); }
.metric-value { font-size: 42px; line-height: 1.15; font-weight: 750; font-variant-numeric: tabular-nums; margin: 12px 0 10px; letter-spacing: -1px; }
.metric-primary .metric-value { color: var(--brand-deep); }
.metric-value span { margin-left: 7px; font-size: var(--fs-base); color: var(--text-2); font-weight: 500; letter-spacing: 0; }
.metric-value.danger { color: var(--danger); }
.metric-value.warning { color: var(--warn); }
.metric-foot { display: flex; gap: 5px; align-items: center; flex-wrap: wrap; font-size: var(--fs-cap); color: var(--text-2); line-height: 1.5; }
.metric-foot strong { font-weight: 650; }
.metric-device { cursor: pointer; transition: border-color .15s, box-shadow .15s; }
.metric-device:hover { border-color: var(--brand-line); box-shadow: var(--shadow-2); }
.metric-link { margin-left: auto; color: var(--brand); font-weight: 600; }
.attention { display: flex; align-items: flex-start; gap: 9px; padding: 9px 13px; background: #fff8ed; border: 1px solid #f0dfc4; border-radius: 8px; color: #855012; font-size: var(--fs-cap); line-height: 1.6; }
.attention .el-icon { flex-shrink: 0; margin-top: 4px; }
.attention strong { white-space: nowrap; font-weight: 650; }
.attention-copy { max-height: 3.2em; overflow-y: auto; }
.analysis { max-height: 310px; overflow-y: auto; border: 1px solid var(--border); border-radius: 12px; background: var(--surface); scrollbar-gutter: stable; }
.analysis-grid { display: grid; grid-template-columns: 1fr 1fr 1.15fr; }
.analysis-panel { min-width: 0; padding: 18px 20px; }
.analysis-panel + .analysis-panel { border-left: 1px solid var(--border); }
.panel-heading { display: flex; align-items: baseline; gap: 8px; justify-content: space-between; margin-bottom: 16px; }
h3 { font-size: var(--fs-md); font-weight: 650; }
.panel-heading > span { color: var(--text-2); font-size: var(--fs-cap); }
.trend-bars, .hour-bars { display: flex; gap: 10px; height: 135px; }
.trend-column, .hour-column { flex: 1; min-width: 0; display: flex; flex-direction: column; align-items: center; gap: 7px; }
.bar-number { color: var(--text-2); font-size: var(--fs-cap); font-variant-numeric: tabular-nums; }
.bar-track { flex: 1; min-height: 0; width: 100%; display: flex; align-items: flex-end; justify-content: center; border-bottom: 1px solid var(--border); }
.bar-track i { display: block; width: 62%; max-width: 30px; background: #b1cde5; border-radius: 4px 4px 0 0; }
.today .bar-track i { background: var(--brand); }
.today .bar-label, .today .bar-number { color: var(--brand); font-weight: 650; }
.bar-label { height: 18px; font-size: var(--fs-micro); color: var(--text-2); white-space: nowrap; }
.hour-bars { gap: 4px; height: 116px; padding-top: 8px; }
.hour-column { gap: 7px; }
.hour-column .bar-track i { width: 100%; background: #79a6cb; border-radius: 3px 3px 0 0; }
.chart-note { margin: 10px 0 0; font-size: var(--fs-cap); color: var(--text-2); }
.hotspots { max-height: 153px; overflow-y: auto; }
.hotspot { display: flex; gap: 10px; align-items: center; padding: 7px 0; }
.rank { flex-shrink: 0; width: 22px; height: 22px; display: grid; place-items: center; border-radius: 5px; background: var(--surface-2); color: var(--text-2); font-size: var(--fs-cap); }
.rank.first { color: var(--brand); background: var(--brand-soft); font-weight: 700; }
.spot-name { min-width: 0; flex: 1; display: flex; flex-direction: column; }
.spot-name strong { font-size: var(--fs-base); font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.spot-name > span { font-size: var(--fs-micro); color: var(--text-2); }
.spot-track { width: 60px; height: 5px; border-radius: 3px; background: var(--surface-3); overflow: hidden; }
.spot-track i { display: block; height: 100%; background: #79a6cb; border-radius: inherit; }
.spot-count { min-width: 45px; text-align: right; font-weight: 650; font-size: var(--fs-md); font-variant-numeric: tabular-nums; }
.spot-count small { color: var(--text-2); font-size: var(--fs-cap); font-weight: 400; }
.empty-chart { display: grid; place-items: center; min-height: 135px; color: var(--text-2); font-size: var(--fs-base); background: var(--surface-2); border-radius: 8px; }
.workshop-strip { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; padding: 12px 20px; border-top: 1px solid var(--border); font-size: var(--fs-cap); color: var(--text-2); }
.workshop-strip > strong { color: var(--text); }
.workshop-item { display: inline-flex; gap: 9px; align-items: baseline; }
.workshop-item b { color: var(--brand); font-weight: 600; }
.workshop-item small { font-size: inherit; }
.rule-stats { padding: 14px 20px 8px; border-top: 1px solid var(--border); }
.rule-stats .panel-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
.rule-stats .panel-heading span { font-size: var(--fs-cap); color: var(--text-2); }
.rule-table { width: 100%; border-collapse: collapse; font-size: var(--fs-cap); }
.rule-table th, .rule-table td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border); color: var(--text); }
.rule-table th { color: var(--text-2); font-weight: 600; background: var(--surface-2); }
.rule-table .num { text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; }
.analysis-foot { display: flex; flex-wrap: wrap; gap: 8px 22px; padding: 10px 20px; background: var(--surface-2); border-top: 1px solid var(--border); color: var(--text-2); font-size: var(--fs-cap); }
.analysis-foot b { color: var(--text); }
.load-error { display: flex; align-items: center; gap: 12px; padding: 24px; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; font-size: var(--fs-base); color: var(--text-2); }
.skeleton .metric { gap: 16px; min-height: 158px; }
.skeleton span, .skeleton b { display: block; border-radius: 4px; background: var(--surface-3); animation: breathe 1.6s ease-in-out infinite; width: 55%; height: 16px; }
.skeleton b { width: 38%; height: 38px; }
.skeleton span:last-child { width: 80%; }
.spinning { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes breathe { 50% { opacity: .45; } }
@media (max-width: 1300px) {
  .metric { padding: 15px; }
  .overview-actions { gap: 8px; }
  .updated { display: none; }
  .metric-value { font-size: 36px; }
  .spot-track { display: none; }
}
@media (max-width: 1000px) {
  .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .analysis-grid { grid-template-columns: 1fr; }
  .analysis-panel + .analysis-panel { border-left: 0; border-top: 1px solid var(--border); }
}
@media (max-width: 650px) {
  .overview-head { align-items: flex-start; flex-direction: column; }
  .metric-grid { gap: 8px; }
  .metric { padding: 12px; }
  .metric-value { font-size: 30px; }
  .metric-top .el-icon { display: none; }
  .connection { font-size: var(--fs-micro); }
}
@media (prefers-reduced-motion: reduce) { .spinning, .skeleton span, .skeleton b { animation: none; } }
</style>
