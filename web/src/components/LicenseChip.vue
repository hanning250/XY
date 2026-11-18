<script setup lang="ts">
/**
 * ★ 顶栏授权角标：常显「授权剩余 X 个月」。
 *
 * 为什么常显而不是快到期才显示：
 *   客户需要随时知道"我还有多久要续"，而不是到期前一个月才第一次看到。
 *   但颜色只在不足 3 个月时才转橙、不足 1 个月转红 —— 平时是安静的灰蓝，
 *   不跟报警红点抢注意力。
 *
 * 点开是授权详情 + 管理员续期入口（到期后顶栏虽然被拦截页替换，
 * 拦截页里的面板是同一个组件，操作路径完全一致）。
 */
import { computed, ref } from 'vue'
import LicensePanel from '@/components/LicensePanel.vue'
import { useLicense } from '@/stores/license'

const license = useLicense()
const open = ref(false)

// ★ 2026-10-26：后端不再返回 state 字段，改为按 expired / days_left 推导
const chipClass = computed(() => {
  const i = license.info
  if (!i) return 'valid'
  if (i.expired) return 'expired'
  if (i.days_left <= 30) return 'critical'
  if (i.days_left <= 90) return 'warning'
  return 'valid'
})

/** 点开时若还没拿到数据，顺手重试一次（角标文案此时是「授权…」/「不可用」） */
function openDialog() {
  open.value = true
  if (!license.info) void license.fetch()
}
</script>

<template>
  <div
    class="chip"
    :class="chipClass"
    :title="`授权到期日 ${license.expireText || '—'}（点击查看 / 续期）`"
    @click="openDialog"
  >
    <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
      <path
        d="M12 2.8l7.2 2.9v6c0 4.3-2.9 8.2-7.2 9.5-4.3-1.3-7.2-5.2-7.2-9.5v-6z"
        fill="none"
        stroke="currentColor"
        stroke-width="1.7"
        stroke-linejoin="round"
      />
    </svg>
    <span>{{ license.chipText }}</span>
  </div>

  <el-dialog v-model="open" title="软件授权" width="520px" append-to-body>
    <LicensePanel />
  </el-dialog>
</template>

<style scoped>
.chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: var(--fs-cap);
  font-weight: 600;
  padding: 4px 9px;
  border-radius: 999px;
  cursor: pointer;
  color: var(--text-2);
  background: var(--surface-2);
  border: 1px solid var(--border);
  white-space: nowrap;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}
.chip:hover {
  color: var(--brand-deep);
  border-color: var(--brand-line);
  background: var(--brand-soft);
}
/* 不足 3 个月：橙；不足 1 个月与已到期：红（唯一会抢注意力的两种状态） */
.chip.warning {
  color: var(--warn);
  background: rgba(var(--warn-rgb), 0.1);
  border-color: rgba(var(--warn-rgb), 0.36);
}
.chip.critical,
.chip.expired {
  color: var(--danger);
  background: var(--danger-soft);
  border-color: var(--danger-line);
}
.chip.critical {
  animation: chipPulse 1.6s ease-in-out infinite;
}
@keyframes chipPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(var(--danger-rgb), 0.28); }
  50% { box-shadow: 0 0 0 4px rgba(var(--danger-rgb), 0); }
}
@media (prefers-reduced-motion: reduce) {
  .chip.critical { animation: none; }
}
/* 窄屏（值守大屏多用 1080p，一般不触发）隐藏文字只留图标 */
@media (max-width: 1100px) {
  .chip span { display: none; }
}
</style>
