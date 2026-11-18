<script setup lang="ts">
/**
 * ★ 登录页。
 *
 * 多车间场景下每个车间一套账号，登录后：
 *   · token 里带 workshops 列表 → 决定能看到哪些车间的数据
 *   · 之后所有请求自动带 Authorization 头（见 api.ts 拦截器）
 */
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { authApi, tokenStore } from '@/api'

const emit = defineEmits<{ (e: 'logged-in'): void }>()

const username = ref('')
const password = ref('')
const loading = ref(false)
const errMsg = ref('')

/** 未启用登录（开发模式）时，直接放行 */
const loginEnabled = ref(true)

onMounted(async () => {
  try {
    const cfg = await authApi.config()
    loginEnabled.value = !!cfg?.login_enabled
    if (!loginEnabled.value) {
      emit('logged-in')
    }
  } catch {
    /* 拿不到配置就按需要登录处理 */
  }
})

async function doLogin() {
  if (!username.value || !password.value) {
    errMsg.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  errMsg.value = ''
  try {
    const res = await authApi.login(username.value, password.value)
    tokenStore.set(res.access_token)
    ElMessage.success('登录成功')
    emit('logged-in')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    errMsg.value = err?.response?.data?.detail || '登录失败，请检查用户名与密码'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-box">
      <div class="brand">
        <!-- 三环标志意象：三重空心圆环 + 梯形基座 -->
        <svg class="logo" viewBox="0 0 24 24" width="34" height="34" aria-hidden="true">
          <defs>
            <linearGradient id="shRingLogin" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stop-color="#91c8e6" />
              <stop offset="100%" stop-color="#155ba3" />
            </linearGradient>
          </defs>
          <g fill="none" stroke="url(#shRingLogin)" stroke-width="1.5">
            <circle cx="12" cy="9.6" r="8" />
            <circle cx="12" cy="9.6" r="5.3" />
            <circle cx="12" cy="9.6" r="2.6" />
          </g>
          <path d="M9.9 17.2h4.2l1.5 4.2H8.4z" fill="url(#shRingLogin)" />
        </svg>
        <div>
          <div class="title">工业安全监控平台</div>
          <div class="sub">德阳三环</div>
        </div>
      </div>

      <div class="form">
        <div class="field">
          <el-icon><User /></el-icon>
          <input
            v-model="username"
            type="text"
            placeholder="用户名"
            autocomplete="username"
            @keyup.enter="doLogin"
          />
        </div>
        <div class="field">
          <el-icon><Lock /></el-icon>
          <input
            v-model="password"
            type="password"
            placeholder="密码"
            autocomplete="current-password"
            @keyup.enter="doLogin"
          />
        </div>

        <div v-if="errMsg" class="err">{{ errMsg }}</div>

        <button class="btn" :disabled="loading" @click="doLogin">
          {{ loading ? '登录中…' : '登 录' }}
        </button>
      </div>

      <div class="hint">
        每个车间使用独立账号，登录后仅能查看本车间的告警数据。
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-wrap {
  /* ★ 用 100% 而不是 100vh：vh 只认视口原始尺寸，不随 #app 的
     transform:scale 缩放，会导致底部留出 20% 空白；
     百分比则沿 html→body→#app 的高度链解析，缩放后正好铺满整屏。 */
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at 50% 30%, var(--surface-3) 0%, var(--stage) 70%);
}
.login-box {
  width: 380px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 32px 28px 22px;
  box-shadow: var(--shadow-2);
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 28px;
}
.logo {
  flex-shrink: 0;
}
.title {
  font-size: var(--fs-lg);
  font-weight: 600;
  color: var(--text);
  letter-spacing: 0.5px;
}
.sub {
  font-size: var(--fs-micro);
  color: var(--text-2);
  margin-top: 3px;
  letter-spacing: 1px;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.field {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--surface-3);
  border: 1px solid var(--border-strong);
  border-radius: 4px;
  padding: 0 12px;
  height: 40px;
}
.field:focus-within {
  border-color: var(--brand);
}
.field .el-icon {
  color: var(--text-2);
  font-size: var(--fs-base);
}
.field input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text);
  font-size: var(--fs-base);
}
.field input::placeholder {
  color: var(--text-3);
}
.err {
  color: var(--danger);
  font-size: var(--fs-cap);
  background: rgba(var(--danger-rgb), 0.1);
  border: 1px solid rgba(var(--danger-rgb), 0.3);
  border-radius: 4px;
  padding: 7px 10px;
}
.btn {
  height: 40px;
  background: linear-gradient(135deg, var(--brand) 0%, var(--brand-deep) 100%);
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: var(--fs-base);
  letter-spacing: 3px;
  cursor: pointer;
  margin-top: 4px;
}
.btn:hover:not(:disabled) {
  background: linear-gradient(135deg, var(--brand-bright) 0%, var(--brand) 100%);
}
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.hint {
  margin-top: 20px;
  padding-top: 14px;
  border-top: 1px solid var(--surface-3);
  font-size: var(--fs-micro);
  color: var(--text-3);
  line-height: 1.6;
}
</style>
