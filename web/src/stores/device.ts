import { defineStore } from 'pinia'
import { ref } from 'vue'
import { deviceApi } from '@/api'
import type { Device } from '@/types'

export const useDeviceStore = defineStore('device', () => {
  const devices = ref<Device[]>([])

  async function fetch() {
    try {
      devices.value = await deviceApi.list()
    } catch {
      devices.value = []
    }
  }

  function label(deviceId: string): string {
    const d = devices.value.find((x) => x.device_id === deviceId)
    if (!d) return deviceId || '未知设备'
    return `${d.device_id}${d.online ? '' : '（离线）'}`
  }

  return { devices, fetch, label }
})
