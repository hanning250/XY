<script setup lang="ts">
/**
 * ★ 应用根组件 —— 唯一登录门禁。
 *
 * · jwt：无 token 显示 LoginView；登录成功或本地已有 token 进 AlarmBoard
 * · anonymous：LoginView 拉 /api/auth/config 后直接 emit，进入看板
 */
import { onMounted, onUnmounted, ref } from 'vue'
import AlarmBoard from '@/views/AlarmBoard.vue'
import LoginView from '@/views/LoginView.vue'
import { tokenStore } from '@/api'

const authed = ref(false)

function onUnauthorized() {
  tokenStore.clear()
  authed.value = false
}

onMounted(() => {
  if (tokenStore.get()) authed.value = true
  window.addEventListener('isup:unauthorized', onUnauthorized)
})

onUnmounted(() => {
  window.removeEventListener('isup:unauthorized', onUnauthorized)
})

function onLoggedIn() {
  authed.value = true
}
</script>

<template>
  <LoginView v-if="!authed" @logged-in="onLoggedIn" />
  <AlarmBoard v-else />
</template>
