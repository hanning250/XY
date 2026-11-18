<script setup lang="ts">
/**
 * 告警详情页。
 *
 * 布局：
 *   左栏 —— 报警信息 + 报警图片 + 「获取视频」「标记为已处理」
 *   右栏 —— 视频回放（★ 只保留播放器，已按需求砍掉「回放时间段」「视频片段」）
 *
 * ★ 不点「获取视频」，右栏不会去设备抓流（不占设备连接）。
 */
import { computed, onUnmounted, ref, watch } from 'vue'
import { ArrowLeft, Picture, VideoPlay, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { withToken } from '@/api'
import { alarmTypeText, useAlarmStore } from '@/stores/alarm'
import type { AlarmBrief, AlarmDetail } from '@/types'

const props = defineProps<{ alarm: AlarmBrief | null }>()
const emit = defineEmits<{
  (e: 'back'): void
  (e: 'changed'): void
}>()

const store = useAlarmStore()

const detail = computed<AlarmDetail | null>(() =>
  store.detail?.id === props.alarm?.id ? store.detail : null,
)

const deviceId = computed(() => detail.value?.device_id ?? props.alarm?.device_id ?? '')
const typeLabel = computed(() => {
  const t = detail.value?.type_text ?? props.alarm?.type_text
  if (t) return t
  const at = detail.value?.alarm_type ?? props.alarm?.alarm_type
  return at !== undefined ? alarmTypeText(at) : '未知报警'
})

const alarmTime = computed(() => {
  const t = detail.value?.alarm_time ?? props.alarm?.alarm_time
  if (!t) return ''
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return t
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
})

/** 报警描述：后端解析出的 summary 优先 */
const description = computed(() => {
  const s = detail.value?.summary ?? props.alarm?.summary
  if (s) return s
  const c = detail.value?.content as Record<string, unknown> | null | undefined
  const rs = c?.ruleName ?? c?.eventType
  return typeof rs === 'string' && rs ? rs : '—'
})

/** 图片列表（★ 全部来自后端图片接口） */
const images = computed(() => {
  const list = detail.value?.images ?? []
  return list.filter((i) => !detail.value?.media_expired)
})
const mainImage = computed(() => images.value[0] ?? null)
const mediaExpired = computed(
  () => !!(detail.value?.media_expired ?? props.alarm?.media_expired),
)

/** ★ 违规人数（替代原来的"已处理"标签——纯展示看板不做处置流转） */
const alarmedCount = computed(() => {
  const n = detail.value?.extra?.alarmed_count ?? props.alarm?.extra?.alarmed_count
  return typeof n === 'number' ? n : 0
})

/** 视频状态 */
const videoStatus = computed(
  () => detail.value?.video?.status ?? props.alarm?.video?.status ?? 'not_requested',
)
const videoUrl = computed(() => detail.value?.video?.url ?? props.alarm?.video?.url ?? null)
const videoReady = computed(() => videoStatus.value === 'ready' && !!videoUrl.value)
const videoStarting = computed(() => videoStatus.value === 'starting')
const videoFailed = computed(() => videoStatus.value === 'failed')

/** 失败原因原文（后端落库的 video_error） */
const rawVideoError = computed(
  () => detail.value?.video?.error ?? props.alarm?.video?.error ?? '',
)

/** ★ 把后端的原因翻译成「人话 + 下一步怎么做」 */
const videoErrorText = computed(() => {
  const e = rawVideoError.value
  if (!e) return '未知原因'
  if (/设备未在线|设备不在线|未在线/.test(e)) return '设备当前离线'
  if (/无录像|空流|没有录像|返回空/.test(e)) return '该时段设备里没有录像'
  if (/超时/.test(e)) return '抓取超时（设备忙或网络慢）'
  if (/转码/.test(e)) return '录像转码失败（文件格式异常）'
  if (/时间.*解析/.test(e)) return '报警时间无法解析'
  return e
})

const videoErrorHint = computed(() => {
  const e = rawVideoError.value
  if (/未在线|不在线/.test(e)) {
    return '设备重新上线后点「重新获取」即可（刚重连时需要等几秒）'
  }
  if (/无录像|空流|没有录像|返回空/.test(e)) {
    return '设备本地可能没有该时间段的录像（未开启录像 / 已被覆盖）'
  }
  if (/超时/.test(e)) return '稍后重试；若持续超时，检查设备回放是否被占用'
  if (/转码/.test(e)) return '可重新抓取一次；若持续失败请把该报警上报给我方排查'
  return '可点「重新获取」再试一次'
})

/** ★ 视频懒加载：用户点「播放视频」才真正拉流（切换告警/返回时重置） */
const videoActive = ref(false)
watch(
  () => props.alarm?.id,
  () => {
    videoActive.value = false
  },
)

const fetching = ref(false)
const deleting = ref(false)

/** ★ 删除该条报警（连图片/视频文件一起删）—— 替代原来的「标记为已处理」 */
async function onDelete() {
  if (!props.alarm) return
  try {
    await ElMessageBox.confirm(
      '确定删除该报警吗？关联的图片与视频文件也会一并删除，且不可恢复。',
      '删除报警',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  deleting.value = true
  try {
    await store.removeOne(props.alarm.id)
    ElMessage.success('已删除')
    emit('back')
  } finally {
    deleting.value = false
  }
}

/** ★ 获取视频：调用后端抓取（SMS 回放），右栏进入「抓取中」 */
async function onFetchVideo() {
  if (!props.alarm || mediaExpired.value) return
  fetching.value = true
  try {
    await store.requestPlayback(props.alarm.id)
    ElMessage.success('已开始从设备抓取录像，请稍候…')
    // 先立即补拉一次（后端已把状态置 starting，界面马上有反馈）
    await store.fetchDetail(props.alarm.id)
    startPolling()
  } catch {
    /* 拦截器已提示（队列满/设备未启动等） */
  } finally {
    fetching.value = false
  }
}

/**
 * ★ 抓取期间轮询（2026-XX）：原来只在 3 秒后补拉一次，
 * 抓取要 10~60 秒，失败状态又只在 WS 断线时收不到 —— 用户会以为卡住。
 * 这里每 2 秒查一次，拿到 ready/failed 就停；最多轮询 90 秒。
 */
let pollTimer: number | null = null
let pollCount = 0

function stopPolling() {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
  pollCount = 0
}

function startPolling() {
  stopPolling()
  pollCount = 0
  pollTimer = window.setInterval(async () => {
    pollCount += 1
    const id = props.alarm?.id
    if (!id) return stopPolling()
    try {
      const fresh = await store.fetchDetail(id)
      const st = fresh?.video?.status
      if (st === 'ready' || st === 'failed' || st === 'unavailable') {
        stopPolling()
        if (st === 'ready') ElMessage.success('视频已就绪')
        if (st === 'failed') ElMessage.warning('未能获取视频，请看右侧原因')
      }
    } catch {
      /* 查询失败继续轮询 */
    }
    if (pollCount >= 45) stopPolling() // 90 秒上限
  }, 2000)
}

onUnmounted(stopPolling)

/** 打开详情时拉一次完整信息 */
watch(
  () => props.alarm?.id,
  (id) => {
    if (id) store.fetchDetail(id)
  },
  { immediate: true },
)
</script>

<template>
  <div v-if="alarm" class="detail">
    <!-- 返回 -->
    <div class="backbar">
      <div class="back" @click="emit('back')">
        <el-icon><ArrowLeft /></el-icon>
        <span>返回</span>
      </div>
    </div>

    <div class="layout">
      <!-- ============ 左栏 ============ -->
      <div class="left">
        <div class="title-row">
          <div class="title-ico">
            <el-icon><WarningFilled /></el-icon>
          </div>
          <span class="title-text">{{ typeLabel }}</span>
          <!-- ★ 2026-10-26：原「已处理」胶囊移除，改为违规人数（客观事实，不需要人点） -->
          <span class="pill alarmed" :class="{ zero: alarmedCount === 0 }">
            违规 {{ alarmedCount }} 人
          </span>
        </div>

        <div class="info-row">
          <div class="info-k">报警时间</div>
          <div class="info-v mono">{{ alarmTime }}</div>
        </div>
        <div class="info-row">
          <div class="info-k">设备名称</div>
          <div class="info-v">{{ deviceId || '未知设备' }}</div>
        </div>
        <div class="info-row">
          <div class="info-k">设备编号</div>
          <div class="info-v">{{ deviceId || '—' }}</div>
        </div>
        <div class="info-row">
          <div class="info-k">报警描述</div>
          <div class="info-v">{{ description }}</div>
        </div>

        <div class="sec-title">报警图片</div>

        <!-- ★ 真实报警图片（对接后端图片接口），无任何装饰框 -->
        <el-image
          v-if="mainImage"
          :src="withToken(mainImage.url)"
          :preview-src-list="images.map((i) => withToken(i.url))"
          fit="cover"
          class="pic"
          preview-teleported
        >
          <template #error>
            <div class="pic-empty"><el-icon><Picture /></el-icon></div>
          </template>
        </el-image>
        <div v-else class="pic-empty big">
          <el-icon><Picture /></el-icon>
          <span>{{ mediaExpired ? '媒体已过期' : '暂无报警图片' }}</span>
        </div>

        <!-- 多图时的小图条 -->
        <div v-if="images.length > 1" class="thumbs">
          <el-image
            v-for="(img, i) in images"
            :key="img.id"
            :src="withToken(img.url)"
            :preview-src-list="images.map((x) => withToken(x.url))"
            :initial-index="i"
            fit="cover"
            class="mini"
            preview-teleported
          />
        </div>

        <!-- ★ 操作按钮 -->
        <div class="actions">
          <el-button
            type="primary"
            :loading="fetching"
            :disabled="videoReady || videoStarting || mediaExpired"
            @click="onFetchVideo"
          >
            {{
              videoReady
                ? '已获取视频'
                : videoStarting
                  ? '抓取中…'
                  : videoFailed
                    ? '重新获取'
                    : '获取视频'
            }}
          </el-button>
          <!-- ★ 2026-10-26：「标记为已处理」按钮已移除（纯展示看板不做处置流转）。
               这里换成"删除"，是甲方实际需要的动作（清掉无关/误报的记录）。 -->
          <el-button type="danger" plain :loading="deleting" @click="onDelete">
            删除记录
          </el-button>
        </div>
      </div>

      <!-- ============ 右栏：视频回放 ============ -->
      <div class="right">
        <div class="right-head">
          <span>视频回放</span>
          <span v-if="videoReady" class="pill ok">已就绪</span>
          <span v-else-if="videoStarting" class="pill warn">抓取中…</span>
          <span v-else-if="videoFailed" class="pill err">获取失败</span>
        </div>

        <div class="player">
          <!-- 已就绪：播放器（默认不预载，用户点播放才拉流，返回列表不被大文件下载拖累） -->
          <video
            v-if="videoReady && videoActive"
            ref="videoEl"
            :src="withToken(videoUrl)"
            preload="none"
            controls
            class="video"
          />

          <!-- ★ 待激活遮罩：状态就绪但用户还没点「播放视频」 -->
          <div v-else-if="videoReady" class="empty">
            <el-icon class="ico"><VideoPlay /></el-icon>
            <div class="t1">视频已就绪</div>
            <div class="t2">点击下方按钮开始加载播放（约 10~20 MB）</div>
            <el-button type="primary" :icon="VideoPlay" @click="videoActive = true">
              播放视频
            </el-button>
          </div>

          <!-- 抓取中 -->
          <div v-else-if="videoStarting" class="empty">
            <div class="spinner" />
            <div class="t1">正在从设备抓取录像…</div>
            <div class="t2">抓取报警时刻前 1 分钟的录像，约需 10~60 秒</div>
          </div>

          <!-- ★ 失败：把原因说清楚 + 允许重试（2026-XX）
               原来只有 ready/starting 两态，failed 时界面默默变回"获取视频"，
               用户以为点了没反应。 -->
          <div v-else-if="videoFailed" class="empty">
            <el-icon class="ico warn"><WarningFilled /></el-icon>
            <div class="t1">未能获取视频</div>
            <div class="t2 err-reason">{{ videoErrorText }}</div>
            <div class="t2">{{ videoErrorHint }}</div>
            <el-button type="primary" :loading="fetching" @click="onFetchVideo">
              重新获取
            </el-button>
          </div>

          <!-- ★ 未获取：不加载（不占设备连接） -->
          <div v-else class="empty">
            <el-icon class="ico"><Picture /></el-icon>
            <div class="t1">尚未获取视频</div>
            <div class="t2">
              点击左侧「获取视频」，将从设备拉取该报警时刻前 1 分钟的录像
            </div>
            <el-button
              type="primary"
              :loading="fetching"
              :disabled="mediaExpired"
              @click="onFetchVideo"
            >
              获取视频
            </el-button>
          </div>
        </div>

        <div class="note">
          <template v-if="mediaExpired">
            ★ 该报警的媒体文件已按保留策略清理，无法再获取录像
          </template>
          <template v-else-if="videoFailed">
            ★ 失败原因：{{ videoErrorText }} —— 可按上面提示处理后再点「重新获取」
          </template>
          <template v-else-if="videoReady">
            ★ 录像为报警时刻前 1 分钟，已从设备抓取并转码为 MP4
          </template>
          <template v-else>
            ★ 不点击「获取视频」不会向设备发起任何取流请求，不占用设备连接
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.detail { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.backbar {
  height: 50px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding: 0 20px;
  border-bottom: 1px solid var(--border);
}
.back {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--text-2);
  cursor: pointer;
  font-size: var(--fs-micro);
}
.back:hover { color: var(--text); }

.layout { flex: 1; display: flex; gap: 16px; padding: 16px 20px; overflow: hidden; }

/* ---------- 左栏 ---------- */
.left {
  width: 340px;
  flex-shrink: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
.title-row { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
.title-ico {
  width: 30px;
  height: 30px;
  border-radius: 7px;
  flex-shrink: 0;
  background: rgba(var(--warn-rgb), 0.14);
  color: var(--warn);
  display: flex;
  align-items: center;
  justify-content: center;
  /* ★ 不写死 size 时 el-icon 会按字号渲染，导致图标显示成小方块/数字 */
  font-size: var(--fs-md);
}
.title-text { font-size: var(--fs-base); font-weight: 700; color: var(--text); }
.pill {
  font-size: var(--fs-micro);
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
}
/* ★ 违规人数胶囊（替代原「已处理」标签）：红底白字，一眼看清卷进几个人 */
.pill.alarmed {
  background: var(--danger);
  color: #fff;
  border: 1px solid #a81f14;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.pill.alarmed.zero {
  background: var(--surface-3);
  color: var(--text-3);
  border-color: var(--border);
  font-weight: 600;
}
.pill.ok { background: rgba(var(--ok-rgb), 0.14); color: var(--ok); }
.pill.warn { background: rgba(var(--warn-rgb), 0.16); color: var(--warn); }
.pill.err { background: rgba(var(--danger-rgb), 0.16); color: var(--danger); }

/* 失败原因高亮显示（用户第一眼要看的就是为什么没拿到） */
.empty .ico.warn { color: var(--danger); }
.err-reason {
  color: var(--danger) !important;
  font-weight: 600;
  font-size: var(--fs-micro) !important;
}

.info-row {
  display: flex;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
  font-size: var(--fs-micro);
}
.info-row:last-of-type { border-bottom: none; }
.info-k { width: 74px; flex-shrink: 0; color: var(--text-2); }
.info-v { color: var(--text); flex: 1; word-break: break-all; }
.mono { font-variant-numeric: tabular-nums; }

.sec-title { font-size: var(--fs-micro); font-weight: 600; color: var(--text); margin: 18px 0 10px; }

.pic {
  width: 100%;
  height: 190px;
  border-radius: 6px;
  display: block;
  background: var(--surface-2);
  border: 1px solid var(--border-strong);
}
.pic-empty {
  width: 100%;
  height: 190px;
  border-radius: 6px;
  background: var(--surface-2);
  border: 1px solid var(--border-strong);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--text-3);
  font-size: 20px;
}
.pic-empty.big span { font-size: var(--fs-cap); }

.thumbs { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
.mini {
  width: 56px;
  height: 38px;
  border-radius: 4px;
  border: 1px solid var(--border-strong);
  cursor: zoom-in;
}

.actions { margin-top: auto; padding-top: 16px; display: flex; gap: 9px; }
.actions :deep(.el-button) { flex: 1; margin-left: 0; }

/* ---------- 右栏 ---------- */
.right {
  flex: 1;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.right-head {
  font-size: var(--fs-base);
  font-weight: 600;
  color: var(--text);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 9px;
}
.player {
  width: 100%;
  aspect-ratio: 16 / 9;
  /* 视频衬底用近黑的深灰（不用纯黑）：画面需要暗底才准，
     按钮/外框仍是浅色主题 */
  background: var(--text);
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--border);
  position: relative;
}
.video { width: 100%; height: 100%; display: block; background: var(--text); }

.empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 11px;
  background: var(--surface-2);
}
.empty .ico { font-size: 38px; color: var(--border-strong); }
.empty .t1 { font-size: var(--fs-base); color: var(--text-2); }
.empty .t2 {
  font-size: var(--fs-cap);
  color: var(--text-3);
  max-width: 320px;
  text-align: center;
  line-height: 1.7;
}
.spinner {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 2px solid rgba(var(--brand-rgb), 0.25);
  border-top-color: var(--brand);
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.note {
  margin-top: 12px;
  font-size: var(--fs-cap);
  color: var(--text-3);
  line-height: 1.7;
  padding: 9px 11px;
  background: var(--surface-2);
  border-radius: 6px;
  border-left: 2px solid var(--brand);
}
</style>
