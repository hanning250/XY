import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // 后端 FastAPI 默认 8088
      '/api': {
        target: 'http://127.0.0.1:8088',
        changeOrigin: true,
        ws: true, // ★ WebSocket 实时推送需要
      },
      '/openapi': {
        target: 'http://127.0.0.1:8088',
        changeOrigin: true,
      },
      '/media': {
        target: 'http://127.0.0.1:8088',
        changeOrigin: true,
      },
    },
  },
})
