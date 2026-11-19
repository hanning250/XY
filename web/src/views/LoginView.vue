<script setup lang="ts">
/**
 * ★ 登录页（含屏幕键盘，无物理键盘亦可登录）。
 */
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { authApi, tokenStore } from '@/api'
import ScreenKeyboard from '@/components/ScreenKeyboard.vue'

const emit = defineEmits<{ (e: 'logged-in'): void }>()

const username = ref('')
const password = ref('')
const loading = ref(false)
const errMsg = ref('')
const showOsk = ref(true)
const oskTarget = ref<'username' | 'password'>('username')

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

function onOskInput(ch: string) {
  if (oskTarget.value === 'username') username.value += ch
  else password.value += ch
}
function onOskBackspace() {
  if (oskTarget.value === 'username') username.value = username.value.slice(0, -1)
  else password.value = password.value.slice(0, -1)
}
function onOskClear() {
  if (oskTarget.value === 'username') username.value = ''
  else password.value = ''
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-box" :class="{ wide: showOsk }">
      <div class="brand">
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
        <div class="field" :class="{ focus: oskTarget === 'username' }" @click="oskTarget = 'username'">
          <el-icon><User /></el-icon>
          <input
            v-model="username"
            type="text"
            placeholder="用户名"
            autocomplete="username"
            @focus="oskTarget = 'username'"
            @keyup.enter="doLogin"
          />
        </div>
        <div class="field" :class="{ focus: oskTarget === 'password' }" @click="oskTarget = 'password'">
          <el-icon><Lock /></el-icon>
          <input
            v-model="password"
            type="password"
            placeholder="密码"
            autocomplete="current-password"
            @focus="oskTarget = 'password'"
            @keyup.enter="doLogin"
          />
        </div>

        <div v-if="errMsg" class="err">{{ errMsg }}</div>

        <button class="btn" :disabled="loading" @click="doLogin">
          {{ loading ? '登录中…' : '登 录' }}
        </button>

        <button type="button" class="osk-toggle" @click="showOsk = !showOsk">
          {{ showOsk ? '收起屏幕键盘' : '打开屏幕键盘' }}
        </button>
      </div>

      <ScreenKeyboard
        v-if="showOsk"
        :target="oskTarget"
        @input="onOskInput"
        @backspace="onOskBackspace"
        @clear="onOskClear"
        @enter="doLogin"
        @switch-target="(t) => (oskTarget = t)"
      />

      <div class="hint">
        每个车间使用独立账号，登录后仅能查看本车间的告警数据。无物理键盘时可使用屏幕键盘。
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-wrap {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at 50% 30%, var(--surface-3) 0%, var(--stage) 70%);
  overflow: auto;
  padding: 16px;
}
.login-box {
  width: 520px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 48px 44px 32px;
  box-shadow: var(--shadow-2);
}
.login-box.wide {
  width: min(900px, 97vw);
}
.brand {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 36px;
}
.logo { flex-shrink: 0; width: 52px; height: 52px; }
.title {
  font-size: 26px;
  font-weight: 600;
  color: var(--text);
  letter-spacing: 0.5px;
}
.sub {
  font-size: 14px;
  color: var(--text-2);
  margin-top: 5px;
  letter-spacing: 1px;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.field {
  display: flex;
  align-items: center;
  gap: 14px;
  background: var(--surface-3);
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  padding: 0 16px;
  height: 56px;
}
.field:focus-within,
.field.focus {
  border-color: var(--brand);
}
.field .el-icon {
  color: var(--text-2);
  font-size: 20px;
}
.field input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text);
  font-size: 18px;
}
.field input::placeholder { color: var(--text-3); }
.err {
  color: var(--danger);
  font-size: 14px;
  background: rgba(var(--danger-rgb), 0.1);
  border: 1px solid rgba(var(--danger-rgb), 0.3);
  border-radius: 6px;
  padding: 10px 14px;
}
.btn {
  height: 56px;
  background: linear-gradient(135deg, var(--brand) 0%, var(--brand-deep) 100%);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 18px;
  letter-spacing: 4px;
  cursor: pointer;
  margin-top: 4px;
}
.btn:hover:not(:disabled) {
  background: linear-gradient(135deg, var(--brand-bright) 0%, var(--brand) 100%);
}
.btn:disabled { opacity: 0.6; cursor: not-allowed; }
.osk-toggle {
  border: none;
  background: transparent;
  color: var(--brand);
  font-size: 15px;
  cursor: pointer;
  padding: 0;
  align-self: flex-start;
}
.hint {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--surface-3);
  font-size: 13px;
  color: var(--text-3);
  line-height: 1.7;
}
</style>
