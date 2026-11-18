import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/api'

/**
 * ★ 当前登录身份（前端角色判断用）。
 *
 * 数据来自 GET /api/auth/me：
 *   · superuser=true → admin，前端显示「车间管理 / 用户管理」菜单
 *   · workshops      → 子账号可见车间（数据隔离以后端为准，这里仅展示）
 */
export const useAuth = defineStore('auth', () => {
  const subject = ref('')
  const superuser = ref(false)
  const workshops = ref<string[]>([])
  const loaded = ref(false)

  async function fetchMe() {
    if (loaded.value) return
    try {
      const me = await authApi.me()
      subject.value = me.subject || ''
      superuser.value = !!me.superuser
      workshops.value = me.workshops || []
      loaded.value = true
    } catch {
      /* 401 由拦截器统一处理 */
    }
  }

  function reset() {
    subject.value = ''
    superuser.value = false
    workshops.value = []
    loaded.value = false
  }

  return { subject, superuser, workshops, loaded, fetchMe, reset }
})
