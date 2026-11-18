<script setup lang="ts">
/**
 * ★ 报警提醒设置（声音时长 / 闪烁时长）。
 *
 * 为什么放在顶栏、为什么是弹窗而不是设置页：
 *   现场调这玩意儿是**试出来的** —— 站在值班室看效果，太长就短一点。
 *   让人跳去"系统设置"页再回来，早就忘了刚才多长。所以做成一键弹出、
 *   拖动即生效、关掉就记住。
 *
 * 两个滑块 + 一个"试一下"按钮：
 *   · 声音时长 0~60 秒（0 = 只闪不响）
 *   · 闪烁时长 1~60 秒，**同时决定全屏浮层糊多久**（产品口径：一次报警
 *     就是一个窗口，响、闪、糊屏同起同落，不给第三个滑块）
 *
 * 存 localStorage（见 useAlarmTiming），改完**下一条报警立即生效**，
 * 不需要重启后端、也不需要刷新页面。
 */
import { computed, ref, watch } from 'vue'
import { Close, Headset, WarningFilled } from '@element-plus/icons-vue'
import {
  flashSeconds,
  fullscreenMs,
  isCustomized,
  resetTiming,
  setTiming,
  soundSeconds,
} from '@/composables/useAlarmTiming'
import { useAlarmSound } from '@/composables/useAlarmSound'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

const open = computed({
  get: () => props.modelValue,
  set: (v: boolean) => emit('update:modelValue', v),
})

const sound = useAlarmSound()

/** 滑块值（本地缓冲，松手时写入配置；拖动过程中实时显示秒数） */
const soundVal = ref(soundSeconds.value)
const flashVal = ref(flashSeconds.value)

// 打开面板时同步一次（别的标签页可能改过）
watch(open, (v) => {
  if (v) {
    soundVal.value = soundSeconds.value
    flashVal.value = flashSeconds.value
  }
})

// 拖动即生效：现场边拖边听/边看，不用点保存
watch(soundVal, (v) => {
  setTiming({ sound: v })
  soundSeconds.value = v
})
watch(flashVal, (v) => {
  const n = Math.max(1, Number(v) || 1)
  setTiming({ flash: n })
  flashSeconds.value = n
})

/** 试听：按当前设置响一次（让人直接判断长短合不合适） */
function preview() {
  sound.play()
}
/** 试闪：把当前设置轮流演示一遍——直接触发一次"模拟"太重，
 *  这里只提示用户下一条报警会按新时长走，避免误造报警数据 */
const hint = ref('')
let hintTimer: number | null = null
function showHint(t: string) {
  hint.value = t
  if (hintTimer !== null) window.clearTimeout(hintTimer)
  hintTimer = window.setTimeout(() => (hint.value = ''), 2600)
}

function onReset() {
  resetTiming()
  soundVal.value = 15
  flashVal.value = 15
  showHint('已恢复默认：声音 15 秒、闪烁 15 秒')
}

function close() {
  open.value = false
}

/** 面板里的说明随数值变化，避免"调了不知道影响什么" */
const soundNote = computed(() => {
  const s = soundVal.value
  if (s === 0) return '不发声，只闪屏（顶栏喇叭仍视为开启）'
  if (s <= 5) return '短促提醒，适合报警频繁的产线'
  if (s <= 20) return '默认量级，兼顾"听得见"和"不烦人"'
  return '长时间响铃，适合人少的夜班，注意可能盖过现场广播'
})

const flashNote = computed(() => {
  const s = flashVal.value
  if (s <= 5) return '一闪而过，适合一屏十几条的高频场景'
  if (s <= 20) return '默认量级，与声音同起同落'
  return '长时间糊屏，人不在跟前时也不会漏看'
})

/**
 * 滑块的"已填充"比例 —— 原生 range 的轨道不会自己渐变，
 * 用 CSS 变量把百分比传给 ::-webkit-slider-runnable-track。
 */
function pct(v: number, min: number, max: number): string {
  const p = ((Number(v) - min) / (max - min)) * 100
  return `${Math.min(100, Math.max(0, p))}%`
}
</script>

<template>
  <transition name="pop">
    <div v-if="open" class="mask" @click.self="close">
      <div class="panel">
        <header class="p-head">
          <span class="p-title">报警提醒设置</span>
          <span class="p-x" @click="close"><el-icon :size="16"><Close /></el-icon></span>
        </header>

        <p class="p-intro">
          调整后<b>下一条报警立即生效</b>，只影响当前这台值守机，无需重启服务。
        </p>

        <!-- ① 声音 -->
        <section class="row">
          <div class="r-head">
            <span class="r-name">
              <el-icon><Headset /></el-icon>
              声音报警时长
            </span>
            <span class="r-val">{{ soundVal }}<i>秒</i></span>
          </div>
          <div class="slider-wrap">
            <input
              v-model.number="soundVal"
              class="slider"
              type="range"
              min="0"
              max="60"
              step="1"
              :style="{ '--pct': pct(soundVal, 0, 60) }"
              aria-label="声音报警时长（秒）"
            />
            <span class="ticks"><b>0</b><b>15</b><b>30</b><b>45</b><b>60</b></span>
          </div>
          <div class="r-note">{{ soundNote }}</div>
        </section>

        <!-- ② 闪烁（含全屏） -->
        <section class="row">
          <div class="r-head">
            <span class="r-name">
              <el-icon><WarningFilled /></el-icon>
              屏幕闪烁时长
            </span>
            <span class="r-val">{{ flashVal }}<i>秒</i></span>
          </div>
          <div class="slider-wrap">
            <input
              v-model.number="flashVal"
              class="slider"
              type="range"
              min="1"
              max="60"
              step="1"
              :style="{ '--pct': pct(flashVal, 1, 60) }"
              aria-label="屏幕闪烁时长（秒）"
            />
            <span class="ticks"><b>1</b><b>15</b><b>30</b><b>45</b><b>60</b></span>
          </div>
          <div class="r-note">{{ flashNote }}</div>
        </section>

        <!-- ★ 联动说明：全屏自动收起跟着闪烁走，避免现场以为"两个设置对不上" -->
        <div class="linkage">
          <span class="lk-label">全屏报警自动收起</span>
          <span class="lk-val">跟随上方闪烁时长 · {{ Math.round(fullscreenMs / 1000) }} 秒</span>
        </div>

        <div v-if="hint" class="hint">{{ hint }}</div>

        <footer class="p-foot">
          <button v-if="isCustomized" class="btn ghost" @click="onReset">恢复默认</button>
          <button class="btn" :disabled="!sound.enabled.value" @click="preview">
            试听声音
          </button>
          <button class="btn primary" @click="close">完成</button>
        </footer>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  z-index: 2500;
  background: rgba(8, 16, 28, 0.42);
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  padding: 64px 20px 20px;
}

.panel {
  width: 430px;
  max-width: calc(100vw - 40px);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: var(--shadow-2);
  padding: 16px 18px 14px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.p-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.p-title { font-size: var(--fs-md); font-weight: 700; color: var(--text); }
.p-x {
  color: var(--text-3);
  cursor: pointer;
  display: flex;
  padding: 4px;
  border-radius: 5px;
}
.p-x:hover { color: var(--text); background: var(--surface-3); }

.p-intro {
  margin: 0;
  font-size: var(--fs-cap);
  line-height: 1.6;
  color: var(--text-2);
  background: var(--surface-2);
  border-left: 3px solid var(--brand-line);
  border-radius: 4px;
  padding: 8px 10px;
}
.p-intro b { color: var(--text); }

.row { display: flex; flex-direction: column; gap: 7px; }
.r-head { display: flex; align-items: baseline; justify-content: space-between; }
.r-name {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs-base);
  font-weight: 600;
  color: var(--text);
}
.r-name .el-icon { color: var(--brand); }
.r-val {
  font-size: 20px;
  font-weight: 700;
  color: var(--brand);
  font-variant-numeric: tabular-nums;
}
.r-val i { font-size: var(--fs-cap); font-style: normal; color: var(--text-2); margin-left: 2px; }

.slider-wrap { display: flex; flex-direction: column; gap: 2px; }
/* 自绘滑块：Element Plus 没有 range 组件，原生 input 最省依赖且键盘可达 */
.slider {
  width: 100%;
  height: 22px;
  margin: 0;
  appearance: none;
  background: transparent;
  cursor: pointer;
}
.slider::-webkit-slider-runnable-track {
  height: 5px;
  border-radius: 3px;
  background: linear-gradient(
    to right,
    var(--brand) 0%,
    var(--brand) var(--pct, 25%),
    var(--border-strong) var(--pct, 25%),
    var(--border-strong) 100%
  );
}
.slider::-webkit-slider-thumb {
  appearance: none;
  width: 17px;
  height: 17px;
  margin-top: -6px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid var(--brand);
  box-shadow: 0 1px 4px rgba(16, 32, 52, 0.25);
  cursor: pointer;
}
.slider::-moz-range-track {
  height: 5px;
  border-radius: 3px;
  background: var(--border-strong);
}
.slider::-moz-range-progress {
  height: 5px;
  border-radius: 3px;
  background: var(--brand);
}
.slider::-moz-range-thumb {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid var(--brand);
  cursor: pointer;
}
.slider:focus-visible { outline: 2px solid var(--brand-line); outline-offset: 3px; }

.ticks {
  display: flex;
  justify-content: space-between;
  font-size: var(--fs-micro);
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
}
.ticks b { font-weight: 400; }

.r-note { font-size: var(--fs-cap); color: var(--text-3); line-height: 1.5; }

.linkage {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: var(--fs-cap);
  background: var(--brand-soft);
  border: 1px solid var(--brand-line);
  border-radius: 6px;
  padding: 8px 11px;
}
.lk-label { color: var(--brand-deep); font-weight: 600; }
.lk-val { color: var(--brand-deep); font-variant-numeric: tabular-nums; }

.hint {
  font-size: var(--fs-cap);
  color: var(--ok);
  background: rgba(var(--ok-rgb), 0.1);
  border: 1px solid rgba(var(--ok-rgb), 0.3);
  border-radius: 6px;
  padding: 7px 10px;
}

.p-foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 2px;
}
.btn {
  font-family: inherit;
  font-size: var(--fs-micro);
  font-weight: 600;
  padding: 8px 16px;
  border-radius: 6px;
  border: 1px solid var(--border-strong);
  background: var(--surface);
  color: var(--text-2);
  cursor: pointer;
  transition: all 0.15s;
}
.btn:hover:not(:disabled) { border-color: var(--brand); color: var(--brand-deep); }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn.ghost { margin-right: auto; border-color: transparent; background: transparent; }
.btn.ghost:hover { background: var(--surface-3); }
.btn.primary {
  background: var(--brand);
  border-color: var(--brand);
  color: #fff;
}
.btn.primary:hover { background: var(--brand-deep); }

.pop-enter-active,
.pop-leave-active { transition: opacity 0.16s ease; }
.pop-enter-from,
.pop-leave-to { opacity: 0; }
</style>
