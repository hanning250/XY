<script setup lang="ts">
/**
 * 顶栏：标题 + 通知铃铛（红点）+ 头像下拉（修改密码 / 退出登录）。
 *
 * ★ 登录体系已启用（JWT）：
 *   · 退出登录 → 清 token 回登录页
 *   · 修改密码 → 弹窗（旧密码校验，成功后强制重新登录）
 */
import { ref } from 'vue'
import { ArrowDown, Key, Setting, SwitchButton } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { authApi, tokenStore } from '@/api'
import AlarmTimingPanel from '@/components/AlarmTimingPanel.vue'
import LicenseChip from '@/components/LicenseChip.vue'
import { useAlarmSound } from '@/composables/useAlarmSound'
import { flashSeconds, isCustomized, soundSeconds } from '@/composables/useAlarmTiming'

/** ★ 异常声音报警开关（顶栏一个按钮，状态全局共用并记忆） */
const sound = useAlarmSound()

/** ★ 报警提醒设置面板（声音时长 / 闪烁时长，现场可调） */
const timingOpen = ref(false)

const props = defineProps<{
  title: string
  /** ★ 2026-10-26：铃铛红点已移除（纯展示看板不展示累计未处理数），
   *  此字段保留仅为兼容调用方传参。 */
  pending?: number
  userName?: string
}>()

const emit = defineEmits<{
  /** ★ 修改密码成功后触发（父组件回到登录页） */
  (e: 'password-changed'): void
}>()

const displayName = () => props.userName || 'admin'
const initial = () => (displayName()[0] || 'A').toUpperCase()

/* ---------------- 修改密码弹窗 ---------------- */
const pwdVisible = ref(false)
const oldPwd = ref('')
const newPwd = ref('')
const newPwd2 = ref('')
const pwdLoading = ref(false)

function openPwdDialog() {
  oldPwd.value = ''
  newPwd.value = ''
  newPwd2.value = ''
  pwdVisible.value = true
}

async function doChangePassword() {
  if (!oldPwd.value || !newPwd.value || !newPwd2.value) {
    ElMessage.warning('请填写完整')
    return
  }
  if (newPwd.value.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  if (newPwd.value !== newPwd2.value) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  pwdLoading.value = true
  try {
    await authApi.changePassword(oldPwd.value, newPwd.value)
    pwdVisible.value = false
    await ElMessageBox.alert(
      '密码已修改，请使用新密码重新登录。',
      '修改成功',
      { confirmButtonText: '重新登录', type: 'success' },
    )
    emit('password-changed')
  } catch {
    /* 错误提示由 axios 拦截器统一处理（400 旧密码错误等） */
  } finally {
    pwdLoading.value = false
  }
}

/* ---------------- 退出登录 ---------------- */
async function onCommand(cmd: string) {
  if (cmd === 'password') {
    openPwdDialog()
  } else if (cmd === 'logout') {
    try {
      await ElMessageBox.confirm('确定退出当前账号吗？', '退出登录', {
        confirmButtonText: '退出',
        cancelButtonText: '取消',
        type: 'warning',
      })
    } catch {
      return
    }
    tokenStore.clear()
    // ★ 与 api.ts 401 处理同一通道：App.vue 监听后回登录页
    window.dispatchEvent(new CustomEvent('isup:unauthorized'))
  }
}
</script>

<template>
  <header class="topbar">
    <div class="page-title">{{ title }}</div>

    <div class="right">
      <!-- ★ 授权角标：常显「剩余 X 个月」，点开可续期 -->
      <LicenseChip />

      <!-- ★ 声音报警开关：检出异常结果时响铃（现场值守的"耳朵"）
           正在响铃（时长可配，默认 15 秒）时按钮同步脉动 —— 现场一眼看出"还在响"。 -->
      <div
        class="sound"
        :class="{ off: !sound.enabled.value, ringing: sound.ringing.value }"
        :title="
          sound.ringing.value
            ? '正在响铃（点击可立即静音）'
            : sound.enabled.value
              ? '异常声音报警：已开启（点击关闭）'
              : '异常声音报警：已关闭（点击开启）'
        "
        @click="sound.toggle()"
      >
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
          <path
            d="M4 9.5h3.2L12 5.4v13.2L7.2 14.5H4z"
            fill="currentColor"
            stroke="currentColor"
            stroke-width="1.2"
            stroke-linejoin="round"
          />
          <template v-if="sound.enabled.value">
            <path d="M15.4 9.2a4 4 0 0 1 0 5.6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
            <path d="M18 6.8a7.6 7.6 0 0 1 0 10.4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          </template>
          <template v-else>
            <path d="M16 9.5l5 5M21 9.5l-5 5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          </template>
        </svg>
      </div>

      <!-- ★ 报警提醒设置：调声音/闪烁时长（现场自己调，立即生效）
           带"已修改"小点，避免有人调完忘了自己改过默认值 -->
      <div
        class="gear"
        :class="{ active: timingOpen }"
        :title="`报警提醒设置（声音 ${soundSeconds} 秒 / 闪烁 ${flashSeconds} 秒）`"
        @click="timingOpen = true"
      >
        <el-icon :size="17"><Setting /></el-icon>
        <span v-if="isCustomized" class="gear-dot" />
      </div>

      <!-- ★ 头像 + 下拉 -->
      <el-dropdown trigger="click" @command="onCommand">
        <div class="avatar-wrap">
          <div class="avatar">{{ initial() }}</div>
          <span class="avatar-name">{{ displayName() }}</span>
          <el-icon class="caret"><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="password">
              <el-icon><Key /></el-icon>修改密码
            </el-dropdown-item>
            <el-dropdown-item command="logout" divided>
              <el-icon><SwitchButton /></el-icon>退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <!-- ★ 报警提醒设置面板（声音时长 / 闪烁时长） -->
    <AlarmTimingPanel v-model="timingOpen" />

    <!-- 修改密码弹窗 -->
    <el-dialog v-model="pwdVisible" title="修改密码" width="400px" append-to-body>
      <el-form label-width="90px" @submit.prevent>
        <el-form-item label="旧密码">
          <el-input v-model="oldPwd" type="password" show-password autocomplete="current-password" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="newPwd" type="password" show-password autocomplete="new-password" placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="newPwd2" type="password" show-password autocomplete="new-password" @keyup.enter="doChangePassword" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdVisible = false">取消</el-button>
        <el-button type="primary" :loading="pwdLoading" @click="doChangePassword">确定</el-button>
      </template>
    </el-dialog>
  </header>
</template>

<style scoped>
.topbar {
  height: 60px;
  flex-shrink: 0;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 22px;
  background: var(--surface);
  box-shadow: var(--shadow-1);
}
.page-title {
  font-size: var(--fs-xl);              /* 视觉 16px（原 14.4px） */
  font-weight: 800;
  color: var(--text);
  letter-spacing: 0.3px;
}
.right { display: flex; align-items: center; gap: 18px; }
/* ★ 报警提醒设置齿轮：与喇叭同一视觉语言；改过默认值时带一个品牌色小点 */
.gear {
  position: relative;
  display: flex;
  align-items: center;
  color: var(--text-2);
  cursor: pointer;
  transition: color 0.15s, transform 0.25s;
}
.gear:hover { color: var(--brand); transform: rotate(35deg); }
.gear.active { color: var(--brand); }
.gear-dot {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--brand);
  border: 2px solid var(--surface);
}
/* ★ 声音开关：开启=品牌蓝，关闭=灰并带斜杠（图标本身已表达） */
.sound {
  display: flex;
  align-items: center;
  color: var(--brand);
  cursor: pointer;
  transition: color 0.15s, transform 0.15s;
}
.sound:hover { color: var(--brand-deep); transform: scale(1.06); }
.sound.off { color: var(--text-3); }
/* ★ 响铃中：按钮转报警红并脉动，与状态框频闪同步 */
.sound.ringing {
  color: var(--danger);
  animation: soundPulse 0.75s ease-in-out infinite;
}
@keyframes soundPulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.22); opacity: 0.55; }
}
@media (prefers-reduced-motion: reduce) {
  .sound.ringing { animation: none; }
}
.avatar-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  outline: none;
}
.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--brand), var(--brand-deep));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--fs-cap);
  font-weight: 800;
  color: #fff;
  box-shadow: 0 2px 6px rgba(var(--brand-rgb), 0.35);
}
.avatar-name { font-size: var(--fs-base); color: var(--text); font-weight: 600; }
.caret { font-size: var(--fs-micro); color: var(--text-3); }
</style>
