<script setup lang="ts">
/**
 * 新报警弹窗（右上角浮层）。
 *
 * ★ 需求：仅在**新报警到达**时弹出，且里面放的是**真实的报警图片**
 *   （来自后端 thumbnail_url），不再画任何装饰性方框。
 */
import { computed } from 'vue'
import { Bell, Close, Picture } from '@element-plus/icons-vue'
import { withToken } from '@/api'
import { alarmTypeText } from '@/stores/alarm'
import type { AlarmBrief } from '@/types'

const props = defineProps<{ alarm: AlarmBrief | null }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'detail', a: AlarmBrief): void
}>()

const typeLabel = computed(() => {
  const a = props.alarm
  if (!a) return ''
  return a.type_text || alarmTypeText(a.alarm_type)
})

const timeText = computed(() => {
  const t = props.alarm?.alarm_time
  if (!t) return ''
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return t
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
})

/** 有图才显示图片，否则显示占位（不画假图） */
const hasImage = computed(() => !!props.alarm?.thumbnail_url && !props.alarm?.media_expired)
</script>

<template>
  <transition name="slide">
    <div v-if="alarm" class="toast">
      <div class="head">
        <el-icon class="head-ico"><Bell /></el-icon>
        <span>新的报警</span>
        <el-icon class="x" @click="emit('close')"><Close /></el-icon>
      </div>

      <div class="body">
        <!-- ★ 真实报警图片 -->
        <el-image
          v-if="hasImage"
          :src="withToken(alarm.thumbnail_url)"
          fit="cover"
          class="pic"
        >
          <template #error>
            <div class="pic-empty"><el-icon><Picture /></el-icon></div>
          </template>
        </el-image>
        <div v-else class="pic-empty"><el-icon><Picture /></el-icon></div>

        <div class="info">
          <div class="dev">{{ alarm.device_id || '未知设备' }}</div>
          <div class="type">{{ typeLabel }}</div>
          <div class="time">{{ timeText }}</div>
        </div>
      </div>

      <div class="actions">
        <button class="ghost" @click="emit('close')">稍后查看</button>
        <button class="primary" @click="emit('detail', alarm)">查看详情</button>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.toast {
  position: fixed;
  top: 68px;
  right: 18px;
  width: 380px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 9px;
  box-shadow: var(--shadow-2);
  overflow: hidden;
  z-index: 2000;
}
.head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  font-size: var(--fs-base);
  font-weight: 600;
  color: var(--text);
}
.head-ico { color: var(--warn); }
.head .x { margin-left: auto; color: var(--text-3); cursor: pointer; }
.head .x:hover { color: var(--text); }

.body { display: flex; gap: 12px; padding: 13px 14px; }
/* ★ 真实图片，无装饰框 */
.pic {
  width: 126px;
  height: 84px;
  border-radius: 5px;
  flex-shrink: 0;
  display: block;
  background: var(--surface-2);
}
.pic-empty {
  width: 126px;
  height: 84px;
  border-radius: 5px;
  flex-shrink: 0;
  background: var(--surface-2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-3);
  font-size: 20px;
}
.info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 5px; }
.dev {
  font-size: var(--fs-base);
  font-weight: 600;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.type { font-size: var(--fs-micro); color: var(--warn); font-weight: 600; }
.time {
  font-size: var(--fs-cap);
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
  margin-top: auto;
}

.actions { display: flex; gap: 8px; padding: 0 14px 14px; }
.actions button {
  flex: 1;
  padding: 8px 0;
  border-radius: 6px;
  font-size: var(--fs-micro);
  cursor: pointer;
  font-family: inherit;
  border: 1px solid var(--border-strong);
  background: transparent;
  color: var(--text);
  transition: background 0.15s;
}
.actions button:hover { background: var(--border); }
.actions .primary {
  background: var(--brand);
  border-color: var(--brand);
  color: #fff;
  font-weight: 600;
}
.actions .primary:hover { background: var(--brand); }

.slide-enter-active,
.slide-leave-active { transition: all 0.25s ease; }
.slide-enter-from,
.slide-leave-to { opacity: 0; transform: translateX(24px); }
</style>
