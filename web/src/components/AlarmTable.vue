<script setup lang="ts">
/**
 * 报警列表（表格）—— 改版 v2。
 *
 * 布局变化：
 *   · 筛选条并入面板头部（工具条），不再浮在面板外，视觉更整体
 *   · ★ 新增「摘要」列（自适应宽度）：填满右侧空间，同时把后端
 *     summary（如「未穿防护服报警，检出 2 人，其中 1 人疑似违规（设备识别）」）摆出来 ——
 *     这是运维扫列表时最需要的信息，原来只能点进详情才看得到
 *   · 缩略图放大到 76×46，行高更稳，扫图更清楚
 *
 * 数据来源：GET /api/alarms（字段见 AlarmBrief）
 */
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { Picture, Refresh, Search, View } from '@element-plus/icons-vue'
import { withToken } from '@/api'
import { alarmTypeText, useAlarmStore } from '@/stores/alarm'
import { useDeviceStore } from '@/stores/device'
import type { AlarmBrief } from '@/types'

const props = defineProps<{
  alarms: AlarmBrief[]
  loading: boolean
  /** ★ 当前实况画面展示的报警 id（点行换图，行上给出同源高亮） */
  focusId?: string | null
}>()

const emit = defineEmits<{
  (e: 'open', a: AlarmBrief): void
  /** ★ 单击行 = 把这张图送到左侧实况画面（不跳页，值守时不打断） */
  (e: 'focus', a: AlarmBrief): void
  (e: 'delete', a: AlarmBrief): void
}>()

const store = useAlarmStore()
const deviceStore = useDeviceStore()

/* ============================================================================
   ★ 每页条数随可用高度自适应（2026-10-26 现场反馈「表格下面一大片空白」）

   原来固定 size=10：1080p 屏上一屏能放 18 行，表格区底部就空出一大块白，
   看起来像"没加载出来"。现在按表格实际可视高度算能放几行。

   ⚠️ 必须用 **布局像素**（clientHeight / offsetHeight），不能用
      getBoundingClientRect()：整页有 `transform: scale(--ui-scale)`，
      后者返回的是**缩放后**的视觉尺寸，拿它除以固定的行高会多算 25% 的行，
      结果就是表格内容溢出、最后几行要滚动才看得到（实测踩过）。
      clientHeight/offsetHeight 不参与 transform，天然就是布局值。

   另外 el-table 的滚动容器 `.el-scrollbar__wrap` 只包**表体**，
   表头是独立的 header-wrapper，所以可用高度不需要再减表头高。
   ========================================================================== */
const panelRef = ref<HTMLElement | null>(null)

function fitSize() {
  const panel = panelRef.value
  if (!panel) return
  const wrap = panel.querySelector('.el-scrollbar__wrap') as HTMLElement | null
  if (!wrap) return // 表格还没挂载（切到别的页签）时不动
  const viewH = wrap.clientHeight
  if (viewH <= 0) return // 隐藏态（display:none）量不到，跳过
  // 行高实测：有数据时量第一行；空表时用兜底值（46px 缩略图 + 上下 padding）
  const rowEl = panel.querySelector('.el-table__body tbody tr') as HTMLElement | null
  const rowH = rowEl?.offsetHeight || 55
  if (rowH <= 0) return
  // 整除时正好铺满（如 385 / 55 = 7 行），不要多减 1 —— 那样会白亏一整行。
  // floor 本身已保证 rows * rowH <= viewH，不会溢出。
  const rows = Math.max(5, Math.min(60, Math.floor(viewH / rowH)))
  if (rows === store.size) return
  store.size = rows
  store.page = 1
  void store.fetchList()
}

let ro: ResizeObserver | null = null
let fitTimer: number | null = null

/** 防抖：拖窗口/缩放时不要每帧都重查 */
function scheduleFit() {
  if (fitTimer !== null) window.clearTimeout(fitTimer)
  fitTimer = window.setTimeout(() => {
    fitTimer = null
    fitSize()
  }, 180)
}

onMounted(() => {
  // 首帧量一次（等 el-table 渲染完）
  window.requestAnimationFrame(() => scheduleFit())
  if (typeof ResizeObserver !== 'undefined' && panelRef.value) {
    ro = new ResizeObserver(() => scheduleFit())
    ro.observe(panelRef.value)
  }
  window.addEventListener('resize', scheduleFit)
})

onUnmounted(() => {
  if (fitTimer !== null) window.clearTimeout(fitTimer)
  ro?.disconnect()
  ro = null
  window.removeEventListener('resize', scheduleFit)
})

/** ★ 焦点行高亮：左侧蓝线 = 当前大图是哪一条 */
function rowClass({ row }: { row: AlarmBrief }): string {
  return row.id === props.focusId ? 'row-focus' : ''
}

/** ★ 报警类型：后端 type_text 优先（AIOP 规则名），回退到类型码映射 */
function typeLabel(a: AlarmBrief): string {
  return a.type_text || alarmTypeText(a.alarm_type)
}

/** ★ 摘要：优先后端 summary；没有时用 extra 里的结构化字段兜底 */
function summaryText(a: AlarmBrief): string {
  if (a.summary) return a.summary
  const e = a.extra || {}
  if (e.person_count != null) {
    return e.alarmed_count
      ? `检出 ${e.person_count} 人，其中 ${e.alarmed_count} 人疑似违规（设备识别）`
      : `检出 ${e.person_count} 人`
  }
  return ''
}

function timeText(t: string): string {
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return t
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(
    d.getMinutes(),
  )}:${pad(d.getSeconds())}`
}

/** 时间列拆两行：上面"时:分"、下面"月-日 秒"，扫读时先看时分 */
function hmText(t: string): string {
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return t
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function secText(t: string): string {
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function fullTime(t: string): string {
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return t
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(
    d.getHours(),
  )}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

/** 该图是否为 AIOP 智能分析告警（决定标签配色） */
function isAiop(a: AlarmBrief): boolean {
  return !!a.extra?.is_aiop
}

/** ★ 违规人数：从 extra 里取（列表用彩色数字直出，比整列状态标签更有信息量） */
function alarmedCount(a: AlarmBrief): number {
  const n = a.extra?.alarmed_count
  return typeof n === 'number' ? n : 0
}

/**
 * ★ 抓拍图筛选（三态 → 后端的 has_image 布尔）
 *
 * 用字符串做 v-model 是为了避开 el-select 里 `undefined`（"全部"）
 * 与清空值混淆的老问题 —— 三态语义写死在映射里更稳。
 * 切换后立即重查（不用点「查询」），因为这是"看什么"的视图开关。
 */
const imageFilter = computed({
  get: () => {
    const v = store.filters.has_image
    return v === true ? 'with' : v === false ? 'none' : 'all'
  },
  set: (v: string) => {
    store.filters.has_image = v === 'with' ? true : v === 'none' ? false : undefined
    store.page = 1
    store.fetchList()
  },
})

function search() {
  store.page = 1
  store.fetchList()
}

function reset() {
  store.resetFilters()
  store.fetchList()
}
</script>

<template>
  <section ref="panelRef" class="panel">
    <!-- 工具条：筛选 + 批量操作 + 计数 -->
    <div class="toolbar">
      <div class="t-left">
        <el-select
          v-model="store.filters.device_id"
          placeholder="全部设备"
          clearable
          size="default"
          style="width: 168px"
        >
          <el-option
            v-for="d in deviceStore.devices"
            :key="d.device_id"
            :label="`${d.device_id}${d.online ? '' : '（离线）'}`"
            :value="d.device_id"
          />
        </el-select>

        <!-- ★ 抓拍图筛选：默认「仅有图片」——配不到图的记录在值守界面上
             只有一行空占位，属于噪声；默认隐藏，需要排查时可切出来看 -->
        <el-select v-model="imageFilter" style="width: 116px">
          <el-option label="仅有图片" value="with" />
          <el-option label="全部" value="all" />
          <el-option label="仅无图片" value="none" />
        </el-select>

        <el-date-picker
          v-model="store.filters.start"
          type="datetime"
          placeholder="开始时间"
          value-format="YYYY-MM-DDTHH:mm:ss"
          style="width: 176px"
        />
        <span class="tilde">~</span>
        <el-date-picker
          v-model="store.filters.end"
          type="datetime"
          placeholder="结束时间"
          value-format="YYYY-MM-DDTHH:mm:ss"
          style="width: 176px"
        />

        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        <el-button :icon="Refresh" @click="reset">重置</el-button>
      </div>

      <div class="t-right">
        <span class="count">共 <b>{{ store.total }}</b> 条</span>
      </div>
    </div>

    <!-- 表格 -->
    <el-table
      v-loading="props.loading"
      :data="props.alarms"
      style="width: 100%"
      height="100%"
      row-key="id"
      :row-class-name="rowClass"
      :row-style="{ cursor: 'pointer' }"
      @row-click="(row: AlarmBrief) => emit('focus', row)"
      @row-dblclick="(row: AlarmBrief) => emit('open', row)"
    >
      <el-table-column label="时间" width="120">
        <template #default="{ row }">
          <div class="time-cell">
            <span class="t-hm">{{ hmText(row.alarm_time) }}</span>
            <span class="t-sec" :title="fullTime(row.alarm_time)">{{ secText(row.alarm_time) }}</span>
          </div>
        </template>
      </el-table-column>

      <!-- ★ 车间：多车间场景下列表要能一眼看出是哪条产线 -->
      <el-table-column label="车间" min-width="132">
        <template #default="{ row }">
          <span v-if="row.workshop" class="ws-chip">{{ row.workshop_name || row.workshop }}</span>
          <span v-else class="ws-none">未指派</span>
        </template>
      </el-table-column>

      <el-table-column label="设备/通道" min-width="150">
        <template #default="{ row }">
          <span class="dev">{{ row.device_id || '未知设备' }}</span>
          <span class="ch">CH{{ row.channel }}</span>
        </template>
      </el-table-column>

      <el-table-column label="报警类型" min-width="168">
        <template #default="{ row }">
          <div class="type-cell">
            <span class="type-dot" :class="{ aiop: isAiop(row) }" />
            <span class="type-name" :title="typeLabel(row)">{{ typeLabel(row) }}</span>
          </div>
        </template>
      </el-table-column>

      <!-- ★ 摘要：把「检出几人/几人疑似违规（设备识别）」直接摆出来，不用点进详情 -->
      <el-table-column label="检测结果" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">
          <div class="sum-cell">
            <span class="summary">{{ summaryText(row) || '—' }}</span>
            <span v-if="row.extra?.repeat_count && row.extra.repeat_count > 1" class="repeat">
              ×{{ row.extra.repeat_count }}
            </span>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="抓拍" width="96" align="center">
        <template #default="{ row }">
          <el-image
            v-if="row.thumbnail_url && !row.media_expired"
            :src="withToken(row.thumbnail_url)"
            :preview-src-list="[withToken(row.thumbnail_url)]"
            fit="cover"
            lazy
            class="thumb"
            preview-teleported
            @click.stop
          >
            <template #error>
              <div class="thumb-empty"><el-icon><Picture /></el-icon></div>
            </template>
          </el-image>
          <div
            v-else
            class="thumb-empty"
            :title="row.media_expired ? '媒体已过期' : '无图片'"
          >
            <el-icon><Picture /></el-icon>
          </div>
        </template>
      </el-table-column>

      <!-- ★ 2026-10-26：原来是「状态」列（未处理/已处理），纯展示看板不需要
           让甲方逐条点处理，已整列移除。这个位置换成**违规人数** —— 同样占
           一格宽度，但给的是"这次卷进了几个人"的客观事实，比状态有用得多。
           新异常仍然闪动（store 计时，到点自动停），只是不再叫"状态"。 -->
      <el-table-column label="设备估算" width="104" align="center">
        <template #default="{ row }">
          <span class="alarmed" :class="{ zero: alarmedCount(row) === 0, flashing: store.isFlashing(row.id) }">
            {{ alarmedCount(row) }}<i v-if="alarmedCount(row) > 0">人</i>
          </span>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="132" align="right">
        <template #default="{ row }">
          <el-button
            type="primary"
            size="small"
            :icon="View"
            @click.stop="emit('open', row)"
          >
            详情
          </el-button>
          <el-button
            type="danger"
            size="small"
            text
            @click.stop="emit('delete', row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>

      <template #empty>
        <el-empty description="暂无报警数据" :image-size="80" />
      </template>
    </el-table>
  </section>
</template>

<style scoped>
.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  overflow: hidden;
  box-shadow: var(--shadow-2);
  /* ★ 合并页里表格要与左侧实况画面对齐高度：工具条固定，表体占满剩余，
     表头常驻、内容区自己滚 —— 分页条因此永远钉在底部（一屏不滚） */
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* ============ 工具条 ============ */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(to bottom, var(--surface-2), var(--surface));
}
.t-left { display: flex; align-items: center; gap: 9px; flex-wrap: wrap; }
.t-right { display: flex; align-items: center; gap: 12px; }
.tilde { color: var(--text-3); font-size: var(--fs-cap); }
.count { font-size: var(--fs-cap); color: var(--text-2); font-weight: 500; }
.count b { color: var(--text); font-size: var(--fs-md); font-weight: 800; font-variant-numeric: tabular-nums; }

/* ============ 单元格 ============ */
/* 时间：上行时分秒（主），下行月-日（辅） */
.time-cell { display: flex; flex-direction: column; line-height: 1.3; }
.t-hm {
  color: var(--text); font-size: var(--fs-md);
  font-variant-numeric: tabular-nums; font-weight: 700;
}
.t-sec { color: var(--text-3); font-size: var(--fs-micro); font-variant-numeric: tabular-nums; }

.dev { color: var(--text); font-size: var(--fs-base); display: block; line-height: 1.35; font-weight: 600; }
.ch {
  color: var(--text-2); font-size: var(--fs-micro);
  background: var(--surface-3); border-radius: var(--r-sm); padding: 1px 6px;
  display: inline-block; margin-top: 3px; font-weight: 600;
}

/* 类型：色点 + 名称（比原来的实心标签更安静，长名字也不挤） */
.type-cell { display: flex; align-items: center; gap: 8px; min-width: 0; }
.type-dot {
  width: 8px; height: 8px; border-radius: 2px; flex-shrink: 0;
  background: var(--brand);
  box-shadow: 0 0 0 3px var(--brand-soft);
}
.type-dot.aiop { background: var(--danger); box-shadow: 0 0 0 3px var(--danger-soft); }
.type-name {
  font-size: var(--fs-base); font-weight: 700; color: var(--text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* 检测结果 */
.sum-cell { display: flex; align-items: center; gap: 8px; min-width: 0; }
.summary { color: var(--text-2); font-size: var(--fs-base); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.repeat {
  flex-shrink: 0; font-size: var(--fs-micro); font-weight: 800;
  color: var(--warn); background: rgba(var(--warn-rgb), 0.14);
  border-radius: var(--r-pill); padding: 1px 8px;
}

/* 车间 chip */
.ws-chip {
  display: inline-block;
  font-size: var(--fs-cap);
  font-weight: 600;
  color: var(--ok);
  background: var(--ok-soft);
  border: 1px solid rgba(var(--ok-rgb), 0.22);
  border-radius: var(--r-sm);
  padding: 2px 9px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ws-none { font-size: var(--fs-cap); color: var(--text-2); }

.thumb {
  width: 80px;
  height: 48px;
  border-radius: var(--r-sm);
  border: 1px solid var(--border-2);
  display: block;
  background: var(--surface-3);
  box-shadow: var(--shadow-1);
}
.thumb-empty {
  width: 80px;
  height: 48px;
  border-radius: var(--r-sm);
  border: 1px dashed var(--border-2);
  background: var(--surface-2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-3);
  margin: 0 auto;
}

/* ============ 违规人数列 ============
   ★ 2026-10-26：原「状态」列（未处理/已处理）已整列移除 ——
     本系统是纯展示看板，甲方不需要逐条点处理。
     这一格换成**违规人数**：同样是醒目的实心胶囊，但内容是客观事实
     （这次检出几个人疑似违规（设备识别）），比"处理没处理"有用。

     视觉沿用上一版验证过的规格：实心底 + 白字 + 14px/700，
     保证 1080p 大屏 80% 缩放后仍看得清（实测对比度 5.3:1）。 */
.alarmed {
  display: inline-flex;
  align-items: baseline;
  justify-content: center;
  gap: 2px;
  min-width: 66px;
  height: 28px;
  padding: 0 12px;
  border-radius: var(--r-pill);
  font-size: var(--fs-md);
  font-weight: 800;
  line-height: 28px;
  letter-spacing: 0.3px;
  border: 1px solid transparent;
  white-space: nowrap;
  vertical-align: middle;
  font-variant-numeric: tabular-nums;
  /* 有违规 → 红色实底（和"报警"同一语义色，不另造颜色） */
  color: #ffffff;
  background: linear-gradient(135deg, var(--danger), #e3543a);
  border-color: #b7261a;
  box-shadow: 0 1px 3px rgba(var(--danger-rgb), 0.4);
}
.alarmed i {
  font-style: normal;
  font-size: var(--fs-micro);
  font-weight: 600;
  opacity: 0.9;
}
/* 0 人疑似违规（设备识别） = 检出但都合规，用中性灰把视觉重量降下来 */
.alarmed.zero {
  color: var(--text-3);
  background: var(--surface-3);
  border-color: var(--border-2);
  box-shadow: none;
  font-weight: 700;
}

/* ★ 新异常闪动（时长可配，默认 15 秒；store 计时，到点自动摘掉 class）。
   硬闪（steps）比渐隐更容易在余光里被捕捉到 —— 值守时常盯着大图，
   列表是余光区域。 */
.alarmed.flashing {
  animation: statusBlink 0.72s steps(1, end) infinite;
  box-shadow: 0 0 0 3px var(--danger-line);
}
@keyframes statusBlink {
  0% { opacity: 1; }
  50% { opacity: 0.35; }
  100% { opacity: 1; }
}
/* 尊重"减少动态效果"偏好：改成常亮红框，不闪 */
@media (prefers-reduced-motion: reduce) {
  .alarmed.flashing { animation: none; box-shadow: 0 0 0 3px var(--danger); }
}

/* 表格微调：行更紧凑、hover 更明确，表头压暗一档 */
:deep(.el-table) {
  --el-table-border-color: var(--border);
  --el-table-header-bg-color: var(--surface-2);
  --el-table-tr-bg-color: var(--surface);
  --el-table-row-hover-bg-color: var(--surface-2);
  font-size: var(--fs-base);
}
/* ★ 行高：由 48px 缩略图 + 上下 4px padding 决定 ≈ 56px。
   字号抬到 --fs-base/--fs-md 后仍能一屏放 16~18 行（表格已自适应行数，
   见 fitSize()），不会出现"字大了就放不下"的问题。 */
:deep(.el-table .el-table__cell) {
  padding: 4px 0;
}
:deep(.el-table .cell) {
  line-height: 1.4;
  padding: 0 12px;
}
:deep(.el-table th.el-table__cell) {
  font-weight: 700;
  color: var(--text-2);
  font-size: var(--fs-md);
  padding: 9px 0;
}
:deep(.el-table__inner-wrapper::before) { background-color: var(--border); }

/* ★ 焦点行：左侧蓝线 + 提亮底色 = 这条就是左边实况画面上的那张图。
   用 inset 阴影而不是 border，避免加边框把行高撑变。 */
:deep(.el-table .row-focus > td.el-table__cell) {
  background: var(--brand-soft);
}
:deep(.el-table .row-focus > td.el-table__cell:first-child) {
  box-shadow: inset 4px 0 0 0 var(--brand);
}
:deep(.el-table .row-focus:hover > td.el-table__cell) {
  background: var(--brand-soft-2);
}
</style>
