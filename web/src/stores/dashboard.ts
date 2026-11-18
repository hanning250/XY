import { defineStore } from 'pinia'
import { ref } from 'vue'
import { alarmApi, tokenStore } from '@/api'
import type { Dashboard } from '@/types'

/** Keep the last successful snapshot across page navigation, scoped to the login. */
export const useDashboardStore = defineStore('dashboard', () => {
  const data = ref<Dashboard | null>(null)
  const refreshing = ref(false)
  const error = ref(false)
  const updatedAt = ref(0)
  let scope: string | null | undefined
  let flight: Promise<void> | null = null

  function ensureScope() {
    const identity = tokenStore.get()
    if (identity !== scope) {
      scope = identity
      data.value = null
      updatedAt.value = 0
      error.value = false
      refreshing.value = false
      flight = null
    }
  }

  function refresh(force = false): Promise<void> {
    ensureScope()
    if (flight) return flight
    if (!force && data.value && Date.now() - updatedAt.value < 30_000) {
      return Promise.resolve()
    }
    const identity = scope
    refreshing.value = true
    error.value = false
    const request: Promise<void> = Promise.resolve()
      .then(() => alarmApi.dashboard(7))
      .then((result: Dashboard) => {
        if (identity !== tokenStore.get() || identity !== scope) return
        data.value = result
        updatedAt.value = Date.now()
      }).catch(() => {
        if (identity === tokenStore.get() && identity === scope) error.value = true
      }).finally(() => {
        if (flight === request) {
          refreshing.value = false
          flight = null
        }
      })
    flight = request
    return request
  }

  return { data, refreshing, error, updatedAt, ensureScope, refresh }
})
