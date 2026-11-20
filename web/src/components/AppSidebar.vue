<script setup lang="ts">
/**
 * 左侧边栏 —— 多页面导航。
 *
 * ★ 按角色显示菜单：
 *   · 所有人：报警看板 / 数据分析 / 实时监控 / 设备管理
 *   · 仅 admin（superuser）：车间管理 / 用户管理
 *
 * 「报警看板」= 态势带 + 实况画面 + 报警列表，是默认落地页；
 * 「数据分析」= 趋势/时段/工位/区域×类型汇总（从看板展开区独立成页）；
 * 「实时监控」保留值守大屏形态。
 */
import { computed } from 'vue'
import {
  Bell,
  DataAnalysis,
  Monitor,
  OfficeBuilding,
  User,
  VideoCamera,
} from '@element-plus/icons-vue'

const props = defineProps<{
  /** ★ 2026-10-26：原「未处理数」角标已移除（纯展示看板不做处置流转，
   *  5746 这种只涨不跌的数字对甲方没有行动价值）。此字段保留但不再展示，
   *  仅为兼容调用方传参。 */
  pending?: number
  /** ★ 当前登录人是否管理员（决定是否显示管理菜单） */
  superuser: boolean
}>()

const emit = defineEmits<{ (e: 'nav', key: string): void }>()

const active = defineModel<string>({ default: 'alarm' })

interface NavItem {
  key: string
  label: string
  icon: unknown
  /** 仅管理员可见 */
  adminOnly?: boolean
}

const items = computed<NavItem[]>(() => [
  // ★ 2026-10：看板与报警合并为一页 —— 态势、实况画面、报警列表同屏，
  //   新报警到达自动换图。默认落地页。
  { key: 'alarm', label: '报警看板', icon: Bell },
  // ★ 从看板「数据分析」展开区独立成页
  { key: 'analysis', label: '数据分析', icon: DataAnalysis },
  // 值守大屏（左流右图 + 键盘操作）作为独立形态保留
  { key: 'live', label: '实时监控', icon: VideoCamera },
  { key: 'device', label: '设备管理', icon: Monitor },
  { key: 'workshop', label: '车间管理', icon: OfficeBuilding, adminOnly: true },
  { key: 'user', label: '用户管理', icon: User, adminOnly: true },
])

const visibleItems = computed(() =>
  items.value.filter((it) => !it.adminOnly || props.superuser),
)

function onNav(item: NavItem) {
  active.value = item.key
  emit('nav', item.key)
}
</script>

<template>
  <aside class="sidebar">
    <div class="brand">
      <div class="logo">
        <!-- 三环标志意象：三重空心圆环 + 梯形基座，单色蓝径向渐变 -->
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
          <defs>
            <linearGradient id="shRing" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stop-color="#91c8e6" />
              <stop offset="100%" stop-color="#155ba3" />
            </linearGradient>
          </defs>
          <g fill="none" stroke="url(#shRing)" stroke-width="1.5">
            <circle cx="12" cy="9.6" r="8" />
            <circle cx="12" cy="9.6" r="5.3" />
            <circle cx="12" cy="9.6" r="2.6" />
          </g>
          <path d="M9.9 17.2h4.2l1.5 4.2H8.4z" fill="url(#shRing)" />
        </svg>
      </div>
      <span>工业安全监控平台</span>
    </div>

    <nav class="nav">
      <div
        v-for="item in visibleItems"
        :key="item.key"
        class="nav-item"
        :class="{ active: active === item.key }"
        @click="onNav(item)"
      >
        <el-icon class="icon"><component :is="item.icon" /></el-icon>
        <span class="label">{{ item.label }}</span>

        <!-- ★ 2026-10-26：原来的「未处理数」红色角标已移除。
             它是"全部未处理"的累计值（实测 5746，只涨不跌），
             对甲方既不能指导行动，又会让人误以为系统没人管。
             新报警的提示交给全屏浮层 + 列表闪动，不做累计数。 -->
      </div>
    </nav>

    <div class="foot">v1.1.0</div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 232px;
  flex-shrink: 0;
  /* ★ 2026-10-26：侧栏从"白底 + 右侧灰线"改为**极淡渐变面**，
     与内容区的纯白拉开层次，整屏不再是"一块白板切两半"。 */
  background: linear-gradient(180deg, var(--surface) 0%, var(--surface-2) 100%);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 18px 20px;
  font-size: var(--fs-lg);              /* 视觉 14.4px */
  font-weight: 800;
  letter-spacing: 0.3px;
  /* 品牌中文近黑（取自三环标志的文字色） */
  color: var(--brand-ink);
}
/* ★ 三环标志意象：三个空心圆环 + 梯形基座，环心浅天蓝向外加深到深蓝 */
.brand .logo {
  width: 30px;
  height: 30px;
  border-radius: var(--r-sm);
  background: linear-gradient(135deg, var(--brand-soft-2), var(--brand-soft));
  box-shadow: inset 0 0 0 1px var(--brand-line);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.nav { padding: 6px 12px; flex: 1; }
.nav-item {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 12px 14px;
  border-radius: var(--r-md);
  margin-bottom: 4px;
  color: var(--text-2);
  cursor: pointer;
  font-size: var(--fs-md);              /* 视觉 12.8px（原 12px） */
  font-weight: 600;
  transition: background 0.16s, color 0.16s, box-shadow 0.16s, transform 0.12s;
}
.nav-item:hover {
  background: var(--brand-soft);
  color: var(--brand-deep);
  transform: translateX(1px);
}
.nav-item.active {
  background: linear-gradient(135deg, var(--brand) 0%, var(--brand-deep) 100%);
  color: #fff;
  font-weight: 700;
  box-shadow: 0 2px 8px rgba(var(--brand-rgb), 0.35);
}
.nav-item .icon { font-size: var(--fs-md); }
.nav-item .label { flex: 1; }
.nav-badge {
  background: var(--danger);
  color: #fff;
  font-size: var(--fs-micro);
  font-weight: 800;
  min-width: 20px;
  height: 20px;
  border-radius: var(--r-pill);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 6px;
}
.foot {
  padding: 14px 18px;
  font-size: var(--fs-micro);
  color: var(--text-3);
}
</style>
