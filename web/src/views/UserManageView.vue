<script setup lang="ts">
/**
 * ★ 用户管理（仅 admin 可见）。
 *
 * 功能：
 *   · 账号列表（角色 / 所属车间 / 启用状态）
 *   · 新建账号（用户名 + 密码 + 车间授权）
 *   · 编辑：改名、重置密码、启用/停用、调整车间授权
 *   · 删除账号（不能删自己 / 最后一个管理员，后端兜底）
 *
 * ★ 车间分配只能在这里（管理员）操作 —— 子账号无此入口。
 */
import { computed, onMounted, ref } from 'vue'
import { Delete, Edit, Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '@/api'
import type { UserInfo, Workshop } from '@/types'
import { useAuth } from '@/stores/auth'

const auth = useAuth()
const rows = ref<UserInfo[]>([])
const workshops = ref<Workshop[]>([])
const loading = ref(false)

const isAdmin = computed(() => auth.superuser)

async function fetchAll() {
  loading.value = true
  try {
    rows.value = await adminApi.users()
    workshops.value = await adminApi.workshops()
  } finally {
    loading.value = false
  }
}

function wsNames(codes: string[]): string {
  if (!codes?.length) return '—'
  return codes
    .map((c) => workshops.value.find((w) => w.code === c)?.name || c)
    .join('、')
}

/* ---------------- 新建 ---------------- */
const createVisible = ref(false)
const createLoading = ref(false)
const form = ref({
  username: '',
  password: '',
  display_name: '',
  superuser: false,
  workshops: [] as string[],
})

function openCreate() {
  form.value = { username: '', password: '', display_name: '', superuser: false, workshops: [] }
  createVisible.value = true
}

async function doCreate() {
  const f = form.value
  if (!f.username.trim() || !f.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  if (f.password.length < 6) {
    ElMessage.warning('密码至少 6 位')
    return
  }
  if (!f.superuser && !f.workshops.length) {
    ElMessage.warning('请至少授权一个车间（或勾选「管理员」）')
    return
  }
  createLoading.value = true
  try {
    await adminApi.createUser({
      username: f.username.trim(),
      password: f.password,
      display_name: f.display_name.trim() || f.username.trim(),
      superuser: f.superuser,
      workshops: f.superuser ? [] : f.workshops,
    })
    createVisible.value = false
    ElMessage.success('账号已创建')
    await fetchAll()
  } finally {
    createLoading.value = false
  }
}

/* ---------------- 编辑 ---------------- */
const editVisible = ref(false)
const editLoading = ref(false)
const editForm = ref({
  id: 0,
  username: '',
  display_name: '',
  password: '',
  enabled: true,
  superuser: false,
  workshops: [] as string[],
})

function openEdit(u: UserInfo) {
  editForm.value = {
    id: u.id,
    username: u.username,
    display_name: u.display_name || '',
    password: '', // 留空 = 不改密码
    enabled: u.enabled,
    superuser: u.is_superuser,
    workshops: [...(u.workshops || [])],
  }
  editVisible.value = true
}

async function doEdit() {
  const f = editForm.value
  const body: Record<string, unknown> = {
    display_name: f.display_name.trim() || f.username,
    enabled: f.enabled,
    superuser: f.superuser,
    workshops: f.superuser ? [] : f.workshops,
  }
  if (f.password) {
    if (f.password.length < 6) {
      ElMessage.warning('新密码至少 6 位（留空表示不修改密码）')
      return
    }
    body.password = f.password
  }
  editLoading.value = true
  try {
    await adminApi.updateUser(f.id, body)
    editVisible.value = false
    ElMessage.success('已保存')
    await fetchAll()
  } finally {
    editLoading.value = false
  }
}

/* ---------------- 删除 ---------------- */
async function onDelete(u: UserInfo) {
  try {
    await ElMessageBox.confirm(
      `确定删除账号「${u.username}」吗？删除后无法登录。`,
      '删除账号',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  await adminApi.deleteUser(u.id)
  ElMessage.success('已删除')
  await fetchAll()
}

onMounted(fetchAll)
</script>

<template>
  <div class="page">
    <div class="head">
      <div>
        <div class="title">用户管理</div>
        <div class="sub">账号创建 / 修改 / 启停 / 车间授权 —— 车间分配仅管理员可操作</div>
      </div>
      <div class="btns">
        <el-button :icon="Refresh" @click="fetchAll">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新建账号</el-button>
      </div>
    </div>

    <div class="panel">
      <!-- ★ 2026-10-26：修正"表格只占左边一半"的观感 ——
           原来几列全是固定 width + min-width，剩余空间无处可去，
           表格右侧就空出一大片。现在：
             · 显示名 / 可见车间 用更宽的 min-width 吃掉剩余空间
             · 表格高度撑满面板（height=100%），不再是一行行往下掉
             · 文本列左对齐、状态/操作右对齐，视觉重心稳定 -->
      <el-table
        v-loading="loading"
        :data="rows"
        style="width: 100%"
        height="100%"
        row-key="id"
      >
        <el-table-column prop="username" label="用户名" width="180" />
        <el-table-column label="显示名" min-width="200">
          <template #default="{ row }">
            <span class="u-name">{{ row.display_name || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="140">
          <template #default="{ row }">
            <span class="role" :class="{ admin: row.is_superuser }">
              {{ row.is_superuser ? '管理员' : '车间用户' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="可见车间" min-width="300">
          <template #default="{ row }">
            <span class="u-ws">{{ row.is_superuser ? '全部车间' : wsNames(row.workshops) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <span class="st" :class="row.enabled ? 'ok' : 'off'">
              {{ row.enabled ? '正常' : '已停用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" align="right">
          <template #default="{ row }">
            <!-- ★ 2026-10-26：原来编辑/删除是 size="small" + text 的纯文字按钮，
                 在 80% 缩放下几乎认不出可点；当前登录账号的「删除」还会被
                 opacity 淡化到 1.69:1（实测），看着像坏了。
                 现在改成带图标的描边按钮，禁用态用灰字 + 提示语说明原因。 -->
            <el-button size="small" type="primary" plain :icon="Edit" @click="openEdit(row)">
              编辑
            </el-button>
            <el-button
              size="small"
              type="danger"
              plain
              :icon="Delete"
              :disabled="row.username === auth.subject"
              :title="row.username === auth.subject ? '不能删除当前登录的账号' : '删除该账号'"
              @click="onDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无账号" :image-size="80" />
        </template>
      </el-table>

      <!-- ★ 2026-10-26：数据少时表格下方是一大片空白面板，看着像没加载完。
           加一条常驻的说明条，把"为什么这么空"讲明白，并给出下一步动作。 -->
      <div class="tips">
        <span class="tip-dot" />
        <span>
          共 <b>{{ rows.length }}</b> 个账号。
          车间用户登录后只能看到被授权车间的数据，新增账号请点右上角「新建账号」。
        </span>
      </div>
    </div>

    <!-- 新建账号 -->
    <el-dialog v-model="createVisible" title="新建账号" width="480px">
      <el-form label-width="90px">
        <el-form-item label="用户名">
          <el-input v-model="form.username" maxlength="64" placeholder="登录用，创建后不可改" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password maxlength="64" placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item label="显示名">
          <el-input v-model="form.display_name" maxlength="64" placeholder="如：1号车间主任（可空）" />
        </el-form-item>
        <el-form-item label="角色">
          <el-checkbox v-model="form.superuser">管理员（可看全部车间并管理系统）</el-checkbox>
        </el-form-item>
        <el-form-item v-if="!form.superuser" label="可见车间">
          <el-select v-model="form.workshops" multiple placeholder="选择该账号能查看的车间" style="width: 100%">
            <el-option v-for="w in workshops" :key="w.code" :label="w.name" :value="w.code" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="doCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑账号 -->
    <el-dialog v-model="editVisible" :title="`编辑账号：${editForm.username}`" width="480px">
      <el-form label-width="90px">
        <el-form-item label="显示名">
          <el-input v-model="editForm.display_name" maxlength="64" />
        </el-form-item>
        <el-form-item label="重置密码">
          <el-input
            v-model="editForm.password"
            type="password"
            show-password
            maxlength="64"
            placeholder="留空 = 不修改密码"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="editForm.enabled" active-text="启用" inactive-text="停用" />
        </el-form-item>
        <el-form-item label="角色">
          <el-checkbox v-model="editForm.superuser">管理员</el-checkbox>
        </el-form-item>
        <el-form-item v-if="!editForm.superuser" label="可见车间">
          <el-select v-model="editForm.workshops" multiple placeholder="未选择则该账号看不到任何数据" style="width: 100%">
            <el-option v-for="w in workshops" :key="w.code" :label="w.name" :value="w.code" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editLoading" @click="doEdit">保存</el-button>
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
  /* ★ 表格撑满剩余高度，页面底部不再空一大块 */
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

.u-name { font-size: var(--fs-base); font-weight: 600; color: var(--text); }
.u-ws { font-size: var(--fs-base); color: var(--text-2); }
/* 角色与状态都做成小胶囊，扫一列就能分辨 */
.role {
  display: inline-flex;
  align-items: center;
  font-size: var(--fs-cap);
  font-weight: 600;
  padding: 2px 10px;
  border-radius: var(--r-pill);
  color: var(--text-2);
  background: var(--surface-3);
}
.role.admin { color: var(--warn); background: var(--warn-soft); font-weight: 800; }

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

.panel :deep(.el-table .el-button + .el-button) { margin-left: 8px; }
</style>
