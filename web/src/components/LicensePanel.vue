<script setup lang="ts">
/**
 * ★ 授权信息 + 授权码续期（拦截页与顶栏弹窗共用同一块面板）。
 *
 * 信息按"管理员要知道的三件事"排序：哪天到期 → 还剩多久 → 怎么续。
 * 续期输入只对 admin 显示（后端也只允许 admin），普通账号看到的是
 * 「请联系管理员续期」——避免他们拿着授权码反复试。
 */
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuth } from '@/stores/auth'
import { useLicense } from '@/stores/license'

defineProps<{ gate?: boolean }>()

const license = useLicense()
const auth = useAuth()

const code = ref('')
const submitting = ref(false)

const isAdmin = computed(() => auth.superuser)

// ★ 2026-10-26：授权状态改由 expired / days_left 推导
//   （后端不再返回 state 字段，改为更直观的 expired + days_left）
const stateText = computed(() => {
  const i = license.info
  if (!i) return '授权…'
  if (i.expired) return '授权已到期'
  if (i.days_left <= 30) return '即将到期'
  return '授权有效'
})

/** 状态样式类（模板里 :class 用） */
const stateClass = computed(() => {
  const i = license.info
  if (!i) return 'valid'
  if (i.expired) return 'expired'
  if (i.days_left <= 30) return 'critical'
  if (i.days_left <= 90) return 'warning'
  return 'valid'
})

const remainingText = computed(() => {
  const i = license.info
  if (!i) return '—'
  if (i.expired) return '已到期'
  if (i.days_left <= 30) return `${i.days_left} 天`
  return `${Math.floor(i.days_left / 30)} 个月`
})

/** ISO → 本地「YYYY-MM-DD HH:mm」 */
function fmt(t?: string): string {
  if (!t) return '—'
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return t.slice(0, 16).replace('T', ' ')
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

async function submit() {
  const v = code.value.trim()
  if (!v) {
    ElMessage.warning('请先粘贴授权码')
    return
  }
  submitting.value = true
  try {
    const fresh = await license.renew(v)
    ElMessage.success(`续期成功：到期日 ${fresh.expires_on ?? '—'}`)
    code.value = ''
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    ElMessage.error(err?.response?.data?.detail || '续期失败，请检查授权码')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="lic" :class="[stateClass, { gate }]">
    <!-- 状态头 -->
    <div class="head">
      <div class="badge" :class="stateClass">
        <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
          <path
            d="M12 2.8l7.2 2.9v6c0 4.3-2.9 8.2-7.2 9.5-4.3-1.3-7.2-5.2-7.2-9.5v-6z"
            fill="none"
            stroke="currentColor"
            stroke-width="1.6"
            stroke-linejoin="round"
          />
          <path
            v-if="!license.info?.expired"
            d="M8.6 12.1l2.4 2.4 4.4-4.6"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <path v-else d="M9 9l6 6M15 9l-6 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
        </svg>
        <span>{{ stateText }}</span>
      </div>
      <div class="head-main">
        <div class="title">软件授权</div>
        <div class="sub">
          自首次启动激活起计算 · 到期后系统停用 · 续期码 10 分钟内有效
        </div>
      </div>
    </div>

    <!-- 三个数字：到期日 / 剩余 / ★ 服务器时间 -->
    <div class="grid">
      <div class="cell">
        <div class="c-label">到期日</div>
        <div class="c-value" :class="{ hot: stateClass === 'critical' || stateClass === 'expired' }">
          {{ license.info?.expires_on || '—' }}
        </div>
      </div>
      <div class="cell">
        <div class="c-label">剩余</div>
        <div class="c-value" :class="{ hot: license.shouldWarn || stateClass === 'expired' }">
          {{ remainingText }}
        </div>
      </div>
      <div class="cell">
        <div class="c-label">激活日</div>
        <div class="c-value">{{ fmt(license.info?.activated_at ?? undefined).slice(0, 10) }}</div>
      </div>
    </div>

    <!-- ★★ 服务器时间（到期后客户要报给供应商换续期码） -->
    <div class="server-time" :class="{ urgent: license.info?.expired }">
      <div class="st-label">服务器时间（授权基准）</div>
      <div class="st-value">{{ fmt(license.info?.server_now) }}</div>
      <div class="st-hint" v-if="license.info?.expired">
        授权已到期 —— 请把上面这个时间告诉供应商，我们会给您一个
        {{ license.info?.window_minutes || 10 }} 分钟内有效的续期码。
      </div>
      <div class="st-hint" v-else>
        授权以服务器时间为准（改系统时间不会延长授权）
      </div>
    </div>

    <!-- 续期 -->
    <div class="renew">
      <div class="r-head">
        <span class="r-title">续期</span>
        <span v-if="!isAdmin" class="r-hint">仅管理员可续期，请联系系统管理员</span>
      </div>
      <template v-if="isAdmin">
        <el-input
          v-model="code"
          type="textarea"
          :rows="2"
          resize="none"
          placeholder="粘贴供应商提供的续期码（形如 ISUP2-xxxxxxxx.yyyyyyyy），10 分钟内有效"
        />
        <div class="r-actions">
          <el-button type="primary" :loading="submitting" @click="submit">立即续期</el-button>
          <span class="r-note">授权码只能往后延长，不会缩短当前有效期</span>
        </div>
      </template>
      <div v-else class="r-disabled">请联系供应商获取授权码，并由管理员在系统中输入。</div>
    </div>
  </div>
</template>

<style scoped>
.lic {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.lic.gate {
  gap: 18px;
}

/* ---- 状态头 ---- */
.head {
  display: flex;
  align-items: center;
  gap: 12px;
}
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs-cap);
  font-weight: 600;
  padding: 5px 10px;
  border-radius: 6px;
  color: var(--ok);
  background: rgba(var(--ok-rgb), 0.1);
  border: 1px solid rgba(var(--ok-rgb), 0.32);
  white-space: nowrap;
}
.badge.warning {
  color: var(--warn);
  background: rgba(var(--warn-rgb), 0.12);
  border-color: rgba(var(--warn-rgb), 0.38);
}
.badge.critical,
.badge.expired {
  color: var(--danger);
  background: var(--danger-soft);
  border-color: var(--danger-line);
}
.head-main {
  min-width: 0;
}
.title {
  font-size: var(--fs-base);
  font-weight: 700;
  color: var(--text);
  letter-spacing: 0.2px;
}
.sub {
  font-size: var(--fs-cap);
  color: var(--text-3);
  margin-top: 2px;
}

/* ---- 三个数字 ---- */
.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.cell {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
}
.c-label {
  font-size: var(--fs-micro);
  color: var(--text-3);
  margin-bottom: 4px;
}
.c-value {
  font-size: var(--fs-md);
  font-weight: 700;
  color: var(--text);
  font-variant-numeric: tabular-nums;
}
.c-value.hot {
  color: var(--danger);
}

/* ---- 续期 ---- */
.renew {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-top: 1px solid var(--border);
  padding-top: 14px;
}
.r-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.r-title {
  font-size: var(--fs-micro);
  font-weight: 600;
  color: var(--text);
}
.r-hint {
  font-size: var(--fs-cap);
  color: var(--warn);
}
.r-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.r-note {
  font-size: var(--fs-micro);
  color: var(--text-3);
}
.r-disabled {
  font-size: var(--fs-cap);
  color: var(--text-2);
  background: var(--surface-2);
  border: 1px dashed var(--border-strong);
  border-radius: 6px;
  padding: 10px 12px;
}

/* ---- 续期历史 ---- */
.history {
  border-top: 1px solid var(--border);
  padding-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.h-title {
  font-size: var(--fs-cap);
  font-weight: 600;
  color: var(--text-2);
}
.h-line {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--fs-cap);
  color: var(--text-2);
  font-variant-numeric: tabular-nums;
}
.h-arrow {
  color: var(--brand);
}
.h-exp {
  font-weight: 600;
  color: var(--text);
}
.h-to {
  color: var(--text-3);
}

/* ---- ★ 服务器时间展示（到期后客户要报给供应商） ---- */
.server-time {
  margin: 12px 0;
  padding: 12px 14px;
  border-radius: 8px;
  background: var(--surface-2);
  border: 1px solid var(--border);
}
.server-time.urgent {
  background: color-mix(in srgb, var(--danger) 8%, var(--surface));
  border-color: color-mix(in srgb, var(--danger) 35%, var(--border));
}
.st-label { font-size: 12px; color: var(--text-2); margin-bottom: 4px; }
.st-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.3px;
}
.server-time.urgent .st-value { color: var(--danger); }
.st-hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-2);
  line-height: 1.5;
}
</style>
