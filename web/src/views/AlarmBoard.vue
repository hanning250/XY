<script setup lang="ts">
/**
 * ★ 主框架 —— 侧边栏多页面切换。
 *
 * 页面（2026-10 改版：数据看板 + 实时画面 + 报警列表合并为同一页
 *       「报警看板」—— 一屏完成 看态势 → 看图 → 处置 闭环）：
 *   alarm     报警看板（态势带 + 实况画面 + 报警列表 + 详情）
 *   live      实时监控（值守大屏：左流右图，保留原交互）
 *   device    设备管理（admin 可改绑定车间；子账号只读本车间）
 *   workshop  车间管理（仅 admin）
 *   user      用户管理（仅 admin）
 *
 * 其余：WebSocket 实时推送、新报警弹窗、断线提示。
 */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Monitor } from '@element-plus/icons-vue'
import AppSidebar from '@/components/AppSidebar.vue'
import AppTopbar from '@/components/AppTopbar.vue'
import AlarmFullscreen from '@/components/AlarmFullscreen.vue'
import AlarmTable from '@/components/AlarmTable.vue'
import LicensePanel from '@/components/LicensePanel.vue'
import LiveFocusPanel from '@/components/LiveFocusPanel.vue'
import LicenseGate from '@/components/LicenseGate.vue'
import NewAlarmToast from '@/components/NewAlarmToast.vue'
import OverviewBand from '@/components/OverviewBand.vue'
import LiveMonitorView from '@/views/LiveMonitorView.vue'
import DeviceManageView from '@/views/DeviceManageView.vue'
import WorkshopManageView from '@/views/WorkshopManageView.vue'
import UserManageView from '@/views/UserManageView.vue'
import AlarmDetailView from '@/views/AlarmDetailView.vue'
import { tokenStore } from '@/api'
import { useAuth } from '@/stores/auth'
import { useAlarmStore } from '@/stores/alarm'
import { useLicense } from '@/stores/license'
import { useAlarmSocket } from '@/composables/useAlarmSocket'
import { useAlarmSound } from '@/composables/useAlarmSound'
import type { AlarmBrief } from '@/types'

const store = useAlarmStore()
const auth = useAuth()

/** 当前页面（默认进「报警看板」—— 看板、实况、列表、处置都在这一页） */
const navKey = ref('alarm')

/** 报警页内部视图：board（列表） / detail（详情） */
const view = ref<'board' | 'detail'>('board')
const selected = ref<AlarmBrief | null>(null)

/* ---------------- 实况画面焦点（与列表联动） ---------------- */
/**
 * ★ 合并页的核心：左侧实况画面永远显示"当前关注的那一条"。
 *   · 点列表行 → 焦点切到该条（不跳页）
 *   · 跟随开启 → 新报警到达自动切到最新 + 红框闪一下
 *   同一份焦点数据喂给列表高亮与画面，两边永远一致。
 */
const focus = ref<AlarmBrief | null>(null)
/** 跟随最新（默认开；手动翻看历史即自动暂停） */
const follow = ref(true)
/** 新报警到达的闪烁标记 */
const flash = ref(false)
let flashTimer: number | null = null
/** 首次加载完成前不闪（否则刷新页面会白闪一次） */
let headSeen: string | null = null

const focusIndex = computed(() =>
  focus.value ? store.items.findIndex((a) => a.id === focus.value!.id) + 1 : 0,
)

/** ★ 列表头部变化时：跟随开启就自动切到最新一条（闪动/出声只针对异常，走 WS 分支） */
watch(
  () => store.items[0]?.id,
  (newId) => {
    if (!newId) return
    const fresh = store.items[0]
    const isFirstLoad = headSeen === null
    headSeen = newId
    if (isFirstLoad || follow.value) focus.value = fresh
  },
)

/** 列表刷新后用新对象替换焦点（保持 handled / video 状态最新），并兜底初始焦点 */
watch(
  () => store.items,
  (v) => {
    if (!v.length) {
      focus.value = null
      return
    }
    const cur = focus.value
    const same = cur ? v.find((a) => a.id === cur.id) : null
    focus.value = same ?? v[0]
  },
)

/** 新异常：实况画面红框闪动，与状态框同样时长（可配，默认 15 秒） */
function flashNew() {
  flash.value = true
  if (flashTimer !== null) window.clearTimeout(flashTimer)
  flashTimer = window.setTimeout(() => {
    flash.value = false
    flashTimer = null
  }, store.FLASH_MS)
}

/** 手动点行选图（暂停跟随，避免下一帧被新报警抢走） */
function focusOn(a: AlarmBrief) {
  focus.value = a
  follow.value = false
}

/** delta = 列表内偏移：-1 更新、+1 更旧（列表最新在最上） */
function moveFocus(delta: number) {
  const list = store.items
  if (!list.length) return
  const cur = focus.value ? list.findIndex((a) => a.id === focus.value!.id) : 0
  const next = Math.min(Math.max((cur < 0 ? 0 : cur) + delta, 0), list.length - 1)
  focusOn(list[next])
}

function setFollow(on: boolean) {
  follow.value = on
  if (on && store.items.length) focus.value = store.items[0]
}

function toggleFollow() {
  setFollow(!follow.value)
}

/** ★ 新报警弹窗：只在真正的新报警到达时弹出 */
const toastAlarm = ref<AlarmBrief | null>(null)
let toastTimer: number | null = null

/**
 * ★ 全屏报警浮层（现场值守"糊屏"提醒）。
 *
 * 与 toast 的分工：
 *   · 检出违规（isAbnormal=true）→ **全屏**，小 toast 不再弹（否则两层叠着，吵）
 *   · 其余报警（移动侦测、遮挡等噪声）→ 仍走小 toast，不打断值守
 * 关掉全屏后不补弹 toast：这个窗口足够看清，再弹一次只是打扰。
 */
const fullscreenAlarm = ref<AlarmBrief | null>(null)

function showFullscreen(a: AlarmBrief) {
  // 连发多条时新的顶掉旧的（排队糊屏比漏看更糟）
  fullscreenAlarm.value = a
  closeToast()
}

function closeFullscreen() {
  fullscreenAlarm.value = null
}

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    live: '实时监控',
    alarm: '报警看板',
    device: '设备管理',
    workshop: '车间管理',
    user: '用户管理',
  }
  return titles[navKey.value] || ''
})

/** 详情页可能来自「实时监控」或「报警查询」，返回时回到来源页 */
const detailFrom = ref<'live' | 'alarm'>('alarm')

const showTopbar = computed(
  () => view.value !== 'detail',
)

/* ---------------- WebSocket ---------------- */
const { play: playAlarmSound } = useAlarmSound()

/**
 * ★ 是否"检出异常结果"。
 *
 * 本项目的业务告警是 AIOP 防护服检测：extra.alarmed_count = 违规人数。
 *   有值 → 按值判断；为 0 说明检出人都合规，不该响；
 *   缺值（老数据/其他规则）→ AIOP 告警按异常处理，非 AIOP（移动侦测等）不响。
 */
function isAbnormal(a: AlarmBrief): boolean {
  const n = a.extra?.alarmed_count
  if (typeof n === 'number') return n > 0
  return !!a.extra?.is_aiop
}

const { connected, connect } = useAlarmSocket(
  (alarm) => {
    const isNew = !store.items.some((a) => a.id === alarm.id)
    store.prepend(alarm)

    void store.fetchStats()
    if (!isNew) return

    // ★ 新报警 → 弹窗 + 刷新统计
    //   检出违规的走全屏（现场大屏看不清 330px 的小 toast），其余走小 toast。
    showToast(alarm)

    // ★ 检出异常结果：全屏 + 声音报警 + 状态框闪动（三处同一个时长口径，可配）
    if (isAbnormal(alarm)) {
      showFullscreen(alarm)
      playAlarmSound()
      store.markFlash(alarm.id)
      flashNew()
      if (follow.value) focus.value = alarm
    }
  },
  () => {
    // 断线重连后补拉，避免漏掉断线期间的数据
    store.fetchList()
    store.fetchStats()
  },
  {
    onDeleted: (ids) => {
      store.removeByIds(ids)
      store.fetchStats()
    },
    onUpdated: (alarm) => {
      store.prepend(alarm)
      store.fetchStats()
      if (navKey.value === 'alarm' && view.value === 'detail' && selected.value?.id === alarm.id) {
        store.fetchDetail(alarm.id)
      }
    },
  },
)

/** 弹出新报警提示；6 秒后自动收起（避免堆积） */
function showToast(a: AlarmBrief) {
  toastAlarm.value = a
  if (toastTimer !== null) window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => {
    toastAlarm.value = null
    toastTimer = null
  }, 6000)
}

function closeToast() {
  toastAlarm.value = null
  if (toastTimer !== null) {
    window.clearTimeout(toastTimer)
    toastTimer = null
  }
}

/* ---------------- 报警页交互 ---------------- */
function openDetail(a: AlarmBrief) {
  // 记住从哪个页面进的详情，返回时回到原页（值守页 or 查询页）
  detailFrom.value = navKey.value === 'live' ? 'live' : 'alarm'
  selected.value = a
  view.value = 'detail'
  closeToast()
  // ★ 从全屏报警点「查看详情」进来时，浮层必须一起收掉
  closeFullscreen()
}

function backToBoard() {
  view.value = 'board'
  selected.value = null
  // ★ 从值守页进来的，返回值守页
  navKey.value = detailFrom.value
  // ★ 不重拉列表：store 里的数据还在，重拉只会盖一层无意义的 loading。
  //   在详情页停留期间的增量由 WebSocket 实时推送维护；
  //   红点统计静默刷新（不触发表格遮罩）。
  store.fetchStats()
}

/** ★ 删除（连磁盘文件一起删） */
async function onDelete(a: AlarmBrief) {
  const { ElMessageBox } = await import('element-plus')
  try {
    await ElMessageBox.confirm(
      `确定删除该报警吗？\n关联的图片与视频文件也会一并删除，且不可恢复。`,
      '删除报警',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  await store.removeOne(a.id)
  if (selected.value?.id === a.id) backToBoard()
  await store.fetchStats()
  ElMessage.success('已删除')
}

/** 侧边栏切换页面时联动（进入报警页时确保列表最新） */
function onNav(key: string) {
  navKey.value = key
  // ★ 关键：点侧边栏意味着「离开当前视图」——必须退出详情态，
  //   否则 view 仍是 'detail'，详情页 v-if 优先级最高会把新页面挡住，
  //   表现就是「点了侧边栏没反应」。
  if (view.value === 'detail') {
    view.value = 'board'
    selected.value = null
  }
  if (key === 'alarm') {
    store.fetchList()
    store.fetchStats()
  }
}

/** ★ 软件授权（有效期 1 年；到期全面停用） */
const license = useLicense()
/** 授权续期弹窗（提醒条上的按钮打开） */
const licenseDialog = ref(false)

/** 修改密码成功 → 交给 App.vue 回到登录页（本组件不再自管登录门禁） */
function onPasswordChanged() {
  tokenStore.clear()
  auth.reset()
  window.dispatchEvent(new Event('isup:unauthorized'))
}

onMounted(async () => {
  // ★ 授权到期事件（后端 403 license_expired 时广播）→ 立刻切拦截页
  window.addEventListener('isup:license-expired', onLicenseExpired)
  // ★ 剩余天数随时间变化，值守机长期不刷新页面，必须定时对表
  licenseTimer = window.setInterval(() => void license.fetch(), 10 * 60 * 1000)

  // ★ App.vue 已完成登录门禁（含 anonymous 无 token）。此处直接初始化业务。
  await license.fetch()
  // ★ 已到期：不连 WebSocket、不拉业务数据（后端也会 403），只留拦截页
  if (license.blocked) return
  await auth.fetchMe()
  connect()
  store.fetchList()
  store.fetchStats()

  // ★ 支持 #/alarm/<id> 直接进入详情（便于分享链接 / 深链）
  const m = /^#\/alarm\/(.+)$/.exec(location.hash)
  if (m) {
    const id = decodeURIComponent(m[1])
    const found = store.items.find((a) => a.id === id)
    selected.value =
      found ??
      ({
        id,
        device_id: '',
        channel: 1,
        alarm_type: 0,
        alarm_time: '',
        status: 'complete',
        image_count: 0,
        thumbnail_url: null,
        video: { status: 'not_requested', url: null, duration: null, provider: null },
        type_text: '',
        summary: '',
        extra: {},
        media_expired: false,
        media_expired_at: null,
        handled: false,
        handled_at: null,
      } as AlarmBrief)
    view.value = 'detail'
  }
})

/** 后端判定授权已到期（403 license_expired）→ 立即锁定界面 */
function onLicenseExpired() {
  license.forceExpired()
}

let licenseTimer: number | null = null

onUnmounted(() => {
  window.removeEventListener('isup:license-expired', onLicenseExpired)
  if (licenseTimer !== null) {
    window.clearInterval(licenseTimer)
    licenseTimer = null
  }
})
</script>

<template>
  <!-- ★ 授权到期：整个界面换成拦截页（业务接口后端也已 403） -->
  <LicenseGate v-if="license.blocked" />

  <div v-else class="app">
    <AppSidebar
      v-model="navKey"
      :pending="store.stats.pending"
      :superuser="auth.superuser"
      @nav="onNav"
    />

    <div class="main">
      <!-- 详情页有自己的返回栏，顶栏只在列表/其他页面显示 -->
      <AppTopbar
        v-if="showTopbar"
        :title="pageTitle"
        :pending="store.stats.pending"
        :user-name="auth.subject"
        @password-changed="onPasswordChanged"
      />

      <!-- ★ 授权即将到期提醒条（不足 3 个月才出现；不是错误，是提醒） -->
      <div v-if="license.shouldWarn" class="lic-warn" :class="license.daysLeft <= 30 ? 'critical' : 'warning'">
        <el-icon><Monitor /></el-icon>
        <span class="lw-text">
          软件授权将于 <b>{{ license.expireText }}</b> 到期，
          剩余 <b>{{ license.daysLeft <= 30 ? license.daysLeft + ' 天' : Math.floor(license.daysLeft / 30) + ' 个月' }}</b>。
          到期后系统将停用，请及时联系供应商续期。
        </span>
        <el-button size="small" type="primary" plain @click="licenseDialog = true">续期</el-button>
      </div>

      <!-- ★ 详情页：可能来自值守页或查询页，独立于 navKey 渲染，
           返回时回到来源页（backToBoard 里恢复） -->
      <AlarmDetailView
        v-if="view === 'detail' && selected"
        :alarm="selected"
        @back="backToBoard"
        @changed="store.fetchStats()"
      />

      <!-- ★ 实时监控（值守页：左流右图，来一条立刻显示） -->
      <LiveMonitorView
        v-else-if="navKey === 'live'"
        :connected="connected"
        @open-detail="openDetail"
      />

      <!-- ★ 报警看板（合并页）：态势带（看板）+ 实况画面 + 报警列表，一屏闭环 -->
      <div v-else-if="navKey === 'alarm'" class="content">
        <OverviewBand :connected="connected" @devices="onNav('device')" />

        <div class="workspace">
          <!-- 左：实况画面 —— 焦点那一条的图 + 处置（新报警自动换图并闪一下） -->
          <LiveFocusPanel
            :alarm="focus"
            :follow="follow"
            :index="focusIndex"
            :total="store.items.length"
            :flash="flash"
            @prev="() => moveFocus(-1)"
            @next="() => moveFocus(1)"
            @toggle-follow="toggleFollow"
            @open-detail="openDetail"
          />

          <!-- 右：报警列表（筛选/分页/批量处理/删除 全部保留） -->
          <div class="right">
            <AlarmTable
              :alarms="store.items"
              :loading="store.loading"
              :focus-id="focus?.id ?? null"
              @open="openDetail"
              @focus="focusOn"
              @delete="onDelete"
            />

            <div v-if="store.items.length" class="pager">
              <span class="pager-info">
                第 {{ store.page }} 页 · 每页 {{ store.size }} 条 · 共
                <b>{{ store.total }}</b> 条
              </span>
              <el-pagination
                layout="prev, pager, next"
                :current-page="store.page"
                :page-size="store.size"
                :total="store.total"
                :pager-count="7"
                @current-change="(p: number) => { store.page = p; store.fetchList() }"
              />
              <span class="pager-hint">
                点行看大图 · 双击进详情 · ↑↓ 换图
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 设备管理 -->
      <DeviceManageView v-else-if="navKey === 'device'" />

      <!-- 车间管理（admin） -->
      <WorkshopManageView v-else-if="navKey === 'workshop'" />

      <!-- 用户管理（admin） -->
      <UserManageView v-else-if="navKey === 'user'" />

      <!-- 连接状态（右下角小提示，不干扰主界面） -->
      <div v-if="!connected" class="offline-tip">
        <el-icon><Monitor /></el-icon> 实时推送已断开，正在重连…
      </div>
    </div>

    <!-- ★ 新报警弹窗（仅新报警到达时出现；检出违规的走下面的全屏，不弹这个） -->
    <NewAlarmToast
      :alarm="toastAlarm"
      @close="closeToast"
      @detail="() => openDetail(toastAlarm!)"
    />

    <!-- ★ 全屏报警浮层：检出违规才弹，到点自动收起（跟随闪烁时长）/ 随时可关 -->
    <AlarmFullscreen
      :alarm="fullscreenAlarm"
      @close="closeFullscreen"
      @detail="(a: AlarmBrief) => openDetail(a)"
    />

    <!-- ★ 授权续期弹窗（提醒条上的「续期」按钮打开；与顶栏角标同一个面板） -->
    <el-dialog v-model="licenseDialog" title="软件授权" width="520px" append-to-body>
      <LicensePanel />
    </el-dialog>
  </div>
</template>

<script lang="ts">
export default { name: 'AlarmBoard' }
</script>

<style scoped>
.app {
  display: flex;
  /* ★ 100% 而非 100vh：vh 只认视口原始尺寸，不随 #app 的
     transform:scale 缩放，用 100vh 会让界面只占屏幕上方 80%、底部空一条；
     百分比沿 html→body→#app 高度链解析，缩放后正好满屏。 */
  height: 100%;
  overflow: hidden;
  background: var(--bg);
  color: var(--text);
}
.main { flex: 1; display: flex; flex-direction: column; min-width: 0; }

/* ★ 授权即将到期提醒条：不足 3 个月才出现，压在顶栏下方（不遮挡内容） */
.lic-warn {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 18px;
  font-size: var(--fs-cap);
  color: var(--warn);
  background: rgba(var(--warn-rgb), 0.1);
  border-bottom: 1px solid rgba(var(--warn-rgb), 0.28);
}
.lic-warn.critical {
  color: var(--danger);
  background: var(--danger-soft);
  border-bottom-color: var(--danger-line);
}
.lic-warn .lw-text { flex: 1; min-width: 0; line-height: 1.6; }
.lic-warn b { font-variant-numeric: tabular-nums; }
/* 常规屏幕由表格内部滚动；矮屏或展开分析时允许页面滚动，保证工作区可用。 */
.content {
  padding: 16px 20px 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-y: auto;
}
/* 态势带（看板）保持自身高度，剩余全给工作区 */
.content > :deep(.board) { flex-shrink: 0; }

/* 工作区保留最小高度，避免展开分析后画面和分页被压缩到不可见。 */
.workspace {
  flex: 1;
  min-height: 360px;
  display: grid;
  grid-template-columns: minmax(320px, 34%) minmax(0, 1fr);
  gap: 14px;
}
/* 栅格子项默认 min-height:auto 会撑破容器，显式压回 0 让内部滚动生效 */
.workspace > :deep(.focus) { min-height: 0; }
.right {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
}
/* 报警面板撑满右列剩余高度，内部再分「工具条 / 表格 / 分页」 */
.right > :deep(.panel) { flex: 1; min-height: 0; }

/* 分页条：左右各一条信息，中间翻页 —— 钉在底部，不随表格滚动 */
.pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 11px 6px 13px;
  flex-wrap: wrap;
  flex-shrink: 0;
}
.pager-info {
  font-size: var(--fs-base);
  color: var(--text-2);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}
.pager-info b { color: var(--text); font-weight: 800; }
.pager-hint { font-size: var(--fs-cap); color: var(--text-3); }

.offline-tip {
  position: fixed;
  right: 18px;
  bottom: 16px;
  background: rgba(var(--danger-rgb), 0.14);
  color: var(--danger);
  border: 1px solid rgba(var(--danger-rgb), 0.35);
  border-radius: 6px;
  padding: 7px 12px;
  font-size: var(--fs-cap);
  display: flex;
  align-items: center;
  gap: 6px;
  z-index: 1500;
}

/* ★ 窄屏降级：实况画面转到上方（给固定高度，图不变形），列表占满剩余 */
@media (max-width: 1280px) {
  .workspace {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: minmax(230px, 40%) minmax(0, 1fr);
  }
}
</style>
