import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'

import App from './App.vue'
import { authApi } from './api'
import './style.css'

/**
 * ★ 大屏适配：按后端配置整页缩放（默认 0.8 = 现场大屏一屏看完）。
 *
 * style.css 里已写死 `:root { --ui-scale: 0.8 }` 兜底，
 * 这里只是让现场能通过 server/.env 的 ISUP_UI_SCALE 调整比例而**不必重新构建前端**。
 *
 * ⚠️ 2026-10-22：缩放方式从 `zoom` 改为 `transform: scale()`。
 *    原因：zoom 不参与 JS 坐标计算，Element Plus 的下拉/日期面板用
 *    getBoundingClientRect 定位，会算到未缩放的坐标 →
 *    「点按钮后选择栏飘到别的地方」。现在只改 CSS 变量，布局与定位自动跟随。
 *
 * 不 await：拿不到配置就用 CSS 默认值，绝不阻塞首屏。
 */
function applyUiScale() {
  authApi
    .config()
    .then((cfg: { ui_scale?: number }) => {
      const s = Number(cfg?.ui_scale)
      if (Number.isFinite(s) && s > 0.5 && s <= 2) {
        document.documentElement.style.setProperty('--ui-scale', String(s))
      }
    })
    .catch(() => {
      /* 探测失败：保持 CSS 里的 0.8 */
    })
}

applyUiScale()

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(ElementPlus, { locale: zhCn })

/**
 * ⚠️ 不要 `for (const [k, c] of Object.entries(Icons)) app.component(k, c)`！
 *
 * @element-plus/icons-vue 导出的图标名里有 `Loading`、`Menu`、`Link`、
 * `View`、`Switch`、`Select`、`Timer` 等**与 Element Plus 内部组件/directive 同名**的名字。
 * 全局注册会**覆盖 Element Plus 自己的实现**，导致：
 *   · v-loading 指令失效
 *   · <el-icon><Loading /></el-icon> 渲染异常
 *   · 控制台报 "io" 相关的加载错误 / 弹 ElMessage 错误提示
 *
 * 正确做法：**按需导入**，在各自组件里 `import { Xxx } from '@element-plus/icons-vue'`。
 * 本项目所有组件都已是按需导入，因此这里不再做全局注册。
 */

app.mount('#app')
