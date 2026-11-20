<script setup lang="ts">
/**
 * ★ 数据分析 —— 从报警看板「数据分析」展开区独立成页。
 *   近 7 天趋势 / 今日时段 / 集中工位 / 车间概况 / 区域×类型汇总。
 */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { Refresh, WarningFilled } from '@element-plus/icons-vue'
import { alarmApi } from '@/api'
import { useAlarmStore } from '@/stores/alarm'
import { useDashboardStore } from '@/stores/dashboard'

const props = defineProps<{ connected?: boolean }>()

const dashboard = useDashboardStore()
dashboard.ensureScope()
const alarms = useAlarmStore()
const data = computed(() => dashboard.data)

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

async function refreshAll(force = true) {
  await Promise.all([dashboard.refresh(force), loadRuleStats()])
}

const updatedLabel = computed(() =>
  dashboard.updatedAt
    ? new Date(dashboard.updatedAt).toLocaleTimeString('zh-CN', { hour12: false })
    : '',
)
const trendMax = computed(() => Math.max(1, ...(data.value?.trend ?? []).map((p) => p.count)))
const hourlyMax = computed(() => Math.max(1, ...(data.value?.hourly ?? []).map((p) => p.count)))
const todayKey = computed(() => {
  const date = new Date(dashboard.updatedAt || Date.now())
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
})

function barHeight(count: number, max: number) {
  return `${count > 0 ? Math.max(2, (count / max) * 100) : 0}%`
}

let poll: number | undefined
let scheduled: number | undefined
function scheduleRefresh() {
  if (scheduled !== undefined) return
  scheduled = window.setTimeout(() => {
    scheduled = undefined
    void refreshAll(true)
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
  if (document.visibilityState === 'visible') void refreshAll(true)
}
onMounted(() => {
  void refreshAll(false)
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
  <div class="page" aria-label="数据分析" :aria-busy="dashboard.refreshing">
    <div class="head">
      <div>
        <div class="title">数据分析</div>
        <div class="sub">按趋势、时段、工位与区域×报警类型汇总今日及近 7 天数据</div>
      </div>
      <div class="head-actions">
        <span class="connection" :class="{ disconnected: !props.connected }">
          <i />{{ props.connected ? '实时推送已连接' : '实时推送重连中' }}
        </span>
        <span class="updated">
          {{ dashboard.refreshing ? '正在更新…' : updatedLabel ? `${updatedLabel} 更新` : '等待数据' }}
        </span>
        <el-button
          :icon="Refresh"
          :loading="dashboard.refreshing"
          @click="refreshAll(true)"
        >
          刷新
        </el-button>
      </div>
    </div>

    <template v-if="data">
      <div class="analysis">
        <div class="analysis-grid">
          <section class="analysis-panel">
            <div class="panel-heading">
              <h3>近 7 天报警</h3>
              <span>原始记录 · 条</span>
            </div>
            <div class="trend-bars">
              <div
                v-for="point in data.trend"
                :key="point.date"
                class="trend-column"
                :class="{ today: point.date === todayKey }"
              >
                <span class="bar-number">{{ point.count }}</span>
                <div class="bar-track">
                  <i
                    :style="{ height: barHeight(point.count, trendMax) }"
                    :title="`${point.date}：${point.count} 条`"
                  />
                </div>
                <span class="bar-label">
                  {{ point.date === todayKey ? '今天' : point.date.slice(5).replace('-', '/') }}
                </span>
              </div>
            </div>
          </section>

          <section class="analysis-panel">
            <div class="panel-heading">
              <h3>今日报警时段</h3>
              <span>原始记录 · 条</span>
            </div>
            <div class="hour-bars">
              <div v-for="point in data.hourly" :key="point.hour" class="hour-column">
                <div class="bar-track">
                  <i
                    :style="{ height: barHeight(point.count, hourlyMax) }"
                    :title="`${point.hour}:00–${point.hour}:59：${point.count} 条`"
                  />
                </div>
                <span class="bar-label">
                  {{ point.hour % 6 === 0 ? `${String(point.hour).padStart(2, '0')}` : '' }}
                </span>
              </div>
            </div>
            <p class="chart-note">
              {{ data.records_today ? `今日累计 ${data.records_today} 条上报记录` : '今日暂无报警记录' }}
            </p>
          </section>

          <section class="analysis-panel">
            <div class="panel-heading">
              <h3>报警集中工位</h3>
              <span>按事件数排序</span>
            </div>
            <div v-if="data.hotspots?.length" class="hotspots">
              <div
                v-for="(spot, index) in data.hotspots"
                :key="`${spot.device_id}-${spot.channel}`"
                class="hotspot"
              >
                <span class="rank" :class="{ first: index === 0 }">{{ index + 1 }}</span>
                <div class="spot-name">
                  <strong :title="`${spot.device_id} / ${spot.channel_name}`">
                    {{ spot.channel_name || `CH${spot.channel}` }}
                  </strong>
                  <span>{{ spot.workshop || '未指派车间' }}</span>
                </div>
                <div class="spot-track">
                  <i :style="{ width: `${Math.min(100, Math.max(0, spot.share))}%` }" />
                </div>
                <span class="spot-count">{{ spot.events }}<small> 次</small></span>
              </div>
            </div>
            <div v-else class="empty-chart">今日暂无报警工位</div>
          </section>
        </div>

        <div v-if="data.workshops?.length" class="workshop-strip">
          <strong>车间概况</strong>
          <span
            v-for="workshop in data.workshops"
            :key="workshop.code"
            class="workshop-item"
          >
            {{ workshop.name }}
            <b>{{ workshop.today }} 条</b>
            <small>在线 {{ workshop.channels_online }}/{{ workshop.channels }}</small>
          </span>
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
              <tr
                v-for="(row, i) in ruleStats"
                :key="`${row.workshop}-${row.rule_name}-${i}`"
              >
                <td>{{ row.workshop_name || row.workshop || '未指派' }}</td>
                <td>{{ row.rule_name || '（未分类）' }}</td>
                <td class="num">{{ row.alarm_count }}</td>
                <td class="num">{{ row.person_sum }}</td>
                <td class="num">{{ row.alarmed_sum }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty-chart short">暂无分类统计数据</div>
        </section>

        <footer class="analysis-foot">
          <span>每个事件平均上报 <b>{{ data.repeat_ratio }}</b> 条</span>
          <span>图片等待配对 <b>{{ data.pending_images }}</b> 张</span>
          <span>
            事件按同一设备、通道、类型及 {{ data.event_window_seconds }} 秒时间窗口归并
          </span>
        </footer>
      </div>
    </template>

    <div v-else-if="dashboard.error" class="load-error" role="status">
      <el-icon><WarningFilled /></el-icon>
      <span>分析数据暂时无法加载，请重试。</span>
      <el-button size="small" @click="refreshAll(true)">重新加载</el-button>
    </div>

    <div v-else class="skeleton" aria-label="正在加载分析数据">
      <div v-for="index in 3" :key="index" class="skel-panel"><span /><b /><span /></div>
    </div>
  </div>
</template>

<style scoped>
.page {
  padding: 16px 20px;
  overflow-y: auto;
  height: 100%;
  min-width: 0;
}
.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.title {
  font-size: var(--fs-xl);
  font-weight: 700;
  color: var(--text);
}
.sub {
  font-size: var(--fs-cap);
  color: var(--text-2);
  margin-top: 4px;
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
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

.analysis {
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
  overflow: hidden;
}
.analysis-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1.15fr;
}
.analysis-panel {
  min-width: 0;
  padding: 20px 22px;
}
.analysis-panel + .analysis-panel {
  border-left: 1px solid var(--border);
}
.panel-heading {
  display: flex;
  align-items: baseline;
  gap: 8px;
  justify-content: space-between;
  margin-bottom: 16px;
}
h3 {
  margin: 0;
  font-size: var(--fs-md);
  font-weight: 650;
  color: var(--text);
}
.panel-heading > span {
  color: var(--text-2);
  font-size: var(--fs-cap);
}

.trend-bars,
.hour-bars {
  display: flex;
  gap: 10px;
  height: 160px;
}
.trend-column,
.hour-column {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 7px;
}
.bar-number {
  color: var(--text-2);
  font-size: var(--fs-cap);
  font-variant-numeric: tabular-nums;
}
.bar-track {
  flex: 1;
  min-height: 0;
  width: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  border-bottom: 1px solid var(--border);
}
.bar-track i {
  display: block;
  width: 62%;
  max-width: 30px;
  background: #b1cde5;
  border-radius: 4px 4px 0 0;
}
.today .bar-track i {
  background: var(--brand);
}
.today .bar-label,
.today .bar-number {
  color: var(--brand);
  font-weight: 650;
}
.bar-label {
  height: 18px;
  font-size: var(--fs-micro);
  color: var(--text-2);
  white-space: nowrap;
}
.hour-bars {
  gap: 4px;
  height: 140px;
  padding-top: 8px;
}
.hour-column {
  gap: 7px;
}
.hour-column .bar-track i {
  width: 100%;
  background: #79a6cb;
  border-radius: 3px 3px 0 0;
}
.chart-note {
  margin: 10px 0 0;
  font-size: var(--fs-cap);
  color: var(--text-2);
}

.hotspots {
  max-height: 220px;
  overflow-y: auto;
}
.hotspot {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 7px 0;
}
.rank {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  border-radius: 5px;
  background: var(--surface-2);
  color: var(--text-2);
  font-size: var(--fs-cap);
}
.rank.first {
  color: var(--brand);
  background: var(--brand-soft);
  font-weight: 700;
}
.spot-name {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
}
.spot-name strong {
  font-size: var(--fs-base);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.spot-name > span {
  font-size: var(--fs-micro);
  color: var(--text-2);
}
.spot-track {
  width: 60px;
  height: 5px;
  border-radius: 3px;
  background: var(--surface-3);
  overflow: hidden;
}
.spot-track i {
  display: block;
  height: 100%;
  background: #79a6cb;
  border-radius: inherit;
}
.spot-count {
  min-width: 45px;
  text-align: right;
  font-weight: 650;
  font-size: var(--fs-md);
  font-variant-numeric: tabular-nums;
}
.spot-count small {
  color: var(--text-2);
  font-size: var(--fs-cap);
  font-weight: 400;
}

.empty-chart {
  display: grid;
  place-items: center;
  min-height: 160px;
  color: var(--text-2);
  font-size: var(--fs-base);
  background: var(--surface-2);
  border-radius: 8px;
}
.empty-chart.short {
  min-height: 96px;
}

.workshop-strip {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
  padding: 14px 22px;
  border-top: 1px solid var(--border);
  font-size: var(--fs-cap);
  color: var(--text-2);
}
.workshop-strip > strong {
  color: var(--text);
}
.workshop-item {
  display: inline-flex;
  gap: 9px;
  align-items: baseline;
}
.workshop-item b {
  color: var(--brand);
  font-weight: 600;
}
.workshop-item small {
  font-size: inherit;
}

.rule-stats {
  padding: 16px 22px 10px;
  border-top: 1px solid var(--border);
}
.rule-stats .panel-heading {
  margin-bottom: 12px;
}
.rule-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--fs-cap);
}
.rule-table th,
.rule-table td {
  text-align: left;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  color: var(--text);
}
.rule-table th {
  color: var(--text-2);
  font-weight: 600;
  background: var(--surface-2);
}
.rule-table .num {
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

.analysis-foot {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 22px;
  padding: 12px 22px;
  background: var(--surface-2);
  border-top: 1px solid var(--border);
  color: var(--text-2);
  font-size: var(--fs-cap);
}
.analysis-foot b {
  color: var(--text);
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

.skeleton {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.skel-panel {
  min-height: 200px;
  padding: 20px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: var(--surface);
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.skel-panel span,
.skel-panel b {
  display: block;
  border-radius: 4px;
  background: var(--surface-3);
  animation: breathe 1.6s ease-in-out infinite;
  width: 55%;
  height: 16px;
}
.skel-panel b {
  width: 38%;
  height: 80px;
}
.skel-panel span:last-child {
  width: 80%;
}

@keyframes breathe {
  50% {
    opacity: 0.45;
  }
}

@media (max-width: 1100px) {
  .analysis-grid {
    grid-template-columns: 1fr;
  }
  .analysis-panel + .analysis-panel {
    border-left: 0;
    border-top: 1px solid var(--border);
  }
  .skeleton {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 700px) {
  .updated {
    display: none;
  }
  .spot-track {
    display: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .skel-panel span,
  .skel-panel b {
    animation: none;
  }
}
</style>
