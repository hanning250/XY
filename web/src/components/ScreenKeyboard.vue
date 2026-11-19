<script setup lang="ts">
/**
 * 登录用屏幕键盘 —— 无物理键盘的触摸屏可输入账号密码。
 */
import { computed, ref } from 'vue'

defineProps<{
  /** 当前输入框：username | password */
  target: 'username' | 'password'
}>()

const emit = defineEmits<{
  (e: 'input', ch: string): void
  (e: 'backspace'): void
  (e: 'clear'): void
  (e: 'enter'): void
  (e: 'switch-target', t: 'username' | 'password'): void
}>()

const shift = ref(false)
const caps = ref(false)
const symbol = ref(false)

const letterRows = [
  ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
  ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],
  ['z', 'x', 'c', 'v', 'b', 'n', 'm'],
]
const numberRow = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']
const symbolRows = [
  ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')'],
  ['-', '_', '=', '+', '[', ']', '{', '}', '\\', '/'],
  ['"', "'", ':', ';', ',', '.', '?', '~'],
]

/** caps 与 shift 异或：单独按下其一为大写 */
const upper = computed(() => caps.value !== shift.value)

const rows = computed(() => {
  if (symbol.value) return symbolRows
  const letters = letterRows.map((row) =>
    row.map((c) => (upper.value ? c.toUpperCase() : c)),
  )
  return [numberRow, ...letters]
})

function tap(ch: string) {
  emit('input', ch)
  // shift 仅对下一键生效；caps 保持锁定
  if (shift.value) shift.value = false
}

function toggleShift() {
  symbol.value = false
  shift.value = !shift.value
}

function toggleCaps() {
  symbol.value = false
  caps.value = !caps.value
  shift.value = false
}
</script>

<template>
  <div class="osk" @mousedown.prevent>
    <div class="osk-bar">
      <button
        type="button"
        class="tab"
        :class="{ on: target === 'username' }"
        @click="emit('switch-target', 'username')"
      >
        用户名
      </button>
      <button
        type="button"
        class="tab"
        :class="{ on: target === 'password' }"
        @click="emit('switch-target', 'password')"
      >
        密码
      </button>
      <span class="hint">屏幕键盘</span>
    </div>
    <div v-for="(row, ri) in rows" :key="ri" class="osk-row">
      <button
        v-for="ch in row"
        :key="ch"
        type="button"
        class="key"
        @click="tap(ch)"
      >
        {{ ch }}
      </button>
    </div>
    <div class="osk-row">
      <button type="button" class="key wide" :class="{ on: shift }" @click="toggleShift">
        shift
      </button>
      <button type="button" class="key wide" :class="{ on: caps }" @click="toggleCaps">
        caps
      </button>
      <button type="button" class="key wide" @click="symbol = !symbol">
        {{ symbol ? 'ABC' : '#+=' }}
      </button>
      <button type="button" class="key space" @click="tap(' ')">空格</button>
      <button type="button" class="key wide" @click="emit('backspace')">⌫</button>
      <button type="button" class="key wide" @click="emit('clear')">清空</button>
      <button type="button" class="key wide go" @click="emit('enter')">登录</button>
    </div>
  </div>
</template>

<style scoped>
.osk {
  margin-top: 18px;
  padding: 14px 12px 16px;
  border-radius: 14px;
  background: #1a2332;
  border: 1px solid #2c3a4f;
  user-select: none;
}
.osk-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  padding: 0 4px;
}
.tab {
  border: 1px solid #3d4f68;
  background: #243044;
  color: #9eb0c7;
  border-radius: 6px;
  padding: 6px 14px;
  font-size: 14px;
  cursor: pointer;
}
.tab.on {
  background: #2b6cb0;
  border-color: #2b6cb0;
  color: #fff;
}
.hint {
  margin-left: auto;
  font-size: 13px;
  color: #6b7c93;
}
.osk-row {
  display: flex;
  justify-content: center;
  gap: 6px;
  margin-bottom: 6px;
}
.key {
  min-width: 48px;
  height: 52px;
  padding: 0 10px;
  border: none;
  border-radius: 8px;
  background: #2a3648;
  color: #e8eef6;
  font-size: 18px;
  cursor: pointer;
  touch-action: manipulation;
}
.key:active {
  background: #3a4d66;
}
.key.wide {
  min-width: 78px;
  font-size: 15px;
}
.key.space {
  flex: 1;
  max-width: 280px;
}
.key.go {
  background: #2b6cb0;
  font-weight: 600;
}
.key.on {
  background: #2b6cb0;
  color: #fff;
}
</style>
