<script setup lang="ts">
/**
 * ★ 设备管理页。
 *
 * 两套视角（同一页面，按角色自动切换）：
 *   · admin   —— 看到全部通道，可修改「通道绑定车间」、改摄像头显示名；
 *                未指派的通道在这里分配（后端会回填历史告警归属）。
 *   · 子账号 —— 只能看到本车间的通道与在线状态（后端已隔离），只读。
 */
import { computed, onMounted, ref } from 'vue'
import { ArrowRight, Picture, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { adminApi, deviceApi, withToken } from '@/api'
import type { ChannelDevice, Workshop } from '@/types'
import { useAuth } from '@/stores/auth'

const auth = useAuth()
const rows = ref<ChannelDevice[]>([])
const workshops = ref<Workshop[]>([])
const loading = ref(false)

const isAdmin = computed(() => auth.superuser)

async function fetchAll() {
  loading.value = true
  try {
    if (isAdmin.value) {
      // ★ admin 走 admin 通道接口：带样本图（看画面认车间）+ 识别信息
      rows.value = await adminApi.channels()
      try {
        workshops.value = await adminApi.workshops()
      } catch {
        workshops.value = []
      }
    } else {
      rows.value = await deviceApi.channels()
    }
  } finally {
    loading.value = false
  }
}

/* ---------------- 修改绑定车间 ---------------- */
async function onChangeWorkshop(row: ChannelDevice, code: string | null) {
  try {
    await adminApi.assignChannel(row.id, code, row.display_name || '')
    ElMessage.success(code ? `已绑定到 ${wsName(code)}` : '已取消绑定')
    await fetchAll()
  } catch {
    /* 拦截器已提示 */
  }
}

function wsName(code: string | null): string {
  if (!code) return '未绑定'
  return workshops.value.find((w) => w.code === code)?.name || code
}

/* ---------------- 改名 ---------------- */
const renameVisible = ref(false)
const renameRow = ref<ChannelDevice | null>(null)
const renameText = ref('')

function openRename(row: ChannelDevice) {
  renameRow.value = row
  renameText.value = row.display_name || row.channel_name || ''
  renameVisible.value = true
}

async function doRename() {
  if (!renameRow.value) return
  const name = renameText.value.trim()
  if (!name) {
    ElMessage.warning('请输入名称')
    return
  }
  await adminApi.renameChannel(renameRow.value.id, name)
  renameVisible.value = false
  ElMessage.success('已改名')
  await fetchAll()
}

function timeText(t: string | null): string {
  if (!t) return '—'
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return t
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// ---------- ★ 2026-10-26 改成「按设备分组」展示 ----------
//
// 现场问题：一台 NVR（box001）有 5 个通道，原来一个通道一行，
// 页面上看起来像 5~6 台设备，运维以为"设备重复了"。
//
// 现在：一台设备一行，展开后看它的通道。
//   · 设备行：设备ID / 在线状态 / 通道数 / 在线通道数 / 该设备最近告警
//   · 展开行：该设备下每个通道（可绑车间、改名）
export interface DeviceGroup {
  deviceId: string
  online: boolean | null
  channels: ChannelDevice[]
  onlineChannels: number
  /** ★ 真正接了摄像头的通道数（camera_online_known 且有型号/IP） */
  cameraChannels: number
  lastAlarm: string | null
  hasMissingParent: boolean
}

const groups = computed<DeviceGroup[]>(() => {
  const map = new Map<string, ChannelDevice[]>()
  for (const r of rows.value) {
    // ★ 只显示有摄像头型号的通道（除非用户勾选"显示全部"）
    if (!showEmpty.value && !hasCamera(r)) continue
    const key = r.parent_device || '（未知设备）'
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(r)
  }

  const out: DeviceGroup[] = []
  for (const [deviceId, chs] of map) {
    // ★ 设备（NVR）在线：看它的通道里有没有在线的
    const onCount = chs.filter((c) => c.online === true).length
    const online = onCount > 0 ? true : chs.every((c) => c.online === false) ? false : null
    // ★ 真正接了摄像头的通道（有型号说明识别到了设备）
    const camCount = chs.filter((c) => !!c.camera_model).length
    let last: string | null = null
    for (const c of chs) {
      if (c.last_alarm_at && (!last || c.last_alarm_at > last)) last = c.last_alarm_at
    }
    out.push({
      deviceId,
      online,
      channels: chs,
      onlineChannels: onCount,
      cameraChannels: camCount,
      lastAlarm: last,
      hasMissingParent: chs.some((c) => c.parent_missing),
    })
  }
  // 在线优先，然后按设备名
  out.sort((a, b) => {
    if (a.online !== b.online) return a.online ? -1 : 1
    return a.deviceId.localeCompare(b.deviceId)
  })
  return out
})

const expanded = ref<string[]>([])

/**
 * ★★ 2026-10-26：是否显示「未接摄像头」的空通道。
 *
 * 现场情况：NVR 有 5 个通道，只有 ch1 真接了摄像头（有型号），
 * ch2~ch5 型号为空（NVR 没识别到设备）。这些空通道留在页面上：
 *   · 运维会以为"有 5 个摄像头"
 *   · 还占着车间绑定位置
 *
 * 默认关闭 → 只看真设备。接上摄像头（型号出现）后会自动显示。
 * 排查问题时可打开开关看全部通道。
 *
 * ★★ 2026-10-29：默认改为**打开**（true）。
 *
 *   原因：默认隐藏的前提是「型号能查到」，而那要求 ISAPI 已配置。
 *   现场首次部署/未配 ISAPI 时，型号全空 → 页面一片空白，
 *   运维第一反应是"设备没接上"，其实设备好好的。
 *
 *   空通道的代价只是"多看一眼"，而误判"没有设备"会让人去查错方向。
 *   需要清爽视图时，手动取消勾选即可。
 */
const showEmpty = ref(true)

/**
 * 该通道是否算「有摄像头」。
 *
 * ★★ 2026-10-29 修复「设备管理页全部空白」：
 *
 *   原实现只看 `camera_model`：
 *       return !!c.camera_model
 *
 *   而 camera_model 来自 ISAPI 查询（server/crud/device.py 的 real_states），
 *   **必须配了 ISUP_ISAPI_HOST 且查询成功**才有值。若现场没配 ISAPI 地址
 *   （离线部署/首次调试的常见状态），所有通道型号都是空 →
 *   全部被这个过滤条件隐藏 → 页面显示"暂无设备"，
 *   但首页看板却显示"2/2 台在线"（那是按 Device 表统计的），
 *   两个页面口径打架，运维完全无法理解。
 *
 *   修法：**只在能确知「没有摄像头」时才隐藏**。
 *   判据改为「型号为空 **且** 该通道从未产生过告警」——
 *   真正接了摄像头的通道迟早会报一次警（alarm_count > 0），
 *   这样既不会误隐藏真实设备，也仍能过滤 NVR 上的空通道。
 */
function hasCamera(c: ChannelDevice): boolean {
  if (c.camera_model) return true          // 有型号：确定是真摄像头
  // 没有型号时，有告警记录 = 确实在用（只是 ISAPI 没查到型号）
  if ((c.alarm_count ?? 0) > 0) return true
  // 其余（型号空 + 零告警）才是真正的空通道，可隐藏
  return false
}

function toggleExpand(deviceId: string) {
  const i = expanded.value.indexOf(deviceId)
  if (i >= 0) expanded.value.splice(i, 1)
  else expanded.value.push(deviceId)
}

onMounted(fetchAll)
</script>

<template>
  <div class="page">
    <div class="head">
      <div>
        <div class="title">设备管理</div>
        <div class="sub">
          {{
            isAdmin
              ? '为每路摄像头通道绑定所属车间；子账号只能看到本车间的设备'
              : '本车间绑定的摄像头通道与在线状态'
          }}
        </div>
      </div>
      <div class="head-actions">
        <el-checkbox v-model="showEmpty" size="small">
          显示未接摄像头的通道
        </el-checkbox>
        <el-button :icon="Refresh" @click="fetchAll">刷新</el-button>
      </div>
    </div>

    <div class="panel">
      <!-- ★ 2026-10-26 按设备分组：一台设备一行，点开看它的通道 -->
      <div v-loading="loading" class="dev-list">
        <div v-for="g in groups" :key="g.deviceId" class="dev-row">
          <div class="dev-head" @click="toggleExpand(g.deviceId)">
            <el-icon class="chev" :class="{ open: expanded.includes(g.deviceId) }">
              <ArrowRight />
            </el-icon>

            <span class="dev-name">{{ g.deviceId }}</span>

            <span
              v-if="g.online === null"
              class="online unknown"
              title="该设备不在设备表中，无法判定在线状态"
            >
              <span class="d" />未知
            </span>
            <span v-else class="online" :class="g.online ? 'on' : 'off'">
              <span class="d" />{{ g.online ? '在线' : '离线' }}
            </span>

            <span class="dev-meta">
              {{ g.channels.length }} 通道<template v-if="g.cameraChannels > 0"> · {{ g.cameraChannels }} 摄像头</template>
            </span>
            <span class="dev-cams" :class="g.onlineChannels > 0 ? 'ok' : 'none'">
              <span class="d" />{{ g.onlineChannels }} 个摄像头在线
            </span>

            <span v-if="g.hasMissingParent" class="dev-warn">父设备缺失</span>

            <span class="dev-last mono">{{ timeText(g.lastAlarm) }}</span>
          </div>

          <div v-if="expanded.includes(g.deviceId)" class="ch-wrap">
            <el-table :data="g.channels" size="small" style="width: 100%">
              <el-table-column v-if="isAdmin" label="画面预览" width="110">
                <template #default="{ row }">
                  <el-image
                    v-if="row.sample_image_url"
                    :src="withToken(row.sample_image_url)"
                    :preview-src-list="[withToken(row.sample_image_url)]"
                    fit="cover"
                    class="thumb"
                    preview-teleported
                    @click.stop
                  >
                    <template #error>
                      <div class="thumb-empty"><el-icon><Picture /></el-icon></div>
                    </template>
                  </el-image>
                  <div v-else class="thumb-empty" title="该通道还没有告警图片">
                    <el-icon><Picture /></el-icon>
                  </div>
                </template>
              </el-table-column>

              <el-table-column label="通道" width="100">
                <template #default="{ row }">
                  <span class="ch-no">CH{{ row.channel_no ?? row.id }}</span>
                </template>
              </el-table-column>

              <!-- ★ 摄像头本身的信息（来自 NVR 的 ISAPI） -->
              <el-table-column label="摄像头" min-width="210">
                <template #default="{ row }">
                  <div v-if="row.camera_model" class="cam">
                    <div class="cam-model">{{ row.camera_model }}</div>
                    <div class="cam-ip mono">{{ row.camera_ip || '—' }}</div>
                  </div>
                  <div v-else-if="row.camera_ip" class="cam">
                    <div class="cam-model dim">未识别型号</div>
                    <div class="cam-ip mono">{{ row.camera_ip }}</div>
                  </div>
                  <span v-else class="cam-none" :title="row.camera_online_known ? 'NVR 上该通道没有接摄像头' : '未能从 NVR 获取该通道状态'">
                    {{ row.camera_online_known ? '未接摄像头' : '状态未知' }}
                  </span>
                </template>
              </el-table-column>

              <el-table-column label="在线" width="90">
                <template #default="{ row }">
                  <span v-if="row.online === null" class="online unknown">
                    <span class="d" />未知
                  </span>
                  <span v-else class="online" :class="row.online ? 'on' : 'off'">
                    <span class="d" />{{ row.online ? '在线' : '离线' }}
                  </span>
                </template>
              </el-table-column>

              <el-table-column label="名称" min-width="160">
                <template #default="{ row }">
                  <span class="name">
                    {{ row.display_name || (row.channel_name ? row.channel_name + ' / CH' + (row.channel_no ?? row.id) : '通道 ' + row.id) }}
                  </span>
                </template>
              </el-table-column>

              <el-table-column v-if="isAdmin" label="所属车间" width="170">
                <template #default="{ row }">
                  <el-select
                    :model-value="row.workshop_code"
                    placeholder="未绑定"
                    size="small"
                    style="width: 140px"
                    @change="(v: string | null) => onChangeWorkshop(row, v || null)"
                  >
                    <el-option
                      v-for="w in workshops"
                      :key="w.code"
                      :label="w.name"
                      :value="w.code"
                    />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column v-else label="所属车间" width="130">
                <template #default="{ row }">{{ wsName(row.workshop_code) }}</template>
              </el-table-column>

              <el-table-column label="告警" width="80">
                <template #default="{ row }">{{ row.alarm_count }}</template>
              </el-table-column>

              <el-table-column label="最近告警" width="160">
                <template #default="{ row }">
                  <span class="mono">{{ timeText(row.last_alarm_at) }}</span>
                </template>
              </el-table-column>

              <el-table-column v-if="isAdmin" label="操作" width="80">
                <template #default="{ row }">
                  <el-button size="small" text type="primary" @click="openRename(row)">
                    改名
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <el-empty
          v-if="groups.length === 0 && !loading"
          :description="
            isAdmin
              ? '暂无设备 —— 设备注册并上报告警后会自动出现在这里'
              : '本车间暂无绑定的设备，请联系管理员分配'
          "
          :image-size="80"
        />
      </div>
    </div>

    <!-- 改名弹窗 -->
    <el-dialog v-model="renameVisible" title="通道改名" width="420px">
      <el-input v-model="renameText" placeholder="如：1号车间东侧" maxlength="128" @keyup.enter="doRename" />
      <template #footer>
        <el-button @click="renameVisible = false">取消</el-button>
        <el-button type="primary" @click="doRename">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page { padding: 16px 20px; overflow-y: auto; height: 100%; }
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}
.title { font-size: var(--fs-xl); font-weight: 700; color: var(--text); }
.sub { font-size: var(--fs-cap); color: var(--text-2); margin-top: 4px; }

.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}

.online { display: inline-flex; align-items: center; gap: 5px; font-size: var(--fs-micro); }
.online .d { width: 6px; height: 6px; border-radius: 50%; }
.online.on { color: var(--ok); }
.online.on .d { background: var(--ok); }
.online.off { color: var(--danger); }
.online.off .d { background: var(--danger); }
/* 未知：灰色，区别于"确定的离线" */
.online.unknown { color: var(--text-2); }
.online.unknown .d { background: var(--text-2); }

/* 父设备：查无此设备时标黄，提示这是历史残留数据 */
.parent { font-size: var(--fs-cap); color: var(--text-2); font-variant-numeric: tabular-nums; }
.parent.missing { color: var(--warn); }
.parent.none { color: var(--text-3); }

.name { color: var(--text); }
.raw-name { font-size: var(--fs-micro); color: var(--text-3); margin-left: 4px; }
.mono { color: var(--text); font-variant-numeric: tabular-nums; font-size: var(--fs-micro); }

.thumb {
  width: 78px;
  height: 46px;
  border-radius: 4px;
  border: 1px solid var(--border-strong);
  display: block;
  background: var(--border);
}
.thumb-empty {
  width: 78px;
  height: 46px;
  border-radius: 4px;
  border: 1px solid var(--border-strong);
  background: var(--surface-2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-3);
}

/* ---- 按设备分组的新样式（2026-10-26）---- */
.dev-list { padding: 4px 0; }
.dev-row { border-bottom: 1px solid var(--border); }
.dev-row:last-child { border-bottom: none; }

.dev-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.15s;
}
.dev-head:hover { background: var(--surface-2); }

.chev { font-size: var(--fs-base); color: var(--text-3); transition: transform 0.2s; }
.chev.open { transform: rotate(90deg); }

.dev-name {
  font-weight: 600;
  font-size: var(--fs-base);
  color: var(--text);
  min-width: 120px;
  font-variant-numeric: tabular-nums;
}
.dev-meta { font-size: var(--fs-cap); color: var(--text-2); }
.dev-warn {
  font-size: var(--fs-micro);
  color: var(--warn);
  background: color-mix(in srgb, var(--warn) 12%, transparent);
  padding: 1px 6px;
  border-radius: 3px;
}
.dev-last { margin-left: auto; font-size: var(--fs-cap); color: var(--text-3); min-width: 130px; text-align: right; }

.ch-wrap { padding: 0 16px 12px 40px; background: var(--surface-2); }

/* ---- 摄像头在线数（设备行右侧）---- */
.dev-cams {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: var(--fs-cap);
  padding: 2px 8px;
  border-radius: 10px;
}
.dev-cams .d { width: 6px; height: 6px; border-radius: 50%; }
.dev-cams.ok {
  color: var(--ok);
  background: color-mix(in srgb, var(--ok) 12%, transparent);
}
.dev-cams.ok .d { background: var(--ok); }
.dev-cams.none {
  color: var(--text-3);
  background: var(--surface-2);
}
.dev-cams.none .d { background: var(--text-3); }

/* ---- 摄像头信息（展开行内）---- */
.cam { line-height: 1.35; }
.cam-model { font-size: var(--fs-micro); color: var(--text); }
.cam-model.dim { color: var(--text-3); }
.cam-ip { font-size: var(--fs-micro); color: var(--text-3); }
.cam-none { font-size: var(--fs-cap); color: var(--text-3); font-style: italic; }

/* 通道号：CH1/CH2… 唯一，避免 NVR 上同名通道（都叫 Camera 01）看起来重复 */
.ch-no {
  display: inline-block;
  min-width: 42px;
  padding: 1px 7px;
  border-radius: 4px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  font-size: var(--fs-cap);
  font-weight: 600;
  color: var(--text);
  font-variant-numeric: tabular-nums;
}

.head-actions { display: flex; align-items: center; gap: 12px; }
</style>
