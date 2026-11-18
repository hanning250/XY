<script setup lang="ts">
/**
 * ★ 车间管理（仅 admin 可见）。
 *
 * 功能：
 *   · 车间列表（含通道数 / 账号数 / 告警数概览）
 *   · 修改车间名字（只动 name 不动 code —— 历史数据归属自动跟随）
 *   · 新建车间 / 删除车间（有告警时后端会拒绝）
 */
import { onMounted, ref } from 'vue'
import { Delete, Edit, Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '@/api'
import type { Workshop } from '@/types'

const rows = ref<Workshop[]>([])
const loading = ref(false)

async function fetchList() {
  loading.value = true
  try {
    rows.value = await adminApi.workshops()
  } finally {
    loading.value = false
  }
}

/* ---------------- 新建 ---------------- */
const createVisible = ref(false)
const newCode = ref('')
const newName = ref('')
const createLoading = ref(false)

function openCreate() {
  newCode.value = ''
  newName.value = ''
  createVisible.value = true
}

async function doCreate() {
  const code = newCode.value.trim()
  const name = newName.value.trim()
  if (!code || !name) {
    ElMessage.warning('请填写车间编码和名称')
    return
  }
  if (!/^[A-Za-z0-9_-]{1,32}$/.test(code)) {
    ElMessage.warning('编码只能用字母/数字/_/-，最长 32 位（创建后不可改）')
    return
  }
  createLoading.value = true
  try {
    await adminApi.upsertWorkshop({ code, name })
    createVisible.value = false
    ElMessage.success('车间已创建')
    await fetchList()
  } finally {
    createLoading.value = false
  }
}

/* ---------------- 改名 ---------------- */
const renameVisible = ref(false)
const renameCode = ref('')
const renameText = ref('')

function openRename(w: Workshop) {
  renameCode.value = w.code
  renameText.value = w.name
  renameVisible.value = true
}

async function doRename() {
  const name = renameText.value.trim()
  if (!name) {
    ElMessage.warning('名称不能为空')
    return
  }
  await adminApi.renameWorkshop(renameCode.value, name)
  renameVisible.value = false
  ElMessage.success('已改名')
  await fetchList()
}

/* ---------------- 删除 ---------------- */
async function onDelete(w: Workshop) {
  try {
    await ElMessageBox.confirm(
      `确定删除车间「${w.name}」吗？\n有告警记录或仍绑定通道的车间无法删除。`,
      '删除车间',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  await adminApi.deleteWorkshop(w.code)
  ElMessage.success('已删除')
  await fetchList()
}

onMounted(fetchList)
</script>

<template>
  <div class="page">
    <div class="head">
      <div>
        <div class="title">车间管理</div>
        <div class="sub">通道绑定到车间、子账号授权到车间，都在这里维护</div>
      </div>
      <div class="btns">
        <el-button :icon="Refresh" @click="fetchList">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新建车间</el-button>
      </div>
    </div>

    <div class="panel">
      <!-- ★ 2026-10-26：与用户管理同口径 —— 表格撑满剩余高度，
           弹性列吃掉右侧空白，不再"表格只占左半边"。 -->
      <el-table
        v-loading="loading"
        :data="rows"
        style="width: 100%"
        height="100%"
        row-key="code"
      >
        <el-table-column prop="code" label="编码" width="160" />
        <el-table-column label="车间名称" min-width="220">
          <template #default="{ row }">
            <span class="w-name">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="描述" min-width="300">
          <template #default="{ row }">
            <span class="w-desc">{{ row.description || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <span class="st" :class="row.enabled ? 'ok' : 'off'">
              {{ row.enabled ? '启用' : '停用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" align="right">
          <template #default="{ row }">
            <!-- ★ 2026-10-26：原来用 size="small" + text，在 80% 缩放下
                 按钮又小又淡，现场反馈"看不清"。现在改为带图标的常规按钮，
                 点击区域 32px 高，配色用品牌蓝/报警红，一眼能分辨。 -->
            <el-button size="small" type="primary" plain :icon="Edit" @click="openRename(row)">
              改名
            </el-button>
            <el-button size="small" type="danger" plain :icon="Delete" @click="onDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无车间，点击右上角「新建车间」创建" :image-size="80" />
        </template>
      </el-table>

      <!-- ★ 2026-10-26：数据少时表格下方是大片空白，加说明条讲清当前状态 -->
      <div class="tips">
        <span class="tip-dot" />
        <span>
          共 <b>{{ rows.length }}</b> 个车间。
          改名只影响显示名称，编码与历史告警归属不变；已有告警或仍绑定通道的车间不能删除。
        </span>
      </div>
    </div>

    <!-- 新建弹窗 -->
    <el-dialog v-model="createVisible" title="新建车间" width="440px">
      <el-form label-width="90px">
        <el-form-item label="车间编码">
          <el-input v-model="newCode" placeholder="如 A / B / workshop_c（创建后不可改）" maxlength="32" />
        </el-form-item>
        <el-form-item label="车间名称">
          <el-input v-model="newName" placeholder="如 1号车间" maxlength="64" @keyup.enter="doCreate" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="doCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 改名弹窗 -->
    <el-dialog v-model="renameVisible" title="修改车间名称" width="420px">
      <el-input v-model="renameText" maxlength="64" @keyup.enter="doRename" />
      <div class="rename-hint">只改显示名称，编码与历史告警归属不受影响。</div>
      <template #footer>
        <el-button @click="renameVisible = false">取消</el-button>
        <el-button type="primary" @click="doRename">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page {
  padding: 18px 22px;
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 18px;
  gap: 16px;
  flex-shrink: 0;
}
.title {
  font-size: var(--fs-xl);
  font-weight: 800;
  color: var(--text);
  letter-spacing: 0.3px;
}
.sub { font-size: var(--fs-base); color: var(--text-2); margin-top: 5px; font-weight: 500; }
.btns { display: flex; gap: 9px; flex-shrink: 0; }

.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  overflow: hidden;
  box-shadow: var(--shadow-2);
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.panel > :deep(.el-table) { flex: 1; min-height: 0; }

/* 底部说明条：固定高度，不会挤压表格 */
.tips {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 12px 18px;
  border-top: 1px solid var(--border);
  background: var(--surface-2);
  font-size: var(--fs-cap);
  color: var(--text-2);
  line-height: 1.6;
}
.tips b { color: var(--text); font-weight: 800; font-variant-numeric: tabular-nums; }
.tip-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--brand);
  flex-shrink: 0;
  box-shadow: 0 0 0 3px var(--brand-soft);
}

.w-name { font-size: var(--fs-base); font-weight: 700; color: var(--text); }
.w-desc { font-size: var(--fs-base); color: var(--text-2); }
/* 状态标签做成小胶囊，比裸文字更易扫读 */
.st {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: var(--fs-cap);
  font-weight: 700;
  padding: 2px 10px;
  border-radius: var(--r-pill);
}
.st::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.st.ok { color: var(--ok); background: var(--ok-soft); }
.st.off { color: var(--text-3); background: var(--surface-3); }
.rename-hint { font-size: var(--fs-cap); color: var(--text-3); margin-top: 10px; line-height: 1.6; }

/* 表格里的操作按钮：点击区域够大、颜色分明 */
.panel :deep(.el-table .el-button + .el-button) { margin-left: 8px; }
</style>
